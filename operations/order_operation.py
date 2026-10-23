from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

from tables.order_table import Order
from tables.order_item_table import OrderItem
from tables.cart_table import Cart
from tables.cart_item_table import CartItem
from tables.product_table import Product
from tables.address_table import Address


# =========================================================
# Helpers
# =========================================================

def _get_product_price(product):
    """Return the effective selling price."""
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


def _money(value):
    """Normalize a monetary value to two decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _error(message, status_code):
    return {
        "success": False,
        "message": message,
    }, status_code


# =========================================================
# Create Order
# =========================================================

def create_order(user_id, data):
    """
    Create an order from the logged-in customer's cart.

    Required JSON:
    {
        "address_id": 1,
        "notes": "Optional delivery instructions"
    }
    """

    if not isinstance(data, dict):
        return _error("Invalid request body.", 400)

    address_id = data.get("address_id")

    if isinstance(address_id, bool) or not isinstance(address_id, int):
        return _error("address_id must be an integer.", 400)

    if address_id <= 0:
        return _error("address_id must be greater than zero.", 400)

    notes = data.get("notes")

    if notes is not None and not isinstance(notes, str):
        return _error("notes must be a string.", 400)

    if notes is not None:
        notes = notes.strip() or None

        if len(notes) > 5000:
            return _error("notes must not exceed 5000 characters.", 400)

    try:
        # Verify that the address belongs to the logged-in customer.
        address = db.session.execute(
            select(Address).where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
        ).scalar_one_or_none()

        if address is None:
            db.session.rollback()
            return _error(
                "Delivery address not found for this customer.",
                404,
            )

        # Lock the cart row where supported by the database.
        cart = db.session.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .with_for_update()
        ).scalar_one_or_none()

        if cart is None:
            db.session.rollback()
            return _error("Your cart is empty.", 400)

        # Lock cart items and load them.
        cart_items = db.session.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .with_for_update()
        ).scalars().all()

        if not cart_items:
            db.session.rollback()
            return _error("Your cart is empty.", 400)

        # Validate every product before creating the order.
        order_lines = []
        subtotal = Decimal("0.00")

        for cart_item in cart_items:
            # Lock the product row where supported.
            product = db.session.execute(
                select(Product)
                .where(Product.id == cart_item.product_id)
                .with_for_update()
            ).scalar_one_or_none()

            if product is None:
                db.session.rollback()
                return _error(
                    f"Product {cart_item.product_id} no longer exists.",
                    400,
                )

            if not product.is_active:
                db.session.rollback()
                return _error(
                    f"Product '{product.product_name}' is unavailable.",
                    400,
                )

            if cart_item.quantity > product.stock_quantity:
                db.session.rollback()
                return {
                    "success": False,
                    "message": (
                        f"Insufficient stock for '{product.product_name}'."
                    ),
                    "product_id": product.id,
                    "requested_quantity": cart_item.quantity,
                    "available_stock": product.stock_quantity,
                }, 400

            unit_price = _money(_get_product_price(product))

            if unit_price < 0:
                db.session.rollback()
                return _error(
                    f"Invalid price for '{product.product_name}'.",
                    400,
                )

            line_total = _money(unit_price * cart_item.quantity)
            subtotal += line_total

            order_lines.append({
                "product": product,
                "quantity": cart_item.quantity,
                "unit_price": unit_price,
                "line_total": line_total,
                "product_name": product.product_name,
                "sku": product.sku,
                "image_url": _get_product_image(product),
            })

        subtotal = _money(subtotal)

        # Current model does not define shipping/tax calculation rules.
        discount_amount = Decimal("0.00")
        shipping_amount = Decimal("0.00")
        tax_amount = Decimal("0.00")

        total_amount = _money(
            subtotal
            - discount_amount
            + shipping_amount
            + tax_amount
        )

        # Create the order.
        order = Order(
            order_number=f"ORD-{uuid4().hex[:16].upper()}",
            user_id=user_id,
            address_id=address.id,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_amount=shipping_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            payment_status="pending",
            order_status="placed",
            notes=notes,
        )

        db.session.add(order)
        db.session.flush()

        # Save product snapshots and deduct stock.
        for line in order_lines:
            product = line["product"]

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=line["product_name"],
                product_image_url=line["image_url"],
                sku=line["sku"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                discount_amount=Decimal("0.00"),
                total_price=line["line_total"],
            )

            db.session.add(order_item)

            product.stock_quantity -= line["quantity"]

        # Clear cart only after order creation logic succeeds.
        cart.items.clear()

        db.session.flush()

        # Build the response before committing.
        response_data = order.to_dict()

        db.session.commit()

        return {
            "success": True,
            "message": "Order created successfully.",
            "data": response_data,
        }, 201

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to create order. Please try again.",
            500,
        )

    except (InvalidOperation, ValueError, TypeError):
        db.session.rollback()

        return _error(
            "Unable to calculate order prices.",
            400,
        )


# =========================================================
# Get All Orders of Customer
# =========================================================

def get_customer_orders(user_id):
    """Return orders belonging only to the specified customer."""

    try:
        orders = db.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
        ).scalars().all()

        return {
            "success": True,
            "message": "Orders fetched successfully.",
            "data": [order.to_dict() for order in orders],
            "count": len(orders),
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to fetch orders.",
            500,
        )


# =========================================================
# Get Single Order
# =========================================================

def get_customer_order_by_id(user_id, order_id):
    """Return a single order only if it belongs to this customer."""

    if order_id <= 0:
        return _error("Invalid order ID.", 400)

    try:
        order = db.session.execute(
            select(Order).where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
        ).scalar_one_or_none()

        if order is None:
            return _error("Order not found.", 404)

        return {
            "success": True,
            "message": "Order fetched successfully.",
            "data": order.to_dict(),
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to fetch order.",
            500,
        )
 