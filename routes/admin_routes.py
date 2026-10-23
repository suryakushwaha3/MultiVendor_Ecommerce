from flask import Blueprint, request
from marshmallow import ValidationError

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.admin_operation import (
    get_admin_dashboard,
    create_vendor_by_admin,
    get_all_vendors,
    update_vendor_approval,
    update_vendor_active_status,
)

from schemas.vendor_schema import (
    vendor_create_schema,
    admin_vendor_update_schema,
)


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/v1/admin"
)


# ============================================================
# Admin Dashboard
# ============================================================

@admin_bp.route("/dashboard", methods=["GET"])
@token_required
@role_required("admin")
def admin_dashboard():
    response, status_code = get_admin_dashboard()
    return response, status_code


# ============================================================
# Create Vendor
# POST /api/v1/admin/vendors
# ============================================================

@admin_bp.route("/vendors", methods=["POST"])
@token_required
@role_required("admin")
def admin_create_vendor():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = vendor_create_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    response, status_code = create_vendor_by_admin(validated_data)

    return response, status_code


# ============================================================
# List Vendors
# GET /api/v1/admin/vendors
# ============================================================

@admin_bp.route("/vendors", methods=["GET"])
@token_required
@role_required("admin")
def admin_get_vendors():

    response, status_code = get_all_vendors()

    return response, status_code


# ============================================================
# Approve / Revoke Vendor Approval
# PATCH /api/v1/admin/vendors/<vendor_id>/approval
# ============================================================

@admin_bp.route(
    "/vendors/<int:vendor_id>/approval",
    methods=["PATCH"]
)
@token_required
@role_required("admin")
def admin_update_vendor_approval(vendor_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = admin_vendor_update_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    if "is_approved" not in validated_data:
        return {
            "success": False,
            "message": "is_approved field is required."
        }, 400

    response, status_code = update_vendor_approval(
        vendor_id,
        validated_data["is_approved"]
    )

    return response, status_code


# ============================================================
# Activate / Deactivate Vendor
# PATCH /api/v1/admin/vendors/<vendor_id>/status
# ============================================================

@admin_bp.route(
    "/vendors/<int:vendor_id>/status",
    methods=["PATCH"]
)
@token_required
@role_required("admin")
def admin_update_vendor_status(vendor_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = admin_vendor_update_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    if "is_active" not in validated_data:
        return {
            "success": False,
            "message": "is_active field is required."
        }, 400

    response, status_code = update_vendor_active_status(
        vendor_id,
        validated_data["is_active"]
    )

    return response, status_code
 