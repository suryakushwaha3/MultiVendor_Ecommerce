from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.product_table import Product
from tables.store_table import Store
from tables.category_table import Category
from tables.subcategory_table import Subcategory
from utils.pagination import paginate_query


def create_product(data, vendor_id, commit=True):
    """Create a product after validating store ownership and category."""

    try:
        store_id = int(data["store_id"])
        category_id = int(data["category_id"])

        subcategory_id = (
            int(data["subcategory_id"])
            if data.get("subcategory_id") not in (None, "")
            else None
        )

        store = Store.query.filter_by(
            id=store_id,
            vendor_id=vendor_id
        ).first()

        if not store:
            return {
                "success": False,
                "message": "Store not found or access denied."
            }, 404

        if not store.is_active:
            return {
                "success": False,
                "message": "Cannot add products to an inactive store."
            }, 400

        category = db.session.get(Category, category_id)

        if not category or not category.is_active:
            return {
                "success": False,
                "message": "Category not found or inactive."
            }, 400

        if subcategory_id is not None:
            subcategory = db.session.get(
                Subcategory,
                subcategory_id
            )

            if (
                not subcategory
                or not subcategory.is_active
                or subcategory.category_id != category_id
            ):
                return {
                    "success": False,
                    "message": (
                        "Subcategory is invalid, inactive, "
                        "or does not belong to this category."
                    )
                }, 400

        product_name = data["product_name"].strip()
        slug = data["slug"].strip()
        description = data["description"].strip()
        sku = data["sku"].strip()

        if not all((product_name, slug, description, sku)):
            return {
                "success": False,
                "message": (
                    "Product name, slug, description, "
                    "and SKU cannot be empty."
                )
            }, 400

        price = Decimal(str(data["price"]))

        discount_price = (
            Decimal(str(data["discount_price"]))
            if data.get("discount_price") not in (None, "")
            else None
        )

        weight = (
            Decimal(str(data["weight"]))
            if data.get("weight") not in (None, "")
            else None
        )

        stock_value = data["stock_quantity"]

        if isinstance(stock_value, bool):
            raise ValueError

        stock_quantity = int(stock_value)

        if str(stock_quantity) != str(stock_value).strip():
            raise ValueError

        if not price.is_finite() or price <= 0:
            return {
                "success": False,
                "message": "Price must be greater than zero."
            }, 400

        if discount_price is not None:
            if (
                not discount_price.is_finite()
                or discount_price < 0
                or discount_price >= price
            ):
                return {
                    "success": False,
                    "message": (
                        "Discount price must be non-negative "
                        "and less than the original price."
                    )
                }, 400

        if weight is not None and (
            not weight.is_finite() or weight <= 0
        ):
            return {
                "success": False,
                "message": "Weight must be greater than zero."
            }, 400

        if stock_quantity < 0:
            return {
                "success": False,
                "message": "Stock quantity cannot be negative."
            }, 400

        featured_value = data.get("is_featured", False)

        if isinstance(featured_value, bool):
            is_featured = featured_value
        elif isinstance(featured_value, str) and (
            featured_value.lower() in ("true", "false", "1", "0")
        ):
            is_featured = featured_value.lower() in ("true", "1")
        else:
            return {
                "success": False,
                "message": "is_featured must be true or false."
            }, 400

        product = Product(
            store_id=store_id,
            category_id=category_id,
            subcategory_id=subcategory_id,
            product_name=product_name,
            slug=slug,
            description=description,
            brand=(
                data.get("brand").strip()
                if isinstance(data.get("brand"), str)
                else data.get("brand")
            ),
            sku=sku,
            price=price,
            discount_price=discount_price,
            stock_quantity=stock_quantity,
            weight=weight,
            is_featured=is_featured
        )

        db.session.add(product)

        # Flush assigns the product ID without committing the transaction.
        db.session.flush()

        if commit:
            db.session.commit()

        return {
            "success": True,
            "message": "Product created successfully.",
            "data": product.to_dict()
        }, 201

    except (ValueError, TypeError, InvalidOperation, KeyError):
        db.session.rollback()

        return {
            "success": False,
            "message": "Invalid product data."
        }, 400

    except IntegrityError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Product slug or SKU already exists."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while creating product."
        }, 500


def get_vendor_products(vendor_id, store_id=None):
    """Get paginated products belonging to the authenticated vendor."""

    query = Product.query.join(Store).filter(
        Store.vendor_id == vendor_id
    )

    if store_id is not None:
        query = query.filter(
            Product.store_id == store_id
        )

    query = query.order_by(Product.created_at.desc())

    result = paginate_query(query)

    return {
        "success": True,
        "count": len(result["data"]),
        "data": [
            product.to_dict()
            for product in result["data"]
        ],
        "pagination": result["pagination"]
    }, 200


def get_vendor_product_by_id(product_id, vendor_id):
    """Get a product only if it belongs to the vendor."""

    product = Product.query.join(Store).filter(
        Product.id == product_id,
        Store.vendor_id == vendor_id
    ).first()

    if not product:
        return {
            "success": False,
            "message": "Product not found."
        }, 404

    return {
        "success": True,
        "data": product.to_dict()
    }, 200


def update_product(product_id, vendor_id, data):
    """Update a vendor-owned product."""

    product = Product.query.join(Store).filter(
        Product.id == product_id,
        Store.vendor_id == vendor_id
    ).first()

    if not product:
        return {
            "success": False,
            "message": "Product not found."
        }, 404

    try:
        if "category_id" in data:
            category_id = int(data["category_id"])

            category = db.session.get(
                Category,
                category_id
            )

            if not category or not category.is_active:
                return {
                    "success": False,
                    "message": "Category not found or inactive."
                }, 400

            product.category_id = category_id

            if product.subcategory_id is not None:
                old_subcategory = db.session.get(
                    Subcategory,
                    product.subcategory_id
                )

                if (
                    old_subcategory is None
                    or old_subcategory.category_id != category_id
                ):
                    product.subcategory_id = None

        if "subcategory_id" in data:
            value = data["subcategory_id"]

            if value in (None, ""):
                product.subcategory_id = None
            else:
                subcategory_id = int(value)

                subcategory = db.session.get(
                    Subcategory,
                    subcategory_id
                )

                if (
                    not subcategory
                    or not subcategory.is_active
                    or subcategory.category_id != product.category_id
                ):
                    return {
                        "success": False,
                        "message": (
                            "Subcategory is invalid or does not "
                            "belong to the selected category."
                        )
                    }, 400

                product.subcategory_id = subcategory_id

        text_fields = (
            "product_name",
            "slug",
            "description",
            "brand",
            "sku"
        )

        for field in text_fields:
            if field in data:
                value = data[field]

                if value is not None and not isinstance(value, str):
                    return {
                        "success": False,
                        "message": f"{field} must be text."
                    }, 400

                setattr(
                    product,
                    field,
                    value.strip() if isinstance(value, str) else value
                )

        if "price" in data:
            price = Decimal(str(data["price"]))

            if not price.is_finite() or price <= 0:
                return {
                    "success": False,
                    "message": "Price must be greater than zero."
                }, 400

            product.price = price

        if "discount_price" in data:
            value = data["discount_price"]

            product.discount_price = (
                Decimal(str(value))
                if value not in (None, "")
                else None
            )

        if "weight" in data:
            value = data["weight"]

            product.weight = (
                Decimal(str(value))
                if value not in (None, "")
                else None
            )

        if "stock_quantity" in data:
            value = data["stock_quantity"]

            if isinstance(value, bool):
                raise ValueError

            quantity = int(value)

            if quantity < 0 or str(quantity) != str(value).strip():
                return {
                    "success": False,
                    "message": "Stock quantity cannot be negative."
                }, 400

            product.stock_quantity = quantity

        if "is_featured" in data:
            value = data["is_featured"]

            if isinstance(value, bool):
                product.is_featured = value

            elif isinstance(value, str) and value.lower() in (
                "true", "false", "1", "0"
            ):
                product.is_featured = value.lower() in (
                    "true", "1"
                )

            else:
                return {
                    "success": False,
                    "message": "is_featured must be true or false."
                }, 400

        if product.discount_price is not None:
            if (
                not product.discount_price.is_finite()
                or product.discount_price < 0
                or product.discount_price >= product.price
            ):
                return {
                    "success": False,
                    "message": (
                        "Discount price must be less than "
                        "the original price."
                    )
                }, 400

        if product.weight is not None and (
            not product.weight.is_finite()
            or product.weight <= 0
        ):
            return {
                "success": False,
                "message": "Weight must be greater than zero."
            }, 400

        db.session.commit()

        return {
            "success": True,
            "message": "Product updated successfully.",
            "data": product.to_dict()
        }, 200

    except (ValueError, TypeError, InvalidOperation):
        db.session.rollback()

        return {
            "success": False,
            "message": "Invalid product data."
        }, 400

    except IntegrityError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Product slug or SKU already exists."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while updating product."
        }, 500


def update_product_status(product_id, vendor_id, is_active):
    """Activate or deactivate a vendor-owned product."""

    product = Product.query.join(Store).filter(
        Product.id == product_id,
        Store.vendor_id == vendor_id
    ).first()

    if not product:
        return {
            "success": False,
            "message": "Product not found."
        }, 404

    if not isinstance(is_active, bool):
        return {
            "success": False,
            "message": "is_active must be true or false."
        }, 400

    try:
        product.is_active = is_active
        db.session.commit()

        return {
            "success": True,
            "message": "Product status updated successfully.",
            "data": product.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while updating product status."
        }, 500


def delete_product(product_id, vendor_id):
    """Delete a vendor-owned product."""

    product = Product.query.join(Store).filter(
        Product.id == product_id,
        Store.vendor_id == vendor_id
    ).first()

    if not product:
        return {
            "success": False,
            "message": "Product not found."
        }, 404

    try:
        db.session.delete(product)
        db.session.commit()

        return {
            "success": True,
            "message": "Product deleted successfully."
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while deleting product."
        }, 500