from flask import Blueprint, request
from marshmallow import ValidationError

from schemas.auth_schema import UserSignupSchema
from operations.user_operation import register_user
from schemas.auth_schema import UserLoginSchema
from operations.auth_operation import login_user
from schemas.auth_schema import VendorLoginSchema
from operations.auth_operation import login_vendor


auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

signup_schema = UserSignupSchema()
login_schema = UserLoginSchema()
vendor_login_schema = VendorLoginSchema()


@auth_bp.route("/signup", methods=["POST"])
def user_signup():
    # Parse JSON request
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    # Validate request data
    try:
        validated_data = signup_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    # Register user
    response, status_code = register_user(validated_data)

    return response, status_code


#Login route

@auth_bp.route("/login", methods=["POST"])
def user_login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = login_schema.load(data)

    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    response, status_code = login_user(validated_data)

    return response, status_code


#Vendor login route
@auth_bp.route("/vendor/login", methods=["POST"])
def vendor_login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = vendor_login_schema.load(data)

    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    response, status_code = login_vendor(validated_data)

    return response, status_code
# Password reset routes
from flask_jwt_extended import jwt_required
from schemas.auth_schema import (
    ForgotPasswordSchema,
    ResetPasswordSchema,
    ChangePasswordSchema,
)
from operations.password_reset_operation import (
    request_password_reset,
    reset_password,
    change_password,
)

forgot_password_schema = ForgotPasswordSchema()
reset_password_schema = ResetPasswordSchema()
change_password_schema = ChangePasswordSchema()


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = forgot_password_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    response, status_code = request_password_reset(validated_data)
    return response, status_code


@auth_bp.route("/reset-password", methods=["POST"])
def password_reset():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = reset_password_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    response, status_code = reset_password(validated_data)
    return response, status_code


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def password_change():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = change_password_schema.load(data)
    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    if validated_data["current_password"] == validated_data["new_password"]:
        return {
            "success": False,
            "message": "New password must be different from the current password."
        }, 400

    response, status_code = change_password(validated_data)
    return response, status_code
