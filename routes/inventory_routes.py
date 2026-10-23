from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from tables.user_table import User
from tables.vendor_table import Vendor
from tables.store_table import Store

from operations.inventory_operation import (
    record_inventory_movement,
    get_inventory_history,
    get_inventory_history_by_product,
)


# =========================================================
# Inventory Blueprint
# =========================================================

inventory_bp = Blueprint("inventory", __name__)


# =========================================================
# Helper: Resolve authenticated user
# =========================================================

def get_current_user():
    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None, (
            jsonify({
                "success": False,
                "message": "Invalid authentication identity."
            }),
            401
        )

    user = db.session.get(User, user_id)

    if user is None:
        return None, (
            jsonify({
                "success": False,
                "message": "User not found."
            }),
            404
        )

    if not user.is_active:
        return None, (
            jsonify({
                "success": False,
                "message": "Your account is inactive."
            }),
            403
        )

    return user, None


# =========================================================
# Helper: Resolve vendor ID
# =========================================================

def get_current_vendor_id(user):
    vendor = Vendor.query.filter_by(user_id=user.id).first()

    if vendor is None:
        return None

    return vendor.id


# =========================================================
# Helper: Parse pagination
# =========================================================

def get_pagination():
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

    except (TypeError, ValueError):
        return None, None, (
            jsonify({
                "success": False,
                "message": "Limit and offset must be integers."
            }),
            400
        )

    if limit < 1 or limit > 100 or offset < 0:
        return None, None, (
            jsonify({
                "success": False,
                "message": (
                    "Limit must be 1-100 and "
                    "offset cannot be negative."
                )
            }),
            400
        )

    return limit, offset, None


# =========================================================
# Get Inventory History
# GET /inventory
#
# Admin: Can access all inventory records.
# Vendor: Can access records belonging to their stores.
# =========================================================

@inventory_bp.route("/inventory", methods=["GET"])
@token_required
@role_required("admin", "vendor")
def inventory_history():
    user, error = get_current_user()

    if error:
        return error

    limit, offset, error = get_pagination()

    if error:
        return error

    store_id = request.args.get("store_id", type=int)
    product_id = request.args.get("product_id", type=int)
    movement_type = request.args.get("movement_type")

    if store_id is not None and store_id <= 0:
        return jsonify({
            "success": False,
            "message": "Invalid store ID."
        }), 400

    if product_id is not None and product_id <= 0:
        return jsonify({
            "success": False,
            "message": "Invalid product ID."
        }), 400

    vendor_id = None

    if user.role == "vendor":
        vendor_id = get_current_vendor_id(user)

        if vendor_id is None:
            return jsonify({
                "success": False,
                "message": "Vendor profile not found."
            }), 403

        # Verify that the requested store belongs to this vendor.
        if store_id is not None:
            store = Store.query.filter_by(
                id=store_id,
                vendor_id=vendor_id
            ).first()

            if store is None:
                return jsonify({
                    "success": False,
                    "message": "Store not found or access denied."
                }), 403

    result, status_code = get_inventory_history(
        vendor_id=vendor_id,
        store_id=store_id,
        product_id=product_id,
        movement_type=movement_type,
        limit=limit,
        offset=offset,
    )

    return jsonify(result), status_code


# =========================================================
# Get Inventory History By Product
# GET /inventory/product/<product_id>
# =========================================================

@inventory_bp.route(
    "/inventory/product/<int:product_id>",
    methods=["GET"]
)
@token_required
@role_required("admin", "vendor")
def inventory_history_by_product(product_id):
    user, error = get_current_user()

    if error:
        return error

    limit, offset, error = get_pagination()

    if error:
        return error

    vendor_id = None

    if user.role == "vendor":
        vendor_id = get_current_vendor_id(user)

        if vendor_id is None:
            return jsonify({
                "success": False,
                "message": "Vendor profile not found."
            }), 403

    result, status_code = get_inventory_history_by_product(
        product_id=product_id,
        vendor_id=vendor_id,
        limit=limit,
        offset=offset,
    )

    return jsonify(result), status_code


# =========================================================
# Record Inventory Movement
# POST /inventory/movement
#
# Admin and Vendor
# =========================================================

@inventory_bp.route("/inventory/movement", methods=["POST"])
@token_required
@role_required("admin", "vendor")
def create_inventory_movement():
    user, error = get_current_user()

    if error:
        return error

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be a valid JSON object."
        }), 400

    required_fields = {
        "product_id",
        "quantity_change",
        "movement_type"
    }

    missing_fields = required_fields - data.keys()

    if missing_fields:
        return jsonify({
            "success": False,
            "message": "Missing required fields.",
            "errors": {
                "missing_fields": sorted(missing_fields)
            }
        }), 400

    product_id = data["product_id"]
    quantity_change = data["quantity_change"]
    movement_type = data["movement_type"]

    # Validate product ID.
    if isinstance(product_id, bool) or not isinstance(
        product_id, (int, str)
    ):
        return jsonify({
            "success": False,
            "message": "Product ID must be an integer."
        }), 400

    # Validate quantity change.
    if isinstance(quantity_change, bool) or not isinstance(
        quantity_change, (int, str)
    ):
        return jsonify({
            "success": False,
            "message": "Quantity change must be an integer."
        }), 400

    try:
        product_id = int(product_id)
        quantity_change = int(quantity_change)

    except (TypeError, ValueError, OverflowError):
        return jsonify({
            "success": False,
            "message": (
                "Product ID and quantity change "
                "must be integers."
            )
        }), 400

    if product_id <= 0 or quantity_change == 0:
        return jsonify({
            "success": False,
            "message": (
                "Product ID must be positive and "
                "quantity change cannot be zero."
            )
        }), 400

    if not isinstance(movement_type, str):
        return jsonify({
            "success": False,
            "message": "Movement type must be a string."
        }), 400

    # Validate optional store ID.
    store_id = data.get("store_id")

    if store_id is not None:
        if isinstance(store_id, bool):
            return jsonify({
                "success": False,
                "message": "Invalid store ID."
            }), 400

        try:
            store_id = int(store_id)

        except (TypeError, ValueError, OverflowError):
            return jsonify({
                "success": False,
                "message": "Store ID must be an integer."
            }), 400

        if store_id <= 0:
            return jsonify({
                "success": False,
                "message": "Invalid store ID."
            }), 400

    # Vendor can modify inventory only for their own store.
    if user.role == "vendor":
        vendor_id = get_current_vendor_id(user)

        if vendor_id is None:
            return jsonify({
                "success": False,
                "message": "Vendor profile not found."
            }), 403

        if store_id is None:
            return jsonify({
                "success": False,
                "message": "store_id is required for vendors."
            }), 400

        store = Store.query.filter_by(
            id=store_id,
            vendor_id=vendor_id
        ).first()

        if store is None:
            return jsonify({
                "success": False,
                "message": "Store not found or access denied."
            }), 403

    # Record the movement and update stock through the operation.
    result, status_code = record_inventory_movement(
        product_id=product_id,
        quantity_change=quantity_change,
        movement_type=movement_type,
        store_id=store_id,
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        note=data.get("note"),
        created_by_type=user.role,
        created_by_id=user.id,
    )

    return jsonify(result), status_code
 