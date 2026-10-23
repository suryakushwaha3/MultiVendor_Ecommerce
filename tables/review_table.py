from datetime import datetime, timezone

from app.extensions import db


class Review(db.Model):
    __tablename__ = "reviews"

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

    order_item_id = db.Column(
        db.Integer,
        db.ForeignKey("order_items.id"),
        nullable=True,
        index=True
    )

    rating = db.Column(
        db.Integer,
        nullable=False
    )

    title = db.Column(
        db.String(150),
        nullable=True
    )

    comment = db.Column(
        db.Text,
        nullable=True
    )

    is_verified_purchase = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    is_approved = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True
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

    __table_args__ = (
        db.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_review_rating_range"
        ),
        db.UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_review_user_product"
        ),
    )

    user = db.relationship(
        "User",
        backref=db.backref("reviews", lazy=True)
    )

    product = db.relationship(
        "Product",
        backref=db.backref("reviews", lazy=True)
    )

    order_item = db.relationship(
        "OrderItem",
        backref=db.backref("review", uselist=False)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "order_item_id": self.order_item_id,
            "rating": self.rating,
            "title": self.title,
            "comment": self.comment,
            "is_verified_purchase": self.is_verified_purchase,
            "is_approved": self.is_approved,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }