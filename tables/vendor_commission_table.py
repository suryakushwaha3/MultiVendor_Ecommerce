from datetime import datetime, timezone

from app.extensions import db


class VendorCommission(db.Model):
    __tablename__ = "vendor_commissions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    vendor_id = db.Column(
        db.Integer,
        db.ForeignKey("vendors.id"),
        nullable=False,
        index=True
    )

    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False,
        index=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    order_item_id = db.Column(
        db.Integer,
        db.ForeignKey("order_items.id"),
        nullable=False,
        unique=True
    )

    sale_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    commission_rate = db.Column(
        db.Numeric(5, 2),
        nullable=False
    )
    # Example: 10.00 means 10%

    commission_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    vendor_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True
    )
    # pending, approved, paid, cancelled

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
            "sale_amount >= 0",
            name="ck_commission_sale_nonnegative"
        ),
        db.CheckConstraint(
            "commission_rate >= 0 AND commission_rate <= 100",
            name="ck_commission_rate_range"
        ),
        db.CheckConstraint(
            "commission_amount >= 0",
            name="ck_commission_amount_nonnegative"
        ),
        db.CheckConstraint(
            "vendor_amount >= 0",
            name="ck_commission_vendor_amount_nonnegative"
        ),
        db.CheckConstraint(
            "status IN ('pending', 'approved', 'paid', 'cancelled')",
            name="ck_commission_status"
        ),
    )

    vendor = db.relationship(
        "Vendor",
        backref=db.backref("commissions", lazy=True)
    )

    store = db.relationship(
        "Store",
        backref=db.backref("commissions", lazy=True)
    )

    order = db.relationship(
        "Order",
        backref=db.backref("commissions", lazy=True)
    )

    order_item = db.relationship(
        "OrderItem",
        backref=db.backref("commission", uselist=False)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "store_id": self.store_id,
            "order_id": self.order_id,
            "order_item_id": self.order_item_id,
            "sale_amount": str(self.sale_amount),
            "commission_rate": str(self.commission_rate),
            "commission_amount": str(self.commission_amount),
            "vendor_amount": str(self.vendor_amount),
            "status": self.status,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }