from functools import wraps

from flask import jsonify
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity
)

from app.extensions import db
from tables.user_table import User


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({
                "success": False,
                "message": (
                    "Authentication required. "
                    "Please provide a valid access token."
                )
            }), 401

        identity = get_jwt_identity()

        # Vendor tokens use the format: vendor:<vendor_id>.
        # Preserve the existing vendor authentication flow.
        if isinstance(identity, str) and identity.startswith("vendor:"):
            return fn(*args, **kwargs)

        # Customer/user tokens contain the user ID.
        try:
            user_id = int(identity)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid authentication identity."
            }), 401

        user = db.session.get(User, user_id)

        if user is None:
            return jsonify({
                "success": False,
                "message": "User not found."
            }), 401

        if not user.is_active:
            return jsonify({
                "success": False,
                "message": "Your account is inactive."
            }), 403

        return fn(*args, **kwargs)

    return wrapper
 