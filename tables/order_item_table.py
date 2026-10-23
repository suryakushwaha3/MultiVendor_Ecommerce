from datetime import datetime, timezone

from app.extensions import db


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    # Product details at the time of purchase
    product_name = db.Column(
        db.String(200),
        nullable=False
    )

    product_image_url = db.Column(
        db.String(500),
        nullable=True
    )

    sku = db.Column(
        db.String(100),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    unit_price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    discount_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    total_price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint(
            "quantity > 0",
            name="ck_order_item_quantity_positive"
        ),
        db.CheckConstraint(
            "unit_price >= 0",
            name="ck_order_item_unit_price_nonnegative"
        ),
        db.CheckConstraint(
            "discount_amount >= 0",
            name="ck_order_item_discount_nonnegative"
        ),
        db.CheckConstraint(
            "total_price >= 0",
            name="ck_order_item_total_nonnegative"
        ),
    )

    order = db.relationship(
        "Order",
        back_populates="items"
    )

    product = db.relationship(
        "Product",
        backref=db.backref("order_items", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_image_url": self.product_image_url,
            "sku": self.sku,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price),
            "discount_amount": str(self.discount_amount),
            "total_price": str(self.total_price),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )
        }