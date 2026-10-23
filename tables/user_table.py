from datetime import datetime, timezone

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    # Primary Key
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # User Information
    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True
    )

    phone_number = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    # Authentication
    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # User Role: customer, vendor, admin
    role = db.Column(
        db.String(20),
        nullable=False,
        default="customer",
        index=True
    )

    # Account Status
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Convert User Object to Dictionary
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone_number": self.phone_number,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }