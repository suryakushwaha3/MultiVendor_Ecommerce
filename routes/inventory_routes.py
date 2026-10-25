from functools import wraps

from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import (
    get_jwt_identity,
    verify_jwt_in_request,
)
from flask_jwt_extended.exceptions import JWTExtendedException

from app.extensions import db

from middleware.vendor_middleware import vendor_required

from tables.user_table import User
from tables.store_table import Store
from tables.product_table import Product

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
# Standard Error Response
# =========================================================

def error_response(message, status_code, errors=None):
    response = {
        "success": False,
        "message": message,
    }

    if errors is not None:
        response["errors"] = errors

    return jsonify(response), status_code


# =========================================================
# Authentication and Authorization
#
# Admin identity: "1", "2", etc.
# Vendor identity: "vendor:1", "vendor:2", etc.
# =========================================================

def inventory_access_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        # Verify JWT before reading identity.
        try:
            verify_jwt_in_request()

        except JWTExtendedException:
            return error_response(
                "Authentication required. Please provide a valid access token.",
                401,
            )

        identity = get_jwt_identity()

        # -------------------------------------------------
        # Vendor authentication
        # -------------------------------------------------

        if (
            isinstance(identity, str)
            and identity.startswith("vendor:")
        ):
            # Existing middleware validates vendor existence,
            # active status, approval status and vendor identity.
            #
            # It sets g.vendor_id after successful validation.
            return vendor_required(fn)(*args, **kwargs)

        # -------------------------------------------------
        # Admin authentication
        # -------------------------------------------------

        try:
            user_id = int(identity)

        except (TypeError, ValueError, OverflowError):
            return error_response(
                "Invalid authentication identity.",
                401,
            )

        if user_id <= 0:
            return error_response(
                "Invalid authentication identity.",
                401,
            )

        user = db.session.get(User, user_id)

        if user is None:
            return error_response(
                "User not found.",
                401,
            )

        if not user.is_active:
            return error_response(
                "Your account is inactive.",
                403,
            )

        if user.role != "admin":
            return error_response(
                "You do not have permission to access this resource.",
                403,
            )

        g.inventory_user = user
        g.inventory_actor_type = "admin"
        g.inventory_actor_id = user.id

        return fn(*args, **kwargs)

    return wrapper


# =========================================================
# Get Authenticated Actor
# =========================================================

def get_inventory_actor():

    vendor_id = getattr(g, "vendor_id", None)

    if vendor_id is not None:
        return "vendor", vendor_id

    user = getattr(g, "inventory_user", None)

    if user is not None:
        return "admin", user.id

    return None, None


# =========================================================
# Pagination Validation
# =========================================================

def get_pagination():

    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

    except (TypeError, ValueError, OverflowError):
        return (
            None,
            None,
            error_response(
                "Limit and offset must be integers.",
                400,
            ),
        )

    if limit < 1 or limit > 100:
        return (
            None,
            None,
            error_response(
                "Limit must be between 1 and 100.",
                400,
            ),
        )

    if offset < 0:
        return (
            None,
            None,
            error_response(
                "Offset cannot be negative.",
                400,
            ),
        )

    return limit, offset, None


# =========================================================
# Query Parameter ID Validation
# =========================================================

def get_positive_query_id(parameter_name):

    raw_value = request.args.get(parameter_name)

    if raw_value is None:
        return None, None

    try:
        value = int(raw_value)

    except (TypeError, ValueError, OverflowError):
        return (
            None,
            error_response(
                f"{parameter_name} must be an integer.",
                400,
            ),
        )

    if value <= 0:
        return (
            None,
            error_response(
                f"{parameter_name} must be a positive integer.",
                400,
            ),
        )

    return value, None


# =========================================================
# Vendor Ownership Helpers
# =========================================================

def get_vendor_store(store_id, vendor_id):

    return Store.query.filter_by(
        id=store_id,
        vendor_id=vendor_id,
    ).first()


def get_vendor_product(product_id, vendor_id):

    product = db.session.get(Product, product_id)

    if product is None:
        return None

    store = get_vendor_store(
        store_id=product.store_id,
        vendor_id=vendor_id,
    )

    if store is None:
        return None

    return product


# =========================================================
# GET /inventory
#
# Admin:
#     Can access all inventory records.
#
# Vendor:
#     Can access inventory records belonging to their stores.
# =========================================================

@inventory_bp.route("/inventory", methods=["GET"])
@inventory_access_required
def inventory_history():

    actor_type, actor_id = get_inventory_actor()

    if actor_type is None or actor_id is None:
        return error_response(
            "Unable to resolve authenticated actor.",
            401,
        )

    # Validate pagination.
    limit, offset, error = get_pagination()

    if error:
        return error

    # Validate optional query parameters.
    store_id, error = get_positive_query_id("store_id")

    if error:
        return error

    product_id, error = get_positive_query_id("product_id")

    if error:
        return error

    movement_type = request.args.get("movement_type")

    vendor_id = None

    # -----------------------------------------------------
    # Vendor ownership validation
    # -----------------------------------------------------

    if actor_type == "vendor":

        vendor_id = actor_id

        # Requested store must belong to this vendor.
        if store_id is not None:

            store = get_vendor_store(
                store_id=store_id,
                vendor_id=vendor_id,
            )

            if store is None:
                return error_response(
                    "Store not found or access denied.",
                    403,
                )

        # Requested product must belong to this vendor.
        if product_id is not None:

            product = get_vendor_product(
                product_id=product_id,
                vendor_id=vendor_id,
            )

            if product is None:
                return error_response(
                    "Product not found or access denied.",
                    403,
                )

            # Product must also belong to the requested store.
            if (
                store_id is not None
                and product.store_id != store_id
            ):
                return error_response(
                    "The product does not belong to the requested store.",
                    403,
                )

    # -----------------------------------------------------
    # Fetch inventory history
    # -----------------------------------------------------

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
# GET /inventory/product/<product_id>
#
# Admin:
#     Can view product inventory history.
#
# Vendor:
#     Can view only their own product inventory history.
# =========================================================

@inventory_bp.route(
    "/inventory/product/<int:product_id>",
    methods=["GET"],
)
@inventory_access_required
def inventory_history_by_product(product_id):

    actor_type, actor_id = get_inventory_actor()

    if actor_type is None or actor_id is None:
        return error_response(
            "Unable to resolve authenticated actor.",
            401,
        )

    if product_id <= 0:
        return error_response(
            "Invalid product ID.",
            400,
        )

    limit, offset, error = get_pagination()

    if error:
        return error

    vendor_id = None

    # -----------------------------------------------------
    # Verify vendor owns the product
    # -----------------------------------------------------

    if actor_type == "vendor":

        vendor_id = actor_id

        product = get_vendor_product(
            product_id=product_id,
            vendor_id=vendor_id,
        )

        if product is None:
            return error_response(
                "Product not found or access denied.",
                403,
            )

    # -----------------------------------------------------
    # Fetch product inventory history
    # -----------------------------------------------------

    result, status_code = get_inventory_history_by_product(
        product_id=product_id,
        vendor_id=vendor_id,
        limit=limit,
        offset=offset,
    )

    return jsonify(result), status_code


# =========================================================
# POST /inventory/movement
#
# Admin:
#     Can record an authorized inventory movement.
#
# Vendor:
#     Can modify inventory only for their own store.
# =========================================================

@inventory_bp.route(
    "/inventory/movement",
    methods=["POST"],
)
@inventory_access_required
def create_inventory_movement():

    actor_type, actor_id = get_inventory_actor()

    if actor_type is None or actor_id is None:
        return error_response(
            "Unable to resolve authenticated actor.",
            401,
        )

    # -----------------------------------------------------
    # Validate JSON body
    # -----------------------------------------------------

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "Request body must be a valid JSON object.",
            400,
        )

    required_fields = {
        "product_id",
        "quantity_change",
        "movement_type",
    }

    missing_fields = required_fields - data.keys()

    if missing_fields:
        return error_response(
            "Missing required fields.",
            400,
            {
                "missing_fields": sorted(missing_fields),
            },
        )

    # -----------------------------------------------------
    # Validate product_id
    # -----------------------------------------------------

    product_id = data["product_id"]

    if isinstance(product_id, bool):
        return error_response(
            "Product ID must be an integer.",
            400,
        )

    if not isinstance(product_id, (int, str)):
        return error_response(
            "Product ID must be an integer.",
            400,
        )

    try:
        product_id = int(product_id)

    except (TypeError, ValueError, OverflowError):
        return error_response(
            "Product ID must be an integer.",
            400,
        )

    if product_id <= 0:
        return error_response(
            "Product ID must be positive.",
            400,
        )

    # -----------------------------------------------------
    # Validate quantity_change
    # -----------------------------------------------------

    quantity_change = data["quantity_change"]

    if isinstance(quantity_change, bool):
        return error_response(
            "Quantity change must be an integer.",
            400,
        )

    if not isinstance(quantity_change, (int, str)):
        return error_response(
            "Quantity change must be an integer.",
            400,
        )

    try:
        quantity_change = int(quantity_change)

    except (TypeError, ValueError, OverflowError):
        return error_response(
            "Quantity change must be an integer.",
            400,
        )

    if quantity_change == 0:
        return error_response(
            "Quantity change cannot be zero.",
            400,
        )

    # -----------------------------------------------------
    # Validate movement_type
    # -----------------------------------------------------

    movement_type = data["movement_type"]

    if not isinstance(movement_type, str):
        return error_response(
            "Movement type must be a string.",
            400,
        )

    movement_type = movement_type.strip()

    if not movement_type:
        return error_response(
            "Movement type cannot be empty.",
            400,
        )

    # -----------------------------------------------------
    # Validate optional store_id
    # -----------------------------------------------------

    store_id = data.get("store_id")

    if store_id is not None:

        if isinstance(store_id, bool):
            return error_response(
                "Store ID must be an integer.",
                400,
            )

        if not isinstance(store_id, (int, str)):
            return error_response(
                "Store ID must be an integer.",
                400,
            )

        try:
            store_id = int(store_id)

        except (TypeError, ValueError, OverflowError):
            return error_response(
                "Store ID must be an integer.",
                400,
            )

        if store_id <= 0:
            return error_response(
                "Store ID must be positive.",
                400,
            )

    # -----------------------------------------------------
    # Verify product exists
    # -----------------------------------------------------

    product = db.session.get(Product, product_id)

    if product is None:
        return error_response(
            "Product not found.",
            404,
        )

    # -----------------------------------------------------
    # Vendor-specific ownership validation
    # -----------------------------------------------------

    if actor_type == "vendor":

        # Vendor must provide store_id.
        if store_id is None:
            return error_response(
                "store_id is required for vendors.",
                400,
            )

        # Store must belong to the authenticated vendor.
        store = get_vendor_store(
            store_id=store_id,
            vendor_id=actor_id,
        )

        if store is None:
            return error_response(
                "Store not found or access denied.",
                403,
            )

        # Product must belong to the selected store.
        if product.store_id != store.id:
            return error_response(
                "The product does not belong to your selected store.",
                403,
            )

    # -----------------------------------------------------
    # Admin-specific store/product validation
    # -----------------------------------------------------

    if actor_type == "admin" and store_id is not None:

        store = db.session.get(Store, store_id)

        if store is None:
            return error_response(
                "Store not found.",
                404,
            )

        # FIX: Product-store mismatch returns 403.
        if product.store_id != store.id:
            return error_response(
                "The product does not belong to the selected store.",
                403,
            )

    # -----------------------------------------------------
    # Record inventory movement
    # -----------------------------------------------------

    result, status_code = record_inventory_movement(
        product_id=product_id,
        quantity_change=quantity_change,
        movement_type=movement_type,
        store_id=store_id,
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        note=data.get("note"),
        created_by_type=actor_type,
        created_by_id=actor_id,
    )

    return jsonify(result), status_code