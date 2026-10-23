from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.cart_operation import (
    get_cart,
    add_item_to_cart,
    update_cart_item,
    remove_cart_item,
    clear_cart,
)


cart_bp = Blueprint(
    "cart",
    __name__,
    url_prefix="/api/v1/cart",
)


@cart_bp.route("", methods=["GET"])
@token_required
@role_required("customer")
def fetch_cart():
    """Get the logged-in customer's cart."""
    user_id = int(get_jwt_identity())

    result, status_code = get_cart(user_id)
    return result, status_code


@cart_bp.route("/items", methods=["POST"])
@token_required
@role_required("customer")
def add_cart_item():
    """Add a product to the cart."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "Request body must be valid JSON.",
        }, 400

    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

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

    user_id = int(get_jwt_identity())

    result, status_code = add_item_to_cart(
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
    )

    return result, status_code


@cart_bp.route("/items/<int:cart_item_id>", methods=["PATCH"])
@token_required
@role_required("customer")
def update_cart_item_quantity(cart_item_id):
    """Update a cart item's quantity."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "Request body must be valid JSON.",
        }, 400

    quantity = data.get("quantity")

    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return {
            "success": False,
            "message": "quantity must be an integer.",
        }, 400

    user_id = int(get_jwt_identity())

    result, status_code = update_cart_item(
        user_id=user_id,
        cart_item_id=cart_item_id,
        quantity=quantity,
    )

    return result, status_code


@cart_bp.route("/items/<int:cart_item_id>", methods=["DELETE"])
@token_required
@role_required("customer")
def delete_cart_item(cart_item_id):
    """Remove a cart item."""
    user_id = int(get_jwt_identity())

    result, status_code = remove_cart_item(
        user_id=user_id,
        cart_item_id=cart_item_id,
    )

    return result, status_code


@cart_bp.route("", methods=["DELETE"])
@token_required
@role_required("customer")
def delete_cart():
    """Clear the logged-in customer's cart."""
    user_id = int(get_jwt_identity())

    result, status_code = clear_cart(user_id)
    return result, status_code
 