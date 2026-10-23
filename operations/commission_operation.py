from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from tables.vendor_commission_table import VendorCommission
from tables.vendor_table import Vendor
from tables.store_table import Store
from tables.order_table import Order
from tables.order_item_table import OrderItem


VALID_STATUSES = {"pending", "approved", "paid", "cancelled"}
CENT = Decimal("0.01")


def _positive_id(value, field):
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a positive integer.")
    if parsed <= 0 or str(parsed) != str(value).strip():
        raise ValueError(f"{field} must be a positive integer.")
    return parsed


def _decimal(value, field):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field} must be a valid number.")
    if not number.is_finite():
        raise ValueError(f"{field} must be finite.")
    return number


def _calculate(sale_amount, commission_rate):
    commission_amount = (sale_amount * commission_rate / Decimal("100")).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    vendor_amount = (sale_amount - commission_amount).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    return commission_amount, vendor_amount


def create_commission(data):
    if not isinstance(data, dict):
        return {"success": False, "message": "A JSON object is required."}, 400

    allowed = {"vendor_id", "store_id", "order_id", "order_item_id", "commission_rate"}
    unknown = set(data) - allowed
    if unknown:
        return {
            "success": False,
            "message": f"Unknown fields: {', '.join(sorted(unknown))}"
        }, 400

    try:
        vendor_id = _positive_id(data.get("vendor_id"), "vendor_id")
        store_id = _positive_id(data.get("store_id"), "store_id")
        order_id = _positive_id(data.get("order_id"), "order_id")
        item_id = _positive_id(data.get("order_item_id"), "order_item_id")
        rate = _decimal(data.get("commission_rate"), "commission_rate")

        if rate < 0 or rate > 100:
            raise ValueError("commission_rate must be between 0 and 100.")

        vendor = db.session.get(Vendor, vendor_id)
        store = db.session.get(Store, store_id)
        order = db.session.get(Order, order_id)
        item = db.session.get(OrderItem, item_id)

        if not vendor:
            return {"success": False, "message": "Vendor not found."}, 404
        if not store:
            return {"success": False, "message": "Store not found."}, 404
        if not order:
            return {"success": False, "message": "Order not found."}, 404
        if not item:
            return {"success": False, "message": "Order item not found."}, 404

        if not vendor.is_active or not vendor.is_approved:
            return {
                "success": False,
                "message": "Vendor must be active and approved."
            }, 400

        if not store.is_active or store.vendor_id != vendor_id:
            return {
                "success": False,
                "message": "Store is inactive or does not belong to this vendor."
            }, 400

        if item.order_id != order_id:
            return {
                "success": False,
                "message": "Order item does not belong to this order."
            }, 400

        if item.product is None or item.product.store_id != store_id:
            return {
                "success": False,
                "message": "Order item product does not belong to this store."
            }, 400

        existing = db.session.execute(
            select(VendorCommission).where(
                VendorCommission.order_item_id == item_id
            )
        ).scalar_one_or_none()

        if existing:
            return {
                "success": False,
                "message": "A commission already exists for this order item."
            }, 409

        sale_amount = _decimal(item.total_price, "order item total_price")
        if sale_amount < 0:
            raise ValueError("Sale amount cannot be negative.")

        commission_amount, vendor_amount = _calculate(sale_amount, rate)

        commission = VendorCommission(
            vendor_id=vendor_id,
            store_id=store_id,
            order_id=order_id,
            order_item_id=item_id,
            sale_amount=sale_amount,
            commission_rate=rate,
            commission_amount=commission_amount,
            vendor_amount=vendor_amount,
            status="pending",
        )

        db.session.add(commission)
        db.session.commit()

        return {
            "success": True,
            "message": "Vendor commission created successfully.",
            "data": commission.to_dict(),
        }, 201

    except ValueError as exc:
        db.session.rollback()
        return {"success": False, "message": str(exc)}, 400
    except IntegrityError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Commission already exists or violates a database constraint."
        }, 409
    except Exception:
        db.session.rollback()
        return {"success": False, "message": "Unable to create commission."}, 500


def get_commissions():
    try:
        records = db.session.execute(
            select(VendorCommission).order_by(VendorCommission.created_at.desc())
        ).scalars().all()
        return {
            "success": True,
            "count": len(records),
            "data": [record.to_dict() for record in records],
        }, 200
    except Exception:
        return {"success": False, "message": "Unable to fetch commissions."}, 500


def get_commission_by_id(commission_id):
    record = db.session.get(VendorCommission, commission_id)
    if record is None:
        return {"success": False, "message": "Commission not found."}, 404
    return {"success": True, "data": record.to_dict()}, 200


def update_commission(commission_id, data):
    record = db.session.get(VendorCommission, commission_id)
    if record is None:
        return {"success": False, "message": "Commission not found."}, 404

    if not isinstance(data, dict):
        return {"success": False, "message": "A JSON object is required."}, 400

    allowed = {"commission_rate"}
    unknown = set(data) - allowed
    if unknown:
        return {
            "success": False,
            "message": f"Only these fields can be updated: {', '.join(sorted(allowed))}."
        }, 400

    if "commission_rate" not in data:
        return {"success": False, "message": "commission_rate is required."}, 400

    try:
        if record.status in {"paid", "cancelled"}:
            return {
                "success": False,
                "message": "Paid or cancelled commissions cannot be updated."
            }, 409

        rate = _decimal(data["commission_rate"], "commission_rate")
        if rate < 0 or rate > 100:
            raise ValueError("commission_rate must be between 0 and 100.")

        commission_amount, vendor_amount = _calculate(
            Decimal(str(record.sale_amount)), rate
        )

        record.commission_rate = rate
        record.commission_amount = commission_amount
        record.vendor_amount = vendor_amount

        db.session.commit()
        return {
            "success": True,
            "message": "Commission updated successfully.",
            "data": record.to_dict(),
        }, 200
    except ValueError as exc:
        db.session.rollback()
        return {"success": False, "message": str(exc)}, 400
    except Exception:
        db.session.rollback()
        return {"success": False, "message": "Unable to update commission."}, 500


def set_commission_status(commission_id, status):
    record = db.session.get(VendorCommission, commission_id)
    if record is None:
        return {"success": False, "message": "Commission not found."}, 404

    if not isinstance(status, str) or status not in VALID_STATUSES:
        return {
            "success": False,
            "message": "status must be pending, approved, paid, or cancelled."
        }, 400

    if record.status == "paid" and status != "paid":
        return {
            "success": False,
            "message": "A paid commission cannot be moved to another status."
        }, 409

    if record.status == "cancelled" and status != "cancelled":
        return {
            "success": False,
            "message": "A cancelled commission cannot be reactivated."
        }, 409

    record.status = status
    try:
        db.session.commit()
        return {
            "success": True,
            "message": "Commission status updated successfully.",
            "data": record.to_dict(),
        }, 200
    except Exception:
        db.session.rollback()
        return {"success": False, "message": "Unable to update commission status."}, 500


def delete_commission(commission_id):
    record = db.session.get(VendorCommission, commission_id)
    if record is None:
        return {"success": False, "message": "Commission not found."}, 404

    if record.status == "paid":
        return {
            "success": False,
            "message": "Paid commissions cannot be deleted."
        }, 409

    try:
        db.session.delete(record)
        db.session.commit()
        return {
            "success": True,
            "message": "Commission deleted successfully."
        }, 200
    except Exception:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to delete commission."
        }, 409
