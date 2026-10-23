from datetime import datetime, timezone

from app.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    payment_method = db.Column(
        db.String(50),
        nullable=False
    )

    transaction_id = db.Column(
        db.String(255),
        unique=True,
        nullable=True,
        index=True
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    currency = db.Column(
        db.String(3),
        nullable=False,
        default="INR"
    )

    payment_status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True
    )

    gateway_name = db.Column(
        db.String(50),
        nullable=True
    )

    gateway_order_id = db.Column(
        db.String(255),
        nullable=True,
        index=True
    )

    gateway_payment_id = db.Column(
        db.String(255),
        nullable=True,
        index=True
    )

    failure_reason = db.Column(
        db.String(500),
        nullable=True
    )

    paid_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
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
            "amount >= 0",
            name="ck_payment_amount_nonnegative"
        ),
    )

    order = db.relationship(
        "Order",
        backref=db.backref("payments", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "payment_status": self.payment_status,
            "gateway_name": self.gateway_name,
            "gateway_order_id": self.gateway_order_id,
            "gateway_payment_id": self.gateway_payment_id,
            "failure_reason": self.failure_reason,
            "paid_at": (
                self.paid_at.isoformat()
                if self.paid_at else None
            ),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }