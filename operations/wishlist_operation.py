from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.extensions import db
from tables.wishlist_table import Wishlist
from tables.product_table import Product


def _get_product_price(product):
    """Return the effective product price."""
    if product.discount_price is not None:
        return Decimal(str(product.discount_price))

    return Decimal(str(product.price))


def _get_product_image(product):
    """Return the first available product image URL."""
    try:
        images = product.images

        if images:
            image = images[0]

            if isinstance(image, dict):
                return image.get("image_url") or image.get("url")

            return (
                getattr(image, "image_url", None)
                or getattr(image, "image_path", None)
                or getattr(image, "url", None)
            )

    except (AttributeError, TypeError):
        pass

    return None


def _serialize_wishlist_item(item):
    """Serialize a wishlist item with product details."""
    product = item.product

    if product is None:
        return None

    price = Decimal(str(product.price))
    effective_price = _get_product_price(product)

    discount_percentage = 0

    if price > 0 and effective_price < price:
        discount_percentage = int(
            ((price - effective_price) / price) * 100
        )

    return {
        "wishlist_item_id": item.id,
        "product_id": product.id,
        "product_name": product.product_name,
        "slug": product.slug,
        "sku": product.sku,
        "description": product.description,
        "brand": product.brand,
        "price": str(price),
        "discount_price": (
            str(product.discount_price)
            if product.discount_price is not None
            else None
        ),
        "effective_price": str(effective_price),
        "discount_percentage": discount_percentage,
        "stock_quantity": product.stock_quantity,
        "is_active": product.is_active,
        "image_url": _get_product_image(product),
        "created_at": (
            item.created_at.isoformat()
            if item.created_at
            else None
        ),
    }


def _serialize_wishlist(items, user_id):
    """Build the wishlist response."""
    serialized_items = []

    for item in items:
        serialized_item = _serialize_wishlist_item(item)

        if serialized_item is not None:
            serialized_items.append(serialized_item)

    return {
        "user_id": user_id,
        "items": serialized_items,
        "item_count": len(serialized_items),
    }


def get_wishlist(user_id):
    """Fetch the logged-in customer's wishlist."""
    try:
        items = db.session.execute(
            select(Wishlist)
            .where(Wishlist.user_id == user_id)
            .order_by(Wishlist.created_at.desc())
        ).scalars().all()

        result = _serialize_wishlist(items, user_id)

        return {
            "success": True,
            "message": "Wishlist fetched successfully.",
            "wishlist": result,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to fetch wishlist.",
        }, 500


def add_to_wishlist(user_id, product_id):
    """Add a product to the customer's wishlist."""
    if isinstance(product_id, bool) or not isinstance(product_id, int):
        return {
            "success": False,
            "message": "product_id must be an integer.",
        }, 400

    if product_id <= 0:
        return {
            "success": False,
            "message": "product_id must be greater than zero.",
        }, 400

    try:
        product = db.session.get(Product, product_id)

        if product is None:
            return {
                "success": False,
                "message": "Product not found.",
            }, 404

        if not product.is_active:
            return {
                "success": False,
                "message": "This product is not available.",
            }, 400

        existing_item = db.session.execute(
            select(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id == product_id,
            )
        ).scalar_one_or_none()

        if existing_item is not None:
            return {
                "success": False,
                "message": "Product is already in your wishlist.",
                "wishlist_item_id": existing_item.id,
            }, 409

        item = Wishlist(
            user_id=user_id,
            product_id=product_id,
        )

        db.session.add(item)
        db.session.flush()

        result = _serialize_wishlist_item(item)

        db.session.commit()

        return {
            "success": True,
            "message": "Product added to wishlist successfully.",
            "item": result,
        }, 201

    except IntegrityError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Product is already in your wishlist.",
        }, 409

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to add product to wishlist.",
        }, 500


def remove_from_wishlist(user_id, wishlist_item_id):
    """Remove only an item belonging to the logged-in customer."""
    try:
        item = db.session.execute(
            select(Wishlist).where(
                Wishlist.id == wishlist_item_id,
                Wishlist.user_id == user_id,
            )
        ).scalar_one_or_none()

        if item is None:
            return {
                "success": False,
                "message": "Wishlist item not found.",
            }, 404

        db.session.delete(item)
        db.session.commit()

        return {
            "success": True,
            "message": "Product removed from wishlist successfully.",
            "wishlist_item_id": wishlist_item_id,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to remove wishlist item.",
        }, 500


def clear_wishlist(user_id):
    """Clear only the logged-in customer's wishlist."""
    try:
        items = db.session.execute(
            select(Wishlist).where(
                Wishlist.user_id == user_id
            )
        ).scalars().all()

        if not items:
            return {
                "success": True,
                "message": "Wishlist is already empty.",
                "wishlist": {
                    "user_id": user_id,
                    "items": [],
                    "item_count": 0,
                },
            }, 200

        for item in items:
            db.session.delete(item)

        db.session.commit()

        return {
            "success": True,
            "message": "Wishlist cleared successfully.",
            "wishlist": {
                "user_id": user_id,
                "items": [],
                "item_count": 0,
            },
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to clear wishlist.",
        }, 500
 