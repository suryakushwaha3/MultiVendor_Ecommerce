from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.order_operation import (
    create_order,
    get_customer_orders,
    get_customer_order_by_id,
)


order_bp = Blueprint(
    "order_bp",
    __name__,
    url_prefix="/api/v1/orders"
)


# =========================================================
# Create Order
# POST /api/v1/orders
# =========================================================

@order_bp.route("", methods=["POST"])
@token_required
@role_required("customer")
def create_order_route():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    result, status_code = create_order(
        user_id=user_id,
        data=data
    )

    return jsonify(result), status_code


# =========================================================
# Get All Orders of Logged-in Customer
# GET /api/v1/orders
# =========================================================

@order_bp.route("", methods=["GET"])
@token_required
@role_required("customer")
def get_customer_orders_route():
    user_id = int(get_jwt_identity())

    result, status_code = get_customer_orders(
        user_id=user_id
    )

    return jsonify(result), status_code


# =========================================================
# Get Single Order
# GET /api/v1/orders/<order_id>
# =========================================================

@order_bp.route("/<int:order_id>", methods=["GET"])
@token_required
@role_required("customer")
def get_customer_order_by_id_route(order_id):
    user_id = int(get_jwt_identity())

    result, status_code = get_customer_order_by_id(
        user_id=user_id,
        order_id=order_id
    )

    return jsonify(result), status_code
 