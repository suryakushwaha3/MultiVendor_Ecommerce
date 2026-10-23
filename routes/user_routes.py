from flask import Blueprint

from app.extensions import db
from tables.user_table import User
from middleware.auth_middleware import token_required

user_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/v1/users"
)


@user_bp.route("/me", methods=["GET"])
@token_required
def get_current_user():
    # Get logged-in user's ID from JWT
    from flask_jwt_extended import get_jwt_identity

    user_id = get_jwt_identity()

    # Find user in database
    user = db.session.get(User, int(user_id))

    if user is None:
        return {
            "success": False,
            "message": "User not found."
        }, 404

    # Return safe user information
    return {
        "success": True,
        "message": "User profile fetched successfully.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone_number": user.phone_number
        }
    }, 200


from middleware.role_middleware import role_required


@user_bp.route("/admin-test", methods=["GET"])
@token_required
@role_required("admin")
def admin_test():
    return {
        "success": True,
        "message": "Admin access granted."
    }, 200