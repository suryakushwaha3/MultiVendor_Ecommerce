from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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
# Constants
# =========================================================

ZERO = Decimal("0.00")
ONE_CENT = Decimal("0.01")

MAX_NOTES_LENGTH = 5000


# =========================================================
# Helpers
# =========================================================

def _error(message, status_code):
    """Build a consistent error response."""
    return {
        "success": False,
        "message": message,
    }, status_code


def _money(value):
    """
    Convert a value to a finite Decimal with two decimal places.

    ROUND_HALF_UP is used for predictable monetary rounding.
    """
    try:
        amount = Decimal(str(value))

        if not amount.is_finite():
            raise ValueError("Monetary value must be finite.")

        return amount.quantize(
            ONE_CENT,
            rounding=ROUND_HALF_UP,
        )

    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid monetary value.") from exc


def _validate_product_price(product):
    """
    Validate product prices and return the effective selling price.

    Rules:
    - Base price must be finite and non-negative.
    - Discount price, when provided, must be finite and non-negative.
    - Discount price cannot exceed the base price.
    """
    try:
        base_price = Decimal(str(product.price))

        if not base_price.is_finite() or base_price < 0:
            raise ValueError("Invalid base price.")

        if product.discount_price is not None:
            discount_price = Decimal(str(product.discount_price))

            if not discount_price.is_finite():
                raise ValueError("Invalid discount price.")

            if discount_price < 0:
                raise ValueError("Invalid discount price.")

            if discount_price > base_price:
                raise ValueError(
                    "Discount price cannot exceed base price."
                )

            effective_price = discount_price
        else:
            effective_price = base_price

        return _money(effective_price)

    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid product price.") from exc


def _get_product_image(product):
    """Return the first product image URL when available."""
    try:
        images = product.images

        if not images:
            return None

        image = images[0]

        if isinstance(image, dict):
            return image.get("image_url") or image.get("url")

        return (
            getattr(image, "image_url", None)
            or getattr(image, "image_path", None)
            or getattr(image, "url", None)
        )

    except (AttributeError, TypeError):
        return None


def _validate_quantity(quantity):
    """Return True only for a positive integer quantity."""
    return (
        isinstance(quantity, int)
        and not isinstance(quantity, bool)
        and quantity > 0
    )


# =========================================================
# Create Order
# =========================================================

def create_order(user_id, data):
    """
    Create an order from the authenticated customer's cart.

    Required JSON:
    {
        "address_id": 1,
        "notes": "Optional delivery instructions"
    }

    The order, order items, stock updates and cart clearing
    are committed together in a single database transaction.
    """

    # -----------------------------------------------------
    # 1. Validate request data
    # -----------------------------------------------------

    if not isinstance(data, dict):
        return _error("Invalid request body.", 400)

    address_id = data.get("address_id")

    if (
        isinstance(address_id, bool)
        or not isinstance(address_id, int)
    ):
        return _error(
            "address_id must be an integer.",
            400,
        )

    if address_id <= 0:
        return _error(
            "address_id must be greater than zero.",
            400,
        )

    notes = data.get("notes")

    if notes is not None and not isinstance(notes, str):
        return _error("notes must be a string.", 400)

    if notes is not None:
        notes = notes.strip() or None

        if notes is not None and len(notes) > MAX_NOTES_LENGTH:
            return _error(
                f"notes must not exceed {MAX_NOTES_LENGTH} characters.",
                400,
            )

    # -----------------------------------------------------
    # 2. Database transaction
    # -----------------------------------------------------

    try:
        # -------------------------------------------------
        # 2.1 Verify customer-owned delivery address
        # -------------------------------------------------

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

        # -------------------------------------------------
        # 2.2 Load and lock the customer's cart
        # -------------------------------------------------

        cart = db.session.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .with_for_update()
        ).scalar_one_or_none()

        if cart is None:
            db.session.rollback()

            return _error(
                "Your cart is empty.",
                400,
            )

        cart_items = db.session.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .order_by(CartItem.id)
            .with_for_update()
        ).scalars().all()

        if not cart_items:
            db.session.rollback()

            return _error(
                "Your cart is empty.",
                400,
            )

        # -------------------------------------------------
        # 2.3 Validate cart quantities and products
        # -------------------------------------------------

        order_lines = []
        subtotal = ZERO

        for cart_item in cart_items:

            if not _validate_quantity(cart_item.quantity):
                db.session.rollback()

                return _error(
                    "Cart contains an invalid product quantity.",
                    400,
                )

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

            # Validate stock before making any changes.
            stock = product.stock_quantity

            if (
                isinstance(stock, bool)
                or not isinstance(stock, int)
                or stock < 0
            ):
                db.session.rollback()

                return _error(
                    f"Invalid stock quantity for '{product.product_name}'.",
                    400,
                )

            if cart_item.quantity > stock:
                db.session.rollback()

                return {
                    "success": False,
                    "message": (
                        f"Insufficient stock for "
                        f"'{product.product_name}'."
                    ),
                    "product_id": product.id,
                    "requested_quantity": cart_item.quantity,
                    "available_stock": stock,
                }, 400

            # ---------------------------------------------
            # 2.4 Validate price
            # ---------------------------------------------

            try:
                unit_price = _validate_product_price(product)

                line_total = _money(
                    unit_price * cart_item.quantity
                )

            except (ValueError, InvalidOperation, TypeError):
                db.session.rollback()

                return _error(
                    f"Invalid price for '{product.product_name}'.",
                    400,
                )

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

        # -------------------------------------------------
        # 2.5 Calculate order totals
        # -------------------------------------------------

        subtotal = _money(subtotal)

        # Shipping, discount and tax rules have not yet
        # been implemented in the current project.
        discount_amount = ZERO
        shipping_amount = ZERO
        tax_amount = ZERO

        total_amount = _money(
            subtotal
            - discount_amount
            + shipping_amount
            + tax_amount
        )

        if total_amount < ZERO:
            db.session.rollback()

            return _error(
                "Invalid order total.",
                400,
            )

        # -------------------------------------------------
        # 2.6 Create order
        # -------------------------------------------------

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

        # Obtain the generated order ID.
        db.session.flush()

        # -------------------------------------------------
        # 2.7 Create order items and deduct stock
        # -------------------------------------------------

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
                discount_amount=ZERO,
                total_price=line["line_total"],
            )

            db.session.add(order_item)

            product.stock_quantity -= line["quantity"]

        # -------------------------------------------------
        # 2.8 Clear cart within the same transaction
        # -------------------------------------------------

        cart.items.clear()

        # Flush all pending database changes.
        db.session.flush()

        # Serialize before committing, while the objects
        # and their relationships are available.
        response_data = order.to_dict()

        # -------------------------------------------------
        # 2.9 Commit everything together
        # -------------------------------------------------

        db.session.commit()

        return {
            "success": True,
            "message": "Order created successfully.",
            "data": response_data,
        }, 201

    except SQLAlchemyError:
        # Roll back order, order items, stock changes and
        # cart changes if a database operation fails.
        db.session.rollback()

        return _error(
            "Unable to create order. Please try again.",
            500,
        )

    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
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
            .order_by(
                Order.created_at.desc(),
                Order.id.desc(),
            )
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
    """Return an order only if it belongs to this customer."""

    if (
        isinstance(order_id, bool)
        or not isinstance(order_id, int)
        or order_id <= 0
    ):
        return _error("Invalid order ID.", 400)

    try:
        order = db.session.execute(
            select(Order).where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
        ).scalar_one_or_none()

        if order is None:
            return _error(
                "Order not found.",
                404,
            )

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
 