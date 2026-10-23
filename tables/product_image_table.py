from datetime import datetime, timezone

from app.extensions import db


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    image_url = db.Column(
        db.String(1000),
        nullable=False
    )

    alt_text = db.Column(
        db.String(250),
        nullable=True
    )

    is_primary = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    display_order = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    product = db.relationship(
        "Product",
        backref=db.backref(
            "images",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "image_url": self.image_url,
            "alt_text": self.alt_text,
            "is_primary": self.is_primary,
            "display_order": self.display_order,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            )
        }