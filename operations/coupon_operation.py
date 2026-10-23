
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from tables.coupon_table import Coupon


def _parse_datetime(value):
    if value is None or value == "":
        return None

    if not isinstance(value, str):
        raise ValueError("Date must be an ISO-8601 string.")

    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result
    except ValueError:
        raise ValueError(
            "Invalid date format. Use ISO-8601, e.g. 2026-12-31T23:59:00Z."
        )


def _parse_decimal(value, field, required=False):
    if value is None or value == "":
        if required:
            raise ValueError(f"{field} is required.")
        return None

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a valid number.")

    if not number.is_finite():
        raise ValueError(f"{field} must be a finite number.")

    return number


def _validate_payload(data, creating=True):
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    allowed = {
        "code",
        "description",
        "discount_type",
        "discount_value",
        "minimum_order_amount",
        "maximum_discount_amount",
        "usage_limit",
        "starts_at",
        "expires_at",
        "is_active",
    }

    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(sorted(unknown))}")

    if creating:
        required = {"code", "discount_type", "discount_value"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"Required fields missing: {', '.join(sorted(missing))}")

    result = {}

    if "code" in data:
        code = data["code"]
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must be a non-empty string.")
        result["code"] = code.strip().upper()

    if "description" in data:
        description = data["description"]
        if description is not None and not isinstance(description, str):
            raise ValueError("description must be a string or null.")
        result["description"] = description.strip() if description else None

    if "discount_type" in data:
        discount_type = data["discount_type"]
        if discount_type not in ("percentage", "fixed"):
            raise ValueError("discount_type must be 'percentage' or 'fixed'.")
        result["discount_type"] = discount_type

    if "discount_value" in data:
        value = _parse_decimal(data["discount_value"], "discount_value", True)
        if value <= 0:
            raise ValueError("discount_value must be greater than zero.")
        result["discount_value"] = value

    if "minimum_order_amount" in data:
        value = _parse_decimal(
            data["minimum_order_amount"], "minimum_order_amount"
        )
        if value is None or value < 0:
            raise ValueError("minimum_order_amount must be zero or greater.")
        result["minimum_order_amount"] = value

    if "maximum_discount_amount" in data:
        value = _parse_decimal(
            data["maximum_discount_amount"], "maximum_discount_amount"
        )
        if value is not None and value < 0:
            raise ValueError("maximum_discount_amount cannot be negative.")
        result["maximum_discount_amount"] = value

    if "usage_limit" in data:
        value = data["usage_limit"]
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("usage_limit must be a positive integer or null.")
        result["usage_limit"] = value

    if "starts_at" in data:
        result["starts_at"] = _parse_datetime(data["starts_at"])

    if "expires_at" in data:
        result["expires_at"] = _parse_datetime(data["expires_at"])

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise ValueError("is_active must be true or false.")
        result["is_active"] = data["is_active"]

    final_type = result.get("discount_type")
    final_value = result.get("discount_value")

    if not creating:
        coupon = data.get("_existing_coupon")
        if coupon:
            final_type = final_type or coupon.discount_type
            final_value = final_value or coupon.discount_value

    if final_type == "percentage" and final_value is not None:
        if final_value > 100:
            raise ValueError("Percentage discount cannot exceed 100.")

    start = result.get("starts_at")
    expiry = result.get("expires_at")
    if start and expiry and expiry <= start:
        raise ValueError("expires_at must be later than starts_at.")

    return result


def create_coupon(data):
    try:
        values = _validate_payload(data, creating=True)
        coupon = Coupon(**values)
        db.session.add(coupon)
        db.session.commit()

        return {
            "success": True,
            "message": "Coupon created successfully.",
            "data": coupon.to_dict(),
        }, 201

    except ValueError as exc:
        db.session.rollback()
        return {"success": False, "message": str(exc)}, 400
    except IntegrityError:
        db.session.rollback()
        return {"success": False, "message": "Coupon code already exists."}, 409
    except Exception:
        db.session.rollback()
        return {"success": False, "message": "Unable to create coupon."}, 500


def get_coupons():
    try:
        query = select(Coupon).order_by(Coupon.created_at.desc())
        coupons = db.session.execute(query).scalars().all()

        return {
            "success": True,
            "count": len(coupons),
            "data": [coupon.to_dict() for coupon in coupons],
        }, 200
    except Exception:
        return {"success": False, "message": "Unable to fetch coupons."}, 500


def get_coupon_by_id(coupon_id):
    coupon = db.session.get(Coupon, coupon_id)
    if coupon is None:
        return {"success": False, "message": "Coupon not found."}, 404

    return {"success": True, "data": coupon.to_dict()}, 200


def update_coupon(coupon_id, data):
    coupon = db.session.get(Coupon, coupon_id)
    if coupon is None:
        return {"success": False, "message": "Coupon not found."}, 404

    try:
        values = _validate_payload(data, creating=False)

        start = values.get("starts_at", coupon.starts_at)
        expiry = values.get("expires_at", coupon.expires_at)
        if start and expiry and expiry <= start:
            raise ValueError("expires_at must be later than starts_at.")

        final_type = values.get("discount_type", coupon.discount_type)
        final_value = values.get("discount_value", coupon.discount_value)
        if final_type == "percentage" and Decimal(str(final_value)) > 100:
            raise ValueError("Percentage discount cannot exceed 100.")

        for key, value in values.items():
            setattr(coupon, key, value)

        db.session.commit()
        return {
            "success": True,
            "message": "Coupon updated successfully.",
            "data": coupon.to_dict(),
        }, 200

    except ValueError as exc:
        db.session.rollback()
        return {"success": False, "message": str(exc)}, 400
    except IntegrityError:
        db.session.rollback()
        return {"success": False, "message": "Coupon code already exists."}, 409
    except Exception:
        db.session.rollback()
        return {"success": False, "message": "Unable to update coupon."}, 500


def set_coupon_status(coupon_id, is_active):
    coupon = db.session.get(Coupon, coupon_id)
    if coupon is None:
        return {"success": False, "message": "Coupon not found."}, 404

    if not isinstance(is_active, bool):
        return {"success": False, "message": "is_active must be true or false."}, 400

    coupon.is_active = is_active
    db.session.commit()

    return {
        "success": True,
        "message": "Coupon status updated successfully.",
        "data": coupon.to_dict(),
    }, 200


def delete_coupon(coupon_id):
    coupon = db.session.get(Coupon, coupon_id)
    if coupon is None:
        return {"success": False, "message": "Coupon not found."}, 404

    try:
        db.session.delete(coupon)
        db.session.commit()
        return {"success": True, "message": "Coupon deleted successfully."}, 200
    except Exception:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to delete coupon. It may be referenced by another record.",
        }, 409
