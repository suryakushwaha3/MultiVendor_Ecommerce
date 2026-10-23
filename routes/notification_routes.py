from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required
from middleware.vendor_middleware import vendor_required

from operations.notification_operation import (
    get_notifications,
    get_unread_notification_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    delete_notification
)


notification_bp = Blueprint(
    "notification",
    __name__,
    url_prefix="/api/v1/notifications"
)


def _response(result, status_code):
    return jsonify(result), status_code


def _get_pagination():
    """Validate pagination parameters from query string."""
    try:
        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)

        if limit is None or offset is None:
            return None, None, (
                {
                    "success": False,
                    "message": "Limit and offset must be integers."
                },
                400
            )

        if limit < 1 or limit > 100:
            return None, None, (
                {
                    "success": False,
                    "message": "Limit must be between 1 and 100."
                },
                400
            )

        if offset < 0:
            return None, None, (
                {
                    "success": False,
                    "message": "Offset cannot be negative."
                },
                400
            )

        return limit, offset, None

    except (TypeError, ValueError):
        return None, None, (
            {
                "success": False,
                "message": "Invalid pagination parameters."
            },
            400
        )


# --------------------------------------------------
# CUSTOMER NOTIFICATIONS
# --------------------------------------------------

@notification_bp.route("/me", methods=["GET"])
@token_required
@role_required("customer")
def customer_notifications():
    user_id = int(get_jwt_identity())

    limit, offset, error = _get_pagination()

    if error:
        return _response(*error)

    result, status_code = get_notifications(
        recipient_type="user",
        recipient_id=user_id,
        limit=limit,
        offset=offset
    )

    return _response(result, status_code)


@notification_bp.route("/me/unread-count", methods=["GET"])
@token_required
@role_required("customer")
def customer_unread_count():
    user_id = int(get_jwt_identity())

    result, status_code = get_unread_notification_count(
        recipient_type="user",
        recipient_id=user_id
    )

    return _response(result, status_code)


@notification_bp.route("/me/read-all", methods=["PATCH"])
@token_required
@role_required("customer")
def customer_read_all():
    user_id = int(get_jwt_identity())

    result, status_code = mark_all_notifications_as_read(
        recipient_type="user",
        recipient_id=user_id
    )

    return _response(result, status_code)


@notification_bp.route("/me/<int:notification_id>/read", methods=["PATCH"])
@token_required
@role_required("customer")
def customer_mark_read(notification_id):
    user_id = int(get_jwt_identity())

    result, status_code = mark_notification_as_read(
        notification_id=notification_id,
        recipient_type="user",
        recipient_id=user_id
    )

    return _response(result, status_code)


@notification_bp.route("/me/<int:notification_id>", methods=["DELETE"])
@token_required
@role_required("customer")
def customer_delete_notification(notification_id):
    user_id = int(get_jwt_identity())

    result, status_code = delete_notification(
        notification_id=notification_id,
        recipient_type="user",
        recipient_id=user_id
    )

    return _response(result, status_code)


# --------------------------------------------------
# VENDOR NOTIFICATIONS
# --------------------------------------------------

@notification_bp.route("/vendor/me", methods=["GET"])
@vendor_required
def vendor_notifications():
    from flask import g

    limit, offset, error = _get_pagination()

    if error:
        return _response(*error)

    result, status_code = get_notifications(
        recipient_type="vendor",
        recipient_id=g.vendor_id,
        limit=limit,
        offset=offset
    )

    return _response(result, status_code)


@notification_bp.route("/vendor/me/unread-count", methods=["GET"])
@vendor_required
def vendor_unread_count():
    from flask import g

    result, status_code = get_unread_notification_count(
        recipient_type="vendor",
        recipient_id=g.vendor_id
    )

    return _response(result, status_code)


@notification_bp.route("/vendor/me/read-all", methods=["PATCH"])
@vendor_required
def vendor_read_all():
    from flask import g

    result, status_code = mark_all_notifications_as_read(
        recipient_type="vendor",
        recipient_id=g.vendor_id
    )

    return _response(result, status_code)


@notification_bp.route(
    "/vendor/me/<int:notification_id>/read",
    methods=["PATCH"]
)
@vendor_required
def vendor_mark_read(notification_id):
    from flask import g

    result, status_code = mark_notification_as_read(
        notification_id=notification_id,
        recipient_type="vendor",
        recipient_id=g.vendor_id
    )

    return _response(result, status_code)


@notification_bp.route(
    "/vendor/me/<int:notification_id>",
    methods=["DELETE"]
)
@vendor_required
def vendor_delete_notification(notification_id):
    from flask import g

    result, status_code = delete_notification(
        notification_id=notification_id,
        recipient_type="vendor",
        recipient_id=g.vendor_id
    )

    return _response(result, status_code)


# --------------------------------------------------
# ADMIN NOTIFICATIONS
# --------------------------------------------------

@notification_bp.route("/admin/me", methods=["GET"])
@token_required
@role_required("admin")
def admin_notifications():
    admin_id = int(get_jwt_identity())

    limit, offset, error = _get_pagination()

    if error:
        return _response(*error)

    result, status_code = get_notifications(
        recipient_type="admin",
        recipient_id=admin_id,
        limit=limit,
        offset=offset
    )

    return _response(result, status_code)


@notification_bp.route("/admin/me/unread-count", methods=["GET"])
@token_required
@role_required("admin")
def admin_unread_count():
    admin_id = int(get_jwt_identity())

    result, status_code = get_unread_notification_count(
        recipient_type="admin",
        recipient_id=admin_id
    )

    return _response(result, status_code)


@notification_bp.route("/admin/me/read-all", methods=["PATCH"])
@token_required
@role_required("admin")
def admin_read_all():
    admin_id = int(get_jwt_identity())

    result, status_code = mark_all_notifications_as_read(
        recipient_type="admin",
        recipient_id=admin_id
    )

    return _response(result, status_code)


@notification_bp.route(
    "/admin/me/<int:notification_id>/read",
    methods=["PATCH"]
)
@token_required
@role_required("admin")
def admin_mark_read(notification_id):
    admin_id = int(get_jwt_identity())

    result, status_code = mark_notification_as_read(
        notification_id=notification_id,
        recipient_type="admin",
        recipient_id=admin_id
    )

    return _response(result, status_code)


@notification_bp.route(
    "/admin/me/<int:notification_id>",
    methods=["DELETE"]
)
@token_required
@role_required("admin")
def admin_delete_notification(notification_id):
    admin_id = int(get_jwt_identity())

    result, status_code = delete_notification(
        notification_id=notification_id,
        recipient_type="admin",
        recipient_id=admin_id
    )

    return _response(result, status_code)