from datetime import datetime, timezone

from app.extensions import db


class Wishlist(db.Model):
    __tablename__ = "wishlists"

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

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_wishlist_user_product"
        ),
    )

    user = db.relationship(
        "User",
        backref=db.backref("wishlist_items", lazy=True)
    )

    product = db.relationship(
        "Product",
        backref=db.backref("wishlist_entries", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )
        }