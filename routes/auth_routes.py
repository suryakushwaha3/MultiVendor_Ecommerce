from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

from schemas.auth_schema import (
    UserSignupSchema,
    UserLoginSchema,
    VendorLoginSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    ChangePasswordSchema,
)

from operations.user_operation import register_user

from operations.auth_operation import (
    login_user,
    login_vendor,
)

from operations.password_reset_operation import (
    request_password_reset,
    reset_password,
    change_password,
)

from tables.user_table import User
from tables.vendor_table import Vendor


# =========================================================
# BLUEPRINT
# =========================================================

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/v1/auth",
)


# =========================================================
# SCHEMA INSTANCES
# =========================================================

signup_schema = UserSignupSchema()
login_schema = UserLoginSchema()
vendor_login_schema = VendorLoginSchema()

forgot_password_schema = ForgotPasswordSchema()
reset_password_schema = ResetPasswordSchema()
change_password_schema = ChangePasswordSchema()


# =========================================================
# HELPER: VALIDATE JSON BODY
# =========================================================

def get_json_body():
    """
    Return a dictionary when a valid JSON object is supplied.
    Return an error response otherwise.
    """

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, (
            jsonify({
                "success": False,
                "message": "A valid JSON request body is required.",
            }),
            400,
        )

    return data, None


# =========================================================
# USER SIGNUP
# POST /api/v1/auth/signup
# =========================================================

@auth_bp.route("/signup", methods=["POST"])
def user_signup():

    data, error_response = get_json_body()

    if error_response:
        return error_response

    try:
        validated_data = signup_schema.load(data)

    except ValidationError as error:
        return jsonify({
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages,
        }), 400

    response, status_code = register_user(validated_data)

    return jsonify(response), status_code


# =========================================================
# USER LOGIN
# POST /api/v1/auth/login
# =========================================================

@auth_bp.route("/login", methods=["POST"])
def user_login():

    data, error_response = get_json_body()

    if error_response:
        return error_response

    try:
        validated_data = login_schema.load(data)

    except ValidationError as error:
        return jsonify({
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages,
        }), 400

    response, status_code = login_user(validated_data)

    return jsonify(response), status_code


# =========================================================
# VENDOR LOGIN
# POST /api/v1/auth/vendor/login
# =========================================================

@auth_bp.route("/vendor/login", methods=["POST"])
def vendor_login():

    data, error_response = get_json_body()

    if error_response:
        return error_response

    try:
        validated_data = vendor_login_schema.load(data)

    except ValidationError as error:
        return jsonify({
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages,
        }), 400

    response, status_code = login_vendor(validated_data)

    return jsonify(response), status_code


# =========================================================
# REFRESH ACCESS TOKEN
# POST /api/v1/auth/refresh
#
# Authorization: Bearer <refresh_token>
# =========================================================

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_access_token():

    identity = get_jwt_identity()

    try:
        # -------------------------------------------------
        # VENDOR REFRESH
        # Vendor identity format: vendor:<vendor_id>
        # -------------------------------------------------

        if (
            isinstance(identity, str)
            and identity.startswith("vendor:")
        ):
            vendor_id_text = identity.split(":", 1)[1]

            if not vendor_id_text.isdigit():
                return jsonify({
                    "success": False,
                    "message": "Invalid token identity.",
                }), 401

            vendor = db.session.get(
                Vendor,
                int(vendor_id_text),
            )

            if vendor is None:
                return jsonify({
                    "success": False,
                    "message": "Vendor account not found.",
                }), 403

            if not vendor.is_active or not vendor.is_approved:
                return jsonify({
                    "success": False,
                    "message": (
                        "Vendor account is inactive or "
                        "awaiting approval."
                    ),
                }), 403

            new_access_token = create_access_token(
                identity=f"vendor:{vendor.id}"
            )

        # -------------------------------------------------
        # USER / ADMIN REFRESH
        # User identity format: <user_id>
        # -------------------------------------------------

        else:
            if not str(identity).isdigit():
                return jsonify({
                    "success": False,
                    "message": "Invalid token identity.",
                }), 401

            user = db.session.get(
                User,
                int(identity),
            )

            if user is None:
                return jsonify({
                    "success": False,
                    "message": "User account not found.",
                }), 403

            if not user.is_active:
                return jsonify({
                    "success": False,
                    "message": "Your account is inactive.",
                }), 403

            new_access_token = create_access_token(
                identity=str(user.id)
            )

        return jsonify({
            "success": True,
            "message": "Access token refreshed successfully.",
            "access_token": new_access_token,
            "token_type": "Bearer",
        }), 200

    except SQLAlchemyError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to refresh token at this time.",
        }), 500


# =========================================================
# FORGOT PASSWORD
# POST /api/v1/auth/forgot-password
# =========================================================

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():

    data, error_response = get_json_body()

    if error_response:
        return error_response

    try:
        validated_data = forgot_password_schema.load(data)

    except ValidationError as error:
        return jsonify({
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages,
        }), 400

    response, status_code = request_password_reset(
        validated_data
    )

    return jsonify(response), status_code


# =========================================================
# RESET PASSWORD
# POST /api/v1/auth/reset-password
# =========================================================

@auth_bp.route("/reset-password", methods=["POST"])
def password_reset():

    data, error_response = get_json_body()

    if error_response:
        return error_response

    try:
        validated_data = reset_password_schema.load(data)

    except ValidationError as error:
        return jsonify({
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages,
        }), 400

    response, status_code = reset_password(
        validated_data
    )

    return jsonify(response), status_code


# =========================================================
# CHANGE PASSWORD
# POST /api/v1/auth/change-password
# =========================================================

@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def password_change():

    data, error_response = get_json_body()

    if error_response:
        return error_response

    try:
        validated_data = change_password_schema.load(data)

    except ValidationError as error:
        return jsonify({
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages,
        }), 400

    if (
        validated_data["current_password"]
        == validated_data["new_password"]
    ):
        return jsonify({
            "success": False,
            "message": (
                "New password must be different "
                "from the current password."
            ),
        }), 400

    response, status_code = change_password(
        validated_data
    )

    return jsonify(response), status_code
 