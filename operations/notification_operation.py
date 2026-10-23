from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from tables.notification_table import Notification


ALLOWED_RECIPIENT_TYPES = {"user", "vendor", "admin"}


def _error(message, status_code):
    return {
        "success": False,
        "message": message
    }, status_code


def _recipient_conditions(recipient_type, recipient_id):
    """
    Build notification ownership conditions.

    user:
        Only notifications belonging to that user.

    vendor:
        Only notifications belonging to that vendor.

    admin:
        Notifications addressed to that admin and
        admin-wide notifications with recipient_id=None.
    """
    conditions = [
        Notification.recipient_type == recipient_type
    ]

    if recipient_type == "admin":
        conditions.append(
            or_(
                Notification.recipient_id == recipient_id,
                Notification.recipient_id.is_(None)
            )
        )
    else:
        conditions.append(
            Notification.recipient_id == recipient_id
        )

    return conditions


def create_notification(
    recipient_type,
    recipient_id,
    title,
    message,
    notification_type="general",
    reference_type=None,
    reference_id=None,
    action_url=None
):
    """
    Create a notification for a user, vendor, or admin.

    This function can be called from other operations,
    such as order, product, and account operations.
    """
    try:
        if recipient_type not in ALLOWED_RECIPIENT_TYPES:
            return _error("Invalid notification recipient type.", 400)

        if recipient_type in {"user", "vendor"}:
            if (
                isinstance(recipient_id, bool)
                or not isinstance(recipient_id, int)
                or recipient_id <= 0
            ):
                return _error(
                    "A valid recipient ID is required.",
                    400
                )

        if recipient_type == "admin" and recipient_id is not None:
            if (
                isinstance(recipient_id, bool)
                or not isinstance(recipient_id, int)
                or recipient_id <= 0
            ):
                return _error("Invalid admin recipient ID.", 400)

        if not isinstance(title, str) or not title.strip():
            return _error("Notification title is required.", 400)

        if not isinstance(message, str) or not message.strip():
            return _error("Notification message is required.", 400)

        if len(title.strip()) > 150:
            return _error(
                "Notification title cannot exceed 150 characters.",
                400
            )

        if (
            not isinstance(notification_type, str)
            or not notification_type.strip()
            or len(notification_type.strip()) > 50
        ):
            return _error("Invalid notification type.", 400)

        if reference_type is not None:
            if (
                not isinstance(reference_type, str)
                or len(reference_type) > 50
            ):
                return _error("Invalid reference type.", 400)

        if reference_id is not None:
            if (
                isinstance(reference_id, bool)
                or not isinstance(reference_id, int)
                or reference_id <= 0
            ):
                return _error("Invalid reference ID.", 400)

        if action_url is not None:
            if (
                not isinstance(action_url, str)
                or len(action_url) > 500
            ):
                return _error("Invalid action URL.", 400)

        notification = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type.strip(),
            reference_type=reference_type,
            reference_id=reference_id,
            action_url=action_url
        )

        db.session.add(notification)
        db.session.commit()

        return {
            "success": True,
            "message": "Notification created successfully.",
            "notification": notification.to_dict()
        }, 201

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to create notification.",
            500
        )


def get_notifications(
    recipient_type,
    recipient_id,
    limit=50,
    offset=0
):
    """Fetch notifications belonging to the authenticated recipient."""
    try:
        if recipient_type not in ALLOWED_RECIPIENT_TYPES:
            return _error("Invalid notification recipient type.", 400)

        if (
            isinstance(recipient_id, bool)
            or not isinstance(recipient_id, int)
            or recipient_id <= 0
        ):
            return _error("Invalid recipient ID.", 400)

        conditions = _recipient_conditions(
            recipient_type,
            recipient_id
        )

        statement = (
            select(Notification)
            .where(*conditions)
            .order_by(
                Notification.created_at.desc(),
                Notification.id.desc()
            )
            .limit(limit)
            .offset(offset)
        )

        notifications = db.session.scalars(statement).all()

        total = db.session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(*conditions)
        ) or 0

        unread = db.session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                *conditions,
                Notification.is_read.is_(False)
            )
        ) or 0

        return {
            "success": True,
            "message": "Notifications fetched successfully.",
            "notifications": [
                notification.to_dict()
                for notification in notifications
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            },
            "unread_count": unread
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to fetch notifications.",
            500
        )


def get_unread_notification_count(recipient_type, recipient_id):
    """Return the number of unread notifications."""
    try:
        if recipient_type not in ALLOWED_RECIPIENT_TYPES:
            return _error("Invalid notification recipient type.", 400)

        if (
            isinstance(recipient_id, bool)
            or not isinstance(recipient_id, int)
            or recipient_id <= 0
        ):
            return _error("Invalid recipient ID.", 400)

        conditions = _recipient_conditions(
            recipient_type,
            recipient_id
        )

        unread_count = db.session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                *conditions,
                Notification.is_read.is_(False)
            )
        ) or 0

        return {
            "success": True,
            "unread_count": unread_count
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to fetch unread notification count.",
            500
        )


def mark_notification_as_read(
    notification_id,
    recipient_type,
    recipient_id
):
    """Mark an owned notification as read."""
    try:
        conditions = _recipient_conditions(
            recipient_type,
            recipient_id
        )

        notification = db.session.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                *conditions
            )
        )

        if notification is None:
            return _error("Notification not found.", 404)

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

            db.session.commit()

        return {
            "success": True,
            "message": "Notification marked as read.",
            "notification": notification.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to update notification.",
            500
        )


def mark_all_notifications_as_read(
    recipient_type,
    recipient_id
):
    """Mark all matching notifications as read."""
    try:
        conditions = _recipient_conditions(
            recipient_type,
            recipient_id
        )

        notifications = db.session.scalars(
            select(Notification).where(
                *conditions,
                Notification.is_read.is_(False)
            )
        ).all()

        current_time = datetime.now(timezone.utc)

        for notification in notifications:
            notification.is_read = True
            notification.read_at = current_time

        db.session.commit()

        return {
            "success": True,
            "message": "Notifications marked as read.",
            "updated_count": len(notifications)
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to mark notifications as read.",
            500
        )


def delete_notification(
    notification_id,
    recipient_type,
    recipient_id
):
    """Delete a notification only if it belongs to the recipient."""
    try:
        conditions = _recipient_conditions(
            recipient_type,
            recipient_id
        )

        notification = db.session.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                *conditions
            )
        )

        if notification is None:
            return _error("Notification not found.", 404)

        db.session.delete(notification)
        db.session.commit()

        return {
            "success": True,
            "message": "Notification deleted successfully."
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to delete notification.",
            500
        )