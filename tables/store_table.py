from datetime import datetime, timezone

from app.extensions import db


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)

    vendor_id = db.Column(
        db.Integer,
        db.ForeignKey("vendors.id"),
        nullable=False,
        index=True
    )

    store_name = db.Column(
        db.String(150),
        nullable=False
    )

    slug = db.Column(
        db.String(180),
        unique=True,
        nullable=False,
        index=True
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    logo_url = db.Column(
        db.String(500),
        nullable=True
    )

    banner_url = db.Column(
        db.String(500),
        nullable=True
    )

    address = db.Column(
        db.Text,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
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

    vendor = db.relationship(
        "Vendor",
        backref=db.backref("stores", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "store_name": self.store_name,
            "slug": self.slug,
            "description": self.description,
            "logo_url": self.logo_url,
            "banner_url": self.banner_url,
            "address": self.address,
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