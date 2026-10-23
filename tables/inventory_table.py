from datetime import datetime, timezone

from app.extensions import db


class Inventory(db.Model):
    __tablename__ = "inventory"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False,
        index=True
    )

    movement_type = db.Column(
        db.String(30),
        nullable=False
    )
    # purchase, sale, return, adjustment, damaged

    quantity_change = db.Column(
        db.Integer,
        nullable=False
    )
    # Positive = stock added; negative = stock removed

    previous_stock = db.Column(
        db.Integer,
        nullable=False
    )

    new_stock = db.Column(
        db.Integer,
        nullable=False
    )

    reference_type = db.Column(
        db.String(50),
        nullable=True
    )
    # order, purchase, return, manual_adjustment

    reference_id = db.Column(
        db.Integer,
        nullable=True,
        index=True
    )

    note = db.Column(
        db.String(500),
        nullable=True
    )

    created_by_type = db.Column(
        db.String(20),
        nullable=True
    )
    # admin, vendor, system

    created_by_id = db.Column(
        db.Integer,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint(
            "quantity_change != 0",
            name="ck_inventory_quantity_change_nonzero"
        ),
        db.CheckConstraint(
            "previous_stock >= 0",
            name="ck_inventory_previous_stock_nonnegative"
        ),
        db.CheckConstraint(
            "new_stock >= 0",
            name="ck_inventory_new_stock_nonnegative"
        ),
        db.CheckConstraint(
            "movement_type IN "
            "('purchase', 'sale', 'return', 'adjustment', 'damaged')",
            name="ck_inventory_movement_type"
        ),
    )

    product = db.relationship(
        "Product",
        backref=db.backref("inventory_history", lazy=True)
    )

    store = db.relationship(
        "Store",
        backref=db.backref("inventory_history", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "store_id": self.store_id,
            "movement_type": self.movement_type,
            "quantity_change": self.quantity_change,
            "previous_stock": self.previous_stock,
            "new_stock": self.new_stock,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "note": self.note,
            "created_by_type": self.created_by_type,
            "created_by_id": self.created_by_id,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )
        }