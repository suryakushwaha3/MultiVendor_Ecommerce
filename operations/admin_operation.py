from sqlalchemy import func, select, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.extensions import db
from tables.user_table import User
from tables.vendor_table import Vendor
from tables.product_table import Product
from tables.order_table import Order
from tables.payment_table import Payment
from utils.security import hash_password


def get_admin_dashboard():
    try:
        total_users = db.session.scalar(
            select(func.count()).select_from(User)
        ) or 0

        total_vendors = db.session.scalar(
            select(func.count()).select_from(Vendor)
        ) or 0

        approved_vendors = db.session.scalar(
            select(func.count())
            .select_from(Vendor)
            .where(Vendor.is_approved.is_(True))
        ) or 0

        total_products = db.session.scalar(
            select(func.count()).select_from(Product)
        ) or 0

        active_products = db.session.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.is_active.is_(True))
        ) or 0

        total_orders = db.session.scalar(
            select(func.count()).select_from(Order)
        ) or 0

        pending_orders = db.session.scalar(
            select(func.count())
            .select_from(Order)
            .where(Order.order_status == "pending")
        ) or 0

        successful_payments = db.session.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.payment_status == "success")
        ) or 0

        total_sales = db.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .select_from(Payment)
            .where(Payment.payment_status == "success")
        )

        return {
            "success": True,
            "message": "Admin dashboard data fetched successfully.",
            "dashboard": {
                "users": {
                    "total": total_users
                },
                "vendors": {
                    "total": total_vendors,
                    "approved": approved_vendors
                },
                "products": {
                    "total": total_products,
                    "active": active_products
                },
                "orders": {
                    "total": total_orders,
                    "pending": pending_orders
                },
                "payments": {
                    "successful": successful_payments,
                    "total_sales": str(total_sales)
                }
            }
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to fetch admin dashboard data."
        }, 500


 # Add these imports at the top of operations/admin_operation.py
 


def create_vendor_by_admin(data):
    """Create a vendor account from the admin panel."""

    name = data["name"].strip()
    email = data["email"].strip().lower()
    phone_number = data["phone_number"].strip()
    business_name = data["business_name"].strip()
    business_address = data.get("business_address")

    if business_address is not None:
        business_address = business_address.strip() or None

    try:
        existing_vendor = db.session.execute(
            select(Vendor).where(
                or_(
                    Vendor.email == email,
                    Vendor.phone_number == phone_number
                )
            )
        ).scalar_one_or_none()

        if existing_vendor:
            if existing_vendor.email == email:
                return {
                    "success": False,
                    "message": "Vendor email is already registered."
                }, 409

            return {
                "success": False,
                "message": "Vendor phone number is already registered."
            }, 409

        vendor = Vendor(
            name=name,
            email=email,
            phone_number=phone_number,
            password_hash=hash_password(data["password"]),
            business_name=business_name,
            business_address=business_address,
            is_approved=False,
            is_active=True
        )

        db.session.add(vendor)
        db.session.commit()

        return {
            "success": True,
            "message": "Vendor created successfully. Admin approval is pending.",
            "vendor": vendor.to_dict()
        }, 201

    except IntegrityError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Vendor email or phone number is already registered."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to create vendor at this time."
        }, 500


def get_all_vendors():
    """Return all vendor accounts without password hashes."""

    try:
        vendors = db.session.execute(
            select(Vendor).order_by(Vendor.id.desc())
        ).scalars().all()

        return {
            "success": True,
            "message": "Vendors fetched successfully.",
            "vendors": [vendor.to_dict() for vendor in vendors]
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to fetch vendors."
        }, 500


def update_vendor_approval(vendor_id, is_approved):
    """Approve or reject a vendor account."""

    try:
        vendor = db.session.get(Vendor, vendor_id)

        if vendor is None:
            return {
                "success": False,
                "message": "Vendor not found."
            }, 404

        vendor.is_approved = is_approved

        db.session.commit()

        return {
            "success": True,
            "message": (
                "Vendor approved successfully."
                if is_approved
                else "Vendor approval revoked successfully."
            ),
            "vendor": vendor.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to update vendor approval."
        }, 500


def update_vendor_active_status(vendor_id, is_active):
    """Activate or deactivate a vendor account."""

    try:
        vendor = db.session.get(Vendor, vendor_id)

        if vendor is None:
            return {
                "success": False,
                "message": "Vendor not found."
            }, 404

        vendor.is_active = is_active

        db.session.commit()

        return {
            "success": True,
            "message": (
                "Vendor activated successfully."
                if is_active
                else "Vendor deactivated successfully."
            ),
            "vendor": vendor.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to update vendor status."
        }, 500
 