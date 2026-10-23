from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from tables.user_table import User


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = db.session.get(User, int(user_id))

            if user is None:
                return jsonify({
                    "success": False,
                    "message": "User not found."
                }), 404

            if not user.is_active:
                return jsonify({
                    "success": False,
                    "message": "Your account is inactive."
                }), 403

            if user.role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": "You do not have permission to access this resource."
                }), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator