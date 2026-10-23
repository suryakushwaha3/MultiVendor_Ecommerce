from datetime import datetime, timezone

from app.extensions import db


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    full_name = db.Column(
        db.String(100),
        nullable=False
    )

    phone_number = db.Column(
        db.String(20),
        nullable=False
    )

    address_line1 = db.Column(
        db.String(255),
        nullable=False
    )

    address_line2 = db.Column(
        db.String(255),
        nullable=True
    )

    landmark = db.Column(
        db.String(150),
        nullable=True
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    state = db.Column(
        db.String(100),
        nullable=False
    )

    pincode = db.Column(
        db.String(10),
        nullable=False
    )

    country = db.Column(
        db.String(100),
        nullable=False,
        default="India"
    )

    address_type = db.Column(
        db.String(20),
        nullable=False,
        default="home"
    )

    is_default = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

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

    user = db.relationship(
        "User",
        backref=db.backref("addresses", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "phone_number": self.phone_number,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "landmark": self.landmark,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "country": self.country,
            "address_type": self.address_type,
            "is_default": self.is_default,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }