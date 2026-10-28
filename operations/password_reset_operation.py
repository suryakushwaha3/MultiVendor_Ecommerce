import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from tables.user_table import User
from tables.vendor_table import Vendor
from tables.password_reset_token_table import PasswordResetToken
from utils.email_service import send_email
from utils.security import hash_password, verify_password


GENERIC_FORGOT_RESPONSE = {
    "success": True,
    "message": (
        "If an eligible account exists for the provided details, "
        "password reset instructions will be sent."
    ),
}

SUPPORTED_ACCOUNT_TYPES = {"customer", "admin", "vendor"}
RESET_TOKEN_LIFETIME_MINUTES = 15


def _utc_now():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def _hash_token(token):
    """Return a SHA-256 hash of the reset token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_datetime(value):
    """Normalize a database datetime to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _get_account(account_type, account_id):
    """Fetch an account from the appropriate table."""
    if account_type == "vendor":
        account = db.session.get(Vendor, account_id)

        if account is None or not account.is_active:
            return None

        if not account.is_approved:
            return None

        return account

    account = db.session.get(User, account_id)

    if account is None or not account.is_active:
        return None

    if account.role != account_type:
        return None

    return account


def request_password_reset(data):
    """
    Request a password reset for a customer, admin, or vendor.

    Required:
        account_type: customer, admin, or vendor
        email: registered email address
    """
    account_type = data["account_type"].strip().lower()
    email = data["email"].strip().lower()

    if account_type not in SUPPORTED_ACCOUNT_TYPES:
        return {
            "success": False,
            "message": "Unsupported account type.",
        }, 400

    try:
        if account_type == "vendor":
            account = db.session.execute(
                select(Vendor).where(
                    Vendor.email == email
                )
            ).scalar_one_or_none()

            token_account_type = "vendor"

        else:
            account = db.session.execute(
                select(User).where(
                    User.email == email,
                    User.role == account_type,
                )
            ).scalar_one_or_none()

            # The existing database model stores both customer and
            # admin reset records using the "user" account type.
            token_account_type = "user"

        if account is None or not account.is_active:
            return dict(GENERIC_FORGOT_RESPONSE), 200

        if account_type == "vendor" and not account.is_approved:
            return dict(GENERIC_FORGOT_RESPONSE), 200

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        now = _utc_now()

        # Invalidate previously issued unused tokens for this account.
        db.session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.account_type == token_account_type,
                PasswordResetToken.account_id == account.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )

        reset_record = PasswordResetToken(
            account_type=token_account_type,
            account_id=account.id,
            token_hash=token_hash,
            expires_at=now + timedelta(
                minutes=RESET_TOKEN_LIFETIME_MINUTES
            ),
        )

        db.session.add(reset_record)
        db.session.commit()

        body = (
            f"Hello {account.name},\n\n"
            "We received a request to reset your password.\n\n"
            f"Your password reset token is:\n{raw_token}\n\n"
            f"This token expires in "
            f"{RESET_TOKEN_LIFETIME_MINUTES} minutes "
            "and can only be used once.\n"
            "If you did not request this, you can ignore this email.\n"
        )

        email_sent = send_email(
            to_email=account.email,
            subject="Password Reset Request",
            body=body,
        )

        if not email_sent:
            db.session.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.id == reset_record.id,
                    PasswordResetToken.used_at.is_(None),
                )
                .values(used_at=_utc_now())
            )

            db.session.commit()

            current_app.logger.warning(
                "Password reset email could not be delivered."
            )

        return dict(GENERIC_FORGOT_RESPONSE), 200

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Database error while requesting a password reset."
        )

        return {
            "success": False,
            "message": "Unable to process the request right now.",
        }, 500


def reset_password(data):
    """
    Reset a password using a valid, unused reset token.

    Required:
        account_type: customer, admin, or vendor
        token: token received by email
        new_password: new password
    """
    account_type = data["account_type"].strip().lower()
    raw_token = data["token"].strip()
    new_password = data["new_password"]

    if account_type not in SUPPORTED_ACCOUNT_TYPES:
        return {
            "success": False,
            "message": "Invalid account type.",
        }, 400

    if not 8 <= len(new_password) <= 128:
        return {
            "success": False,
            "message": (
                "Password must be between 8 and 128 characters."
            ),
        }, 400

    token_account_type = (
        "vendor" if account_type == "vendor" else "user"
    )

    now = _utc_now()
    token_hash = _hash_token(raw_token)

    try:
        reset_record = db.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.account_type == token_account_type,
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
            )
        ).scalar_one_or_none()

        if reset_record is None:
            return {
                "success": False,
                "message": "Invalid or expired reset token.",
            }, 400

        expires_at = _normalize_datetime(reset_record.expires_at)

        if expires_at <= now:
            reset_record.used_at = now
            db.session.commit()

            return {
                "success": False,
                "message": "Invalid or expired reset token.",
            }, 400

        # Fetch the account and verify its current role.
        account = _get_account(
            account_type,
            reset_record.account_id,
        )

        if account is None:
            reset_record.used_at = now
            db.session.commit()

            return {
                "success": False,
                "message": "Invalid or expired reset token.",
            }, 400

        # Update password and consume the token in one transaction.
        account.password_hash = hash_password(new_password)
        reset_record.used_at = now

        # Invalidate all other unused reset tokens for this account.
        db.session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.account_type == token_account_type,
                PasswordResetToken.account_id == account.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.id != reset_record.id,
            )
            .values(used_at=now)
        )

        db.session.commit()

        return {
            "success": True,
            "message": (
                "Password reset successfully. "
                "Please log in with your new password."
            ),
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Database error while resetting a password."
        )

        return {
            "success": False,
            "message": "Unable to reset the password right now.",
        }, 500


def change_password(data):
    """
    Change the password of the currently authenticated account.

    Required:
        current_password
        new_password
    """
    identity = str(get_jwt_identity())

    current_password = data["current_password"]
    new_password = data["new_password"]

    if current_password == new_password:
        return {
            "success": False,
            "message": (
                "New password must be different "
                "from the current password."
            ),
        }, 400

    if not 8 <= len(new_password) <= 128:
        return {
            "success": False,
            "message": (
                "Password must be between 8 and 128 characters."
            ),
        }, 400

    try:
        if identity.startswith("vendor:"):
            try:
                vendor_id = int(identity.split(":", 1)[1])
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid authentication identity.",
                }, 401

            account = db.session.get(Vendor, vendor_id)
            account_type = "vendor"

            if (
                account is not None
                and not account.is_approved
            ):
                return {
                    "success": False,
                    "message": "Your vendor account is awaiting approval.",
                }, 403

        else:
            try:
                user_id = int(identity)
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid authentication identity.",
                }, 401

            account = db.session.get(User, user_id)
            account_type = "user"

        if account is None or not account.is_active:
            return {
                "success": False,
                "message": "Account not found or inactive.",
            }, 403

        if not verify_password(
            current_password,
            account.password_hash,
        ):
            return {
                "success": False,
                "message": "Current password is incorrect.",
            }, 400

        account.password_hash = hash_password(new_password)
        now = _utc_now()

        # Invalidate outstanding reset tokens after a password change.
        db.session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.account_type == account_type,
                PasswordResetToken.account_id == account.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )

        db.session.commit()

        return {
            "success": True,
            "message": "Password changed successfully.",
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Database error while changing a password."
        )

        return {
            "success": False,
            "message": "Unable to change the password right now.",
        }, 500
 