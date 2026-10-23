from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from middleware.vendor_middleware import vendor_required
from schemas.store_schema import StoreCreateSchema, StoreUpdateSchema
from operations.store_operation import (
    create_store,
    get_vendor_stores,
    get_store_by_id,
    update_store,
    update_store_status
)


store_bp = Blueprint(
    "store",
    __name__,
    url_prefix="/api/v1/vendor/stores"
)

store_create_schema = StoreCreateSchema()
store_update_schema = StoreUpdateSchema()


def get_authenticated_vendor_id():
    identity = get_jwt_identity()
    return int(identity.split(":", 1)[1])


# Create Store
@store_bp.route("", methods=["POST"])
@vendor_required
def create_vendor_store():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = store_create_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    response, status_code = create_store(
        get_authenticated_vendor_id(),
        validated_data
    )

    return response, status_code


# Get Vendor Stores
@store_bp.route("", methods=["GET"])
@vendor_required
def get_stores():
    response, status_code = get_vendor_stores(
        get_authenticated_vendor_id()
    )

    return response, status_code


# Get Store Details
@store_bp.route("/<int:store_id>", methods=["GET"])
@vendor_required
def get_store_details(store_id):
    response, status_code = get_store_by_id(
        get_authenticated_vendor_id(),
        store_id
    )

    return response, status_code


# Update Store
@store_bp.route("/<int:store_id>", methods=["PATCH"])
@vendor_required
def update_vendor_store(store_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = store_update_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    response, status_code = update_store(
        get_authenticated_vendor_id(),
        store_id,
        validated_data
    )

    return response, status_code


# Activate / Deactivate Store
@store_bp.route("/<int:store_id>/status", methods=["PATCH"])
@vendor_required
def change_store_status(store_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not isinstance(
        data.get("is_active"), bool
    ):
        return {
            "success": False,
            "message": "is_active must be true or false."
        }, 400

    response, status_code = update_store_status(
        get_authenticated_vendor_id(),
        store_id,
        data["is_active"]
    )

    return response, status_code