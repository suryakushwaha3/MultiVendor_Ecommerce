from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.banner_table import Banner


# =========================================================
# Helpers
# =========================================================

def _error(message, status_code):
    return {
        "success": False,
        "message": message
    }, status_code


def _parse_datetime(value, field_name):
    """
    Accept ISO-8601 datetime strings.
    Example: 2026-10-20T10:00:00+05:30
    """
    if value is None or value == "":
        return None, None

    if not isinstance(value, str):
        return None, f"{field_name} must be an ISO-8601 datetime string."

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        # Treat a datetime without timezone as UTC.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed, None

    except ValueError:
        return None, f"{field_name} must be a valid ISO-8601 datetime."


def _validate_text(data, field_name, required=False, max_length=None):
    value = data.get(field_name)

    if value is None:
        if required:
            return None, f"{field_name} is required."
        return None, None

    if not isinstance(value, str):
        return None, f"{field_name} must be a string."

    value = value.strip()

    if required and not value:
        return None, f"{field_name} cannot be empty."

    if max_length and len(value) > max_length:
        return None, f"{field_name} must not exceed {max_length} characters."

    return value or None, None


def _validate_order(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None, "display_order must be an integer."

    if value < 0:
        return None, "display_order cannot be negative."

    return value, None


def _validate_boolean(value, field_name):
    if not isinstance(value, bool):
        return None, f"{field_name} must be true or false."

    return value, None


def _validate_schedule(starts_at, ends_at):
    if starts_at and ends_at and ends_at <= starts_at:
        return "ends_at must be later than starts_at."

    return None


def _is_banner_currently_visible(banner, now=None):
    """
    Determine whether a banner should be shown to customers.
    This does not change the stored is_active value.
    """
    now = now or datetime.now(timezone.utc)

    if not banner.is_active:
        return False

    starts_at = banner.starts_at
    ends_at = banner.ends_at

    if starts_at:
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)

        if starts_at > now:
            return False

    if ends_at:
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)

        if ends_at <= now:
            return False

    return True


# =========================================================
# Create Banner
# =========================================================

def create_banner(data):
    if not isinstance(data, dict):
        return _error("Request body must be a JSON object.", 400)

    title, error = _validate_text(
        data, "title", required=True, max_length=150
    )
    if error:
        return _error(error, 400)

    image_url, error = _validate_text(
        data, "image_url", required=True, max_length=500
    )
    if error:
        return _error(error, 400)

    subtitle, error = _validate_text(
        data, "subtitle", max_length=255
    )
    if error:
        return _error(error, 400)

    redirect_url, error = _validate_text(
        data, "redirect_url", max_length=500
    )
    if error:
        return _error(error, 400)

    position = data.get("position", "home")
    if not isinstance(position, str) or not position.strip():
        return _error("position must be a non-empty string.", 400)

    position = position.strip()
    if len(position) > 50:
        return _error("position must not exceed 50 characters.", 400)

    display_order, error = _validate_order(
        data.get("display_order", 0)
    )
    if error:
        return _error(error, 400)

    is_active, error = _validate_boolean(
        data.get("is_active", True), "is_active"
    )
    if error:
        return _error(error, 400)

    starts_at, error = _parse_datetime(
        data.get("starts_at"), "starts_at"
    )
    if error:
        return _error(error, 400)

    ends_at, error = _parse_datetime(
        data.get("ends_at"), "ends_at"
    )
    if error:
        return _error(error, 400)

    schedule_error = _validate_schedule(starts_at, ends_at)
    if schedule_error:
        return _error(schedule_error, 400)

    banner = Banner(
        title=title,
        subtitle=subtitle,
        image_url=image_url,
        redirect_url=redirect_url,
        position=position,
        display_order=display_order,
        starts_at=starts_at,
        ends_at=ends_at,
        is_active=is_active
    )

    try:
        db.session.add(banner)
        db.session.commit()

        return {
            "success": True,
            "message": "Banner created successfully.",
            "data": banner.to_dict()
        }, 201

    except IntegrityError:
        db.session.rollback()
        return _error("Banner could not be created due to a data conflict.", 409)

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Database error while creating banner.", 500)


# =========================================================
# Get All Banners
# =========================================================

def get_banners(position=None, active_only=False, visible_only=False):
    try:
        query = Banner.query

        if position is not None:
            if not isinstance(position, str) or not position.strip():
                return _error("position must be a non-empty string.", 400)

            query = query.filter_by(position=position.strip())

        if active_only:
            query = query.filter_by(is_active=True)

        banners = query.order_by(
            Banner.display_order.asc(),
            Banner.id.desc()
        ).all()

        if visible_only:
            now = datetime.now(timezone.utc)
            banners = [
                banner for banner in banners
                if _is_banner_currently_visible(banner, now)
            ]

        return {
            "success": True,
            "count": len(banners),
            "data": [banner.to_dict() for banner in banners]
        }, 200

    except SQLAlchemyError:
        return _error("Database error while fetching banners.", 500)


# =========================================================
# Get Banner by ID
# =========================================================

def get_banner_by_id(banner_id):
    if isinstance(banner_id, bool) or not isinstance(banner_id, int) or banner_id <= 0:
        return _error("Invalid banner ID.", 400)

    try:
        banner = db.session.get(Banner, banner_id)

        if banner is None:
            return _error("Banner not found.", 404)

        return {
            "success": True,
            "data": banner.to_dict()
        }, 200

    except SQLAlchemyError:
        return _error("Database error while fetching banner.", 500)


# =========================================================
# Update Banner
# =========================================================

def update_banner(banner_id, data):
    if isinstance(banner_id, bool) or not isinstance(banner_id, int) or banner_id <= 0:
        return _error("Invalid banner ID.", 400)

    if not isinstance(data, dict):
        return _error("Request body must be a JSON object.", 400)

    allowed_fields = {
        "title",
        "subtitle",
        "image_url",
        "redirect_url",
        "position",
        "display_order",
        "starts_at",
        "ends_at",
        "is_active"
    }

    unknown_fields = set(data.keys()) - allowed_fields
    if unknown_fields:
        return _error(
            "Unsupported field(s): " + ", ".join(sorted(unknown_fields)),
            400
        )

    if not data:
        return _error("At least one field is required to update the banner.", 400)

    try:
        banner = db.session.get(Banner, banner_id)

        if banner is None:
            return _error("Banner not found.", 404)

        updated_values = {}

        for field in ("title", "image_url"):
            if field in data:
                value, error = _validate_text(
                    data, field, required=True,
                    max_length=150 if field == "title" else 500
                )
                if error:
                    return _error(error, 400)
                updated_values[field] = value

        for field, max_length in (
            ("subtitle", 255),
            ("redirect_url", 500)
        ):
            if field in data:
                value, error = _validate_text(
                    data, field, max_length=max_length
                )
                if error:
                    return _error(error, 400)
                updated_values[field] = value

        if "position" in data:
            position = data["position"]

            if not isinstance(position, str) or not position.strip():
                return _error("position must be a non-empty string.", 400)

            position = position.strip()
            if len(position) > 50:
                return _error("position must not exceed 50 characters.", 400)

            updated_values["position"] = position

        if "display_order" in data:
            order, error = _validate_order(data["display_order"])
            if error:
                return _error(error, 400)
            updated_values["display_order"] = order

        if "is_active" in data:
            active, error = _validate_boolean(data["is_active"], "is_active")
            if error:
                return _error(error, 400)
            updated_values["is_active"] = active

        for field in ("starts_at", "ends_at"):
            if field in data:
                value, error = _parse_datetime(data[field], field)
                if error:
                    return _error(error, 400)
                updated_values[field] = value

        proposed_start = updated_values.get("starts_at", banner.starts_at)
        proposed_end = updated_values.get("ends_at", banner.ends_at)

        schedule_error = _validate_schedule(proposed_start, proposed_end)
        if schedule_error:
            return _error(schedule_error, 400)

        for field, value in updated_values.items():
            setattr(banner, field, value)

        db.session.commit()

        return {
            "success": True,
            "message": "Banner updated successfully.",
            "data": banner.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Database error while updating banner.", 500)


# =========================================================
# Activate / Deactivate Banner
# =========================================================

def update_banner_status(banner_id, is_active):
    if isinstance(banner_id, bool) or not isinstance(banner_id, int) or banner_id <= 0:
        return _error("Invalid banner ID.", 400)

    active, error = _validate_boolean(is_active, "is_active")
    if error:
        return _error(error, 400)

    try:
        banner = db.session.get(Banner, banner_id)

        if banner is None:
            return _error("Banner not found.", 404)

        banner.is_active = active
        db.session.commit()

        return {
            "success": True,
            "message": "Banner status updated successfully.",
            "data": banner.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Database error while updating banner status.", 500)


# =========================================================
# Delete Banner
# =========================================================

def delete_banner(banner_id):
    if isinstance(banner_id, bool) or not isinstance(banner_id, int) or banner_id <= 0:
        return _error("Invalid banner ID.", 400)

    try:
        banner = db.session.get(Banner, banner_id)

        if banner is None:
            return _error("Banner not found.", 404)

        db.session.delete(banner)
        db.session.commit()

        return {
            "success": True,
            "message": "Banner deleted successfully."
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Database error while deleting banner.", 500)
 