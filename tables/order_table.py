from datetime import datetime, timezone
from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    order_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    address_id = db.Column(
        db.Integer,
        db.ForeignKey("addresses.id"),
        nullable=False
    )

    subtotal = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    discount_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    shipping_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    tax_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    total_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    payment_status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    order_status = db.Column(
        db.String(30),
        nullable=False,
        default="placed",
        index=True
    )

    notes = db.Column(db.Text, nullable=True)

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
        backref=db.backref("orders", lazy=True)
    )

    address = db.relationship(
        "Address",
        backref=db.backref("orders", lazy=True)
    )

    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "user_id": self.user_id,
            "address_id": self.address_id,
            "subtotal": str(self.subtotal),
            "discount_amount": str(self.discount_amount),
            "shipping_amount": str(self.shipping_amount),
            "tax_amount": str(self.tax_amount),
            "total_amount": str(self.total_amount),
            "payment_status": self.payment_status,
            "order_status": self.order_status,
            "notes": self.notes,
            "items": [item.to_dict() for item in self.items],
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }