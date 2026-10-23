from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.address_operation import (
    create_address,
    get_customer_addresses,
    get_address_by_id,
    update_address,
    delete_address,
    set_default_address,
)


address_bp = Blueprint(
    "address_bp",
    __name__,
    url_prefix="/api/v1/addresses"
)


# =========================================================
# Create Address
# POST /api/v1/addresses
# =========================================================

@address_bp.route("", methods=["POST"])
@token_required
@role_required("customer")
def create_address_route():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    result, status_code = create_address(
        user_id=user_id,
        data=data,
    )

    return jsonify(result), status_code


# =========================================================
# Get All Customer Addresses
# GET /api/v1/addresses
# =========================================================

@address_bp.route("", methods=["GET"])
@token_required
@role_required("customer")
def get_customer_addresses_route():
    user_id = int(get_jwt_identity())

    result, status_code = get_customer_addresses(
        user_id=user_id,
    )

    return jsonify(result), status_code


# =========================================================
# Get Address By ID
# GET /api/v1/addresses/<address_id>
# =========================================================

@address_bp.route("/<int:address_id>", methods=["GET"])
@token_required
@role_required("customer")
def get_address_by_id_route(address_id):
    user_id = int(get_jwt_identity())

    result, status_code = get_address_by_id(
        user_id=user_id,
        address_id=address_id,
    )

    return jsonify(result), status_code


# =========================================================
# Update Address
# PATCH /api/v1/addresses/<address_id>
# =========================================================

@address_bp.route("/<int:address_id>", methods=["PATCH"])
@token_required
@role_required("customer")
def update_address_route(address_id):
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    result, status_code = update_address(
        user_id=user_id,
        address_id=address_id,
        data=data,
    )

    return jsonify(result), status_code


# =========================================================
# Delete Address
# DELETE /api/v1/addresses/<address_id>
# =========================================================

@address_bp.route("/<int:address_id>", methods=["DELETE"])
@token_required
@role_required("customer")
def delete_address_route(address_id):
    user_id = int(get_jwt_identity())

    result, status_code = delete_address(
        user_id=user_id,
        address_id=address_id,
    )

    return jsonify(result), status_code


# =========================================================
# Set Default Address
# PATCH /api/v1/addresses/<address_id>/default
# =========================================================

@address_bp.route(
    "/<int:address_id>/default",
    methods=["PATCH"],
)
@token_required
@role_required("customer")
def set_default_address_route(address_id):
    user_id = int(get_jwt_identity())

    result, status_code = set_default_address(
        user_id=user_id,
        address_id=address_id,
    )

    return jsonify(result), status_code
 