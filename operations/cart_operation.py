from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from tables.cart_table import Cart
from tables.cart_item_table import CartItem
from tables.product_table import Product


def _get_product_price(product):
    """Return the effective product price from the database."""
    if product.discount_price is not None:
        return Decimal(str(product.discount_price))

    return Decimal(str(product.price))


def _get_product_image(product):
    """Return the first product image URL when available."""
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


def _serialize_cart(cart):
    """Build a cart response containing product details and totals."""
    items = []
    subtotal = Decimal("0.00")

    for item in cart.items:
        product = item.product

        if product is None:
            continue

        unit_price = _get_product_price(product)
        line_total = unit_price * item.quantity
        subtotal += line_total

        items.append({
            "cart_item_id": item.id,
            "product_id": product.id,
            "product_name": product.product_name,
            "sku": product.sku,
            "image_url": _get_product_image(product),
            "quantity": item.quantity,
            "unit_price": str(unit_price),
            "line_total": str(line_total),
            "available_stock": product.stock_quantity,
            "is_active": product.is_active,
        })

    return {
        "cart_id": cart.id,
        "user_id": cart.user_id,
        "items": items,
        "item_count": len(items),
        "total_quantity": sum(item["quantity"] for item in items),
        "subtotal": str(subtotal),
        "created_at": (
            cart.created_at.isoformat() if cart.created_at else None
        ),
        "updated_at": (
            cart.updated_at.isoformat() if cart.updated_at else None
        ),
    }


def get_or_create_cart(user_id):
    """Fetch the user's cart or create one if it does not exist."""
    try:
        cart = db.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        ).scalar_one_or_none()

        if cart is None:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.flush()

        return cart

    except SQLAlchemyError:
        db.session.rollback()
        raise


def get_cart(user_id):
    """Get the current user's cart."""
    try:
        cart = get_or_create_cart(user_id)
        result = _serialize_cart(cart)
        db.session.commit()

        return {
            "success": True,
            "message": "Cart fetched successfully.",
            "cart": result,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to fetch cart.",
        }, 500


def add_item_to_cart(user_id, product_id, quantity):
    """Add a product to the cart or increase its quantity."""
    if isinstance(product_id, bool) or not isinstance(product_id, int):
        return {
            "success": False,
            "message": "product_id must be an integer.",
        }, 400

    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return {
            "success": False,
            "message": "quantity must be an integer.",
        }, 400

    if product_id <= 0 or quantity <= 0:
        return {
            "success": False,
            "message": "product_id and quantity must be greater than zero.",
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

        if product.stock_quantity < quantity:
            return {
                "success": False,
                "message": "Requested quantity exceeds available stock.",
                "available_stock": product.stock_quantity,
            }, 400

        cart = get_or_create_cart(user_id)

        item = db.session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product.id,
            )
        ).scalar_one_or_none()

        if item:
            new_quantity = item.quantity + quantity

            if new_quantity > product.stock_quantity:
                db.session.rollback()
                return {
                    "success": False,
                    "message": "Requested quantity exceeds available stock.",
                    "available_stock": product.stock_quantity,
                    "current_quantity": item.quantity,
                }, 400

            item.quantity = new_quantity
        else:
            item = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=quantity,
            )
            db.session.add(item)

        db.session.flush()
        result = _serialize_cart(cart)
        db.session.commit()

        return {
            "success": True,
            "message": "Product added to cart successfully.",
            "cart": result,
        }, 201

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to add product to cart.",
        }, 500


def update_cart_item(user_id, cart_item_id, quantity):
    """Update the quantity of an item belonging to this user's cart."""
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return {
            "success": False,
            "message": "quantity must be an integer.",
        }, 400

    if quantity <= 0:
        return {
            "success": False,
            "message": "quantity must be greater than zero.",
        }, 400

    try:
        item = db.session.execute(
            select(CartItem)
            .join(Cart, Cart.id == CartItem.cart_id)
            .where(
                CartItem.id == cart_item_id,
                Cart.user_id == user_id,
            )
        ).scalar_one_or_none()

        if item is None:
            return {
                "success": False,
                "message": "Cart item not found.",
            }, 404

        product = item.product

        if product is None or not product.is_active:
            return {
                "success": False,
                "message": "This product is not available.",
            }, 400

        if quantity > product.stock_quantity:
            return {
                "success": False,
                "message": "Requested quantity exceeds available stock.",
                "available_stock": product.stock_quantity,
            }, 400

        item.quantity = quantity
        db.session.flush()
        result = _serialize_cart(item.cart)
        db.session.commit()

        return {
            "success": True,
            "message": "Cart quantity updated successfully.",
            "cart": result,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to update cart item.",
        }, 500


def remove_cart_item(user_id, cart_item_id):
    """Remove an item only from the current user's cart."""
    try:
        item = db.session.execute(
            select(CartItem)
            .join(Cart, Cart.id == CartItem.cart_id)
            .where(
                CartItem.id == cart_item_id,
                Cart.user_id == user_id,
            )
        ).scalar_one_or_none()

        if item is None:
            return {
                "success": False,
                "message": "Cart item not found.",
            }, 404

        cart = item.cart
        db.session.delete(item)
        db.session.flush()

        result = _serialize_cart(cart)
        db.session.commit()

        return {
            "success": True,
            "message": "Product removed from cart successfully.",
            "cart": result,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to remove cart item.",
        }, 500


def clear_cart(user_id):
    """Remove all items from the current user's cart."""
    try:
        cart = db.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        ).scalar_one_or_none()

        if cart is None:
            return {
                "success": True,
                "message": "Cart is already empty.",
                "cart": None,
            }, 200

        cart.items.clear()
        db.session.flush()

        result = _serialize_cart(cart)
        db.session.commit()

        return {
            "success": True,
            "message": "Cart cleared successfully.",
            "cart": result,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to clear cart.",
        }, 500
 