from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.wishlist_operation import (
    get_wishlist,
    add_to_wishlist,
    remove_from_wishlist,
    clear_wishlist,
)


wishlist_bp = Blueprint(
    "wishlist",
    __name__,
    url_prefix="/api/v1/wishlist",
)


@wishlist_bp.route("", methods=["GET"])
@token_required
@role_required("customer")
def fetch_wishlist():
    """Get the logged-in customer's wishlist."""
    user_id = int(get_jwt_identity())

    result, status_code = get_wishlist(user_id)
    return result, status_code


@wishlist_bp.route("/items", methods=["POST"])
@token_required
@role_required("customer")
def add_wishlist_item():
    """Add a product to the wishlist."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "Request body must be valid JSON.",
        }, 400

    product_id = data.get("product_id")

    if isinstance(product_id, bool) or not isinstance(product_id, int):
        return {
            "success": False,
            "message": "product_id must be an integer.",
        }, 400

    user_id = int(get_jwt_identity())

    result, status_code = add_to_wishlist(
        user_id=user_id,
        product_id=product_id,
    )

    return result, status_code


@wishlist_bp.route("/items/<int:wishlist_item_id>", methods=["DELETE"])
@token_required
@role_required("customer")
def delete_wishlist_item(wishlist_item_id):
    """Remove an item from the logged-in customer's wishlist."""
    user_id = int(get_jwt_identity())

    result, status_code = remove_from_wishlist(
        user_id=user_id,
        wishlist_item_id=wishlist_item_id,
    )

    return result, status_code


@wishlist_bp.route("", methods=["DELETE"])
@token_required
@role_required("customer")
def delete_wishlist():
    """Clear the logged-in customer's wishlist."""
    user_id = int(get_jwt_identity())

    result, status_code = clear_wishlist(user_id)
    return result, status_code
 