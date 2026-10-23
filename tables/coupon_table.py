from datetime import datetime, timezone

from app.extensions import db


class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    code = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    discount_type = db.Column(
        db.String(20),
        nullable=False
    )
    # Supported types will be: percentage, fixed

    discount_value = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    minimum_order_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    maximum_discount_amount = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    usage_limit = db.Column(
        db.Integer,
        nullable=True
    )

    used_count = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    starts_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
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
            "discount_value > 0",
            name="ck_coupon_discount_positive"
        ),
        db.CheckConstraint(
            "discount_type IN ('percentage', 'fixed')",
            name="ck_coupon_discount_type"
        ),
        db.CheckConstraint(
            "minimum_order_amount >= 0",
            name="ck_coupon_min_order_nonnegative"
        ),
        db.CheckConstraint(
            "maximum_discount_amount IS NULL OR maximum_discount_amount >= 0",
            name="ck_coupon_max_discount_nonnegative"
        ),
        db.CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="ck_coupon_usage_limit_positive"
        ),
        db.CheckConstraint(
            "used_count >= 0",
            name="ck_coupon_used_count_nonnegative"
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "description": self.description,
            "discount_type": self.discount_type,
            "discount_value": str(self.discount_value),
            "minimum_order_amount": str(self.minimum_order_amount),
            "maximum_discount_amount": (
                str(self.maximum_discount_amount)
                if self.maximum_discount_amount is not None
                else None
            ),
            "usage_limit": self.usage_limit,
            "used_count": self.used_count,
            "starts_at": (
                self.starts_at.isoformat()
                if self.starts_at else None
            ),
            "expires_at": (
                self.expires_at.isoformat()
                if self.expires_at else None
            ),
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