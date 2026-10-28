from datetime import datetime, timezone

from app.extensions import db


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)

    # "user" or "vendor"; admin accounts are identified through User.role.
    account_type = db.Column(db.String(20), nullable=False, index=True)
    account_id = db.Column(db.Integer, nullable=False, index=True)

    # Store only the SHA-256 hash of the reset token.
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)

    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return (
            f"<PasswordResetToken id={self.id} "
            f"account_type={self.account_type!r} "
            f"account_id={self.account_id}>"
        )
