from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.store_table import Store


def create_store(vendor_id, data):
    try:
        existing_slug = db.session.execute(
            select(Store.id).where(Store.slug == data["slug"])
        ).scalar_one_or_none()

        if existing_slug is not None:
            return {
                "success": False,
                "message": "This store slug is already taken."
            }, 409

        store = Store(
            vendor_id=vendor_id,
            store_name=data["store_name"].strip(),
            slug=data["slug"],
            description=data.get("description"),
            logo_url=data.get("logo_url"),
            banner_url=data.get("banner_url"),
            address=data.get("address")
        )

        db.session.add(store)
        db.session.commit()

        return {
            "success": True,
            "message": "Store created successfully.",
            "store": store.to_dict()
        }, 201

    except IntegrityError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Store slug already exists."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to create store at this time."
        }, 500


def get_vendor_stores(vendor_id):
    try:
        stores = db.session.execute(
            select(Store)
            .where(Store.vendor_id == vendor_id)
            .order_by(Store.id.desc())
        ).scalars().all()

        return {
            "success": True,
            "message": "Stores fetched successfully.",
            "total": len(stores),
            "stores": [store.to_dict() for store in stores]
        }, 200

    except SQLAlchemyError:
        return {
            "success": False,
            "message": "Unable to fetch stores at this time."
        }, 500


def get_store_by_id(vendor_id, store_id):
    try:
        store = db.session.execute(
            select(Store).where(
                Store.id == store_id,
                Store.vendor_id == vendor_id
            )
        ).scalar_one_or_none()

        if store is None:
            return {
                "success": False,
                "message": "Store not found."
            }, 404

        return {
            "success": True,
            "message": "Store fetched successfully.",
            "store": store.to_dict()
        }, 200

    except SQLAlchemyError:
        return {
            "success": False,
            "message": "Unable to fetch store at this time."
        }, 500


def update_store(vendor_id, store_id, data):
    try:
        store = db.session.execute(
            select(Store).where(
                Store.id == store_id,
                Store.vendor_id == vendor_id
            )
        ).scalar_one_or_none()

        if store is None:
            return {
                "success": False,
                "message": "Store not found."
            }, 404

        if not data:
            return {
                "success": False,
                "message": "At least one field is required."
            }, 400

        if "slug" in data:
            existing_slug = db.session.execute(
                select(Store.id).where(
                    Store.slug == data["slug"],
                    Store.id != store_id
                )
            ).scalar_one_or_none()

            if existing_slug is not None:
                return {
                    "success": False,
                    "message": "This store slug is already taken."
                }, 409

        for field, value in data.items():
            if field == "store_name" and value is not None:
                value = value.strip()

            setattr(store, field, value)

        db.session.commit()

        return {
            "success": True,
            "message": "Store updated successfully.",
            "store": store.to_dict()
        }, 200

    except IntegrityError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Store slug already exists."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to update store at this time."
        }, 500


def update_store_status(vendor_id, store_id, is_active):
    try:
        store = db.session.execute(
            select(Store).where(
                Store.id == store_id,
                Store.vendor_id == vendor_id
            )
        ).scalar_one_or_none()

        if store is None:
            return {
                "success": False,
                "message": "Store not found."
            }, 404

        store.is_active = is_active
        db.session.commit()

        return {
            "success": True,
            "message": (
                "Store activated successfully."
                if is_active
                else "Store deactivated successfully."
            ),
            "store": store.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to update store status at this time."
        }, 500