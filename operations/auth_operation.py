from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
)

from app.extensions import db
from tables.user_table import User
from tables.vendor_table import Vendor
from utils.security import verify_password


def login_user(data):
    """Authenticate a user and generate access and refresh tokens."""

    email = data["email"].strip().lower()
    password = data["password"]

    try:
        user = db.session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if user is None or not verify_password(
            password, user.password_hash
        ):
            return {
                "success": False,
                "message": "Invalid email or password."
            }, 401

        if not user.is_active:
            return {
                "success": False,
                "message": "Your account is inactive."
            }, 403

        access_token = create_access_token(
            identity=str(user.id)
        )

        refresh_token = create_refresh_token(
            identity=str(user.id)
        )

        return {
            "success": True,
            "message": "Login successful.",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to process login at this time."
        }, 500


def login_vendor(data):
    """Authenticate a vendor and generate access and refresh tokens."""

    email = data["email"].strip().lower()
    password = data["password"]

    try:
        vendor = db.session.execute(
            select(Vendor).where(Vendor.email == email)
        ).scalar_one_or_none()

        if vendor is None or not verify_password(
            password, vendor.password_hash
        ):
            return {
                "success": False,
                "message": "Invalid email or password."
            }, 401

        if not vendor.is_active:
            return {
                "success": False,
                "message": "Your vendor account is inactive."
            }, 403

        if not vendor.is_approved:
            return {
                "success": False,
                "message": "Your vendor account is awaiting approval."
            }, 403

        identity = f"vendor:{vendor.id}"

        access_token = create_access_token(
            identity=identity
        )

        refresh_token = create_refresh_token(
            identity=identity
        )

        return {
            "success": True,
            "message": "Vendor login successful.",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "vendor": {
                "id": vendor.id,
                "name": vendor.name,
                "email": vendor.email,
                "business_name": vendor.business_name
            }
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to process vendor login at this time."
        }, 500
 