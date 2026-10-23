from datetime import datetime, timezone

from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False,
        index=True
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False,
        index=True
    )

    subcategory_id = db.Column(
        db.Integer,
        db.ForeignKey("subcategories.id"),
        nullable=True,
        index=True
    )

    product_name = db.Column(
        db.String(200),
        nullable=False,
        index=True
    )

    slug = db.Column(
        db.String(220),
        unique=True,
        nullable=False,
        index=True
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    brand = db.Column(
        db.String(100),
        nullable=True
    )

    sku = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    discount_price = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    stock_quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    weight = db.Column(
        db.Numeric(10, 3),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    is_featured = db.Column(
        db.Boolean,
        nullable=False,
        default=False
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

    store = db.relationship(
        "Store",
        backref=db.backref(
            "products",
            lazy=True
        )
    )

    category = db.relationship(
        "Category",
        backref=db.backref(
            "products",
            lazy=True
        )
    )

    subcategory = db.relationship(
        "Subcategory",
        backref=db.backref(
            "products",
            lazy=True
        )
    )

    def to_dict(self):
        return {
            "id": self.id,
            "store_id": self.store_id,
            "category_id": self.category_id,
            "subcategory_id": self.subcategory_id,
            "product_name": self.product_name,
            "slug": self.slug,
            "description": self.description,
            "brand": self.brand,
            "sku": self.sku,

            "price": str(self.price),

            "discount_price": (
                str(self.discount_price)
                if self.discount_price is not None
                else None
            ),

            "stock_quantity": self.stock_quantity,

            "weight": (
                str(self.weight)
                if self.weight is not None
                else None
            ),

            "is_active": self.is_active,
            "is_featured": self.is_featured,

            "images": [
                image.to_dict()
                for image in self.images
            ],

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            )
        }