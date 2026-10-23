from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.inventory_table import Inventory
from tables.product_table import Product
from tables.store_table import Store


ALLOWED_MOVEMENTS = {
    "purchase",
    "sale",
    "return",
    "adjustment",
    "damaged",
}


def record_inventory_movement(
    product_id,
    quantity_change,
    movement_type,
    store_id=None,
    reference_type=None,
    reference_id=None,
    note=None,
    created_by_type="system",
    created_by_id=None,
    commit=True,
):
    """
    Record a stock movement and update the product's current stock.

    Positive quantity_change adds stock.
    Negative quantity_change removes stock.

    If commit=False, the caller owns the transaction.
    """

    try:
        if isinstance(product_id, bool) or isinstance(quantity_change, bool):
            return {
                "success": False,
                "message": "Invalid product or quantity."
            }, 400

        product_id = int(product_id)
        quantity_change = int(quantity_change)

        if product_id <= 0 or quantity_change == 0:
            return {
                "success": False,
                "message": "Product ID must be positive and quantity cannot be zero."
            }, 400

        if movement_type not in ALLOWED_MOVEMENTS:
            return {
                "success": False,
                "message": "Invalid inventory movement type."
            }, 400

        if store_id is not None:
            if isinstance(store_id, bool):
                return {
                    "success": False,
                    "message": "Invalid store ID."
                }, 400

            store_id = int(store_id)

        if reference_id is not None:
            if isinstance(reference_id, bool):
                return {
                    "success": False,
                    "message": "Invalid reference ID."
                }, 400

            reference_id = int(reference_id)

        if created_by_id is not None:
            if isinstance(created_by_id, bool):
                return {
                    "success": False,
                    "message": "Invalid creator ID."
                }, 400

            created_by_id = int(created_by_id)

        if created_by_type not in {"admin", "vendor", "system"}:
            return {
                "success": False,
                "message": "Invalid creator type."
            }, 400

        if note is not None:
            if not isinstance(note, str):
                return {
                    "success": False,
                    "message": "Note must be a string."
                }, 400

            note = note.strip()

            if len(note) > 500:
                return {
                    "success": False,
                    "message": "Note cannot exceed 500 characters."
                }, 400

        # Lock the product row while changing stock.
        product = db.session.execute(
            select(Product)
            .where(Product.id == product_id)
            .with_for_update()
        ).scalar_one_or_none()

        if product is None:
            return {
                "success": False,
                "message": "Product not found."
            }, 404

        if store_id is not None and product.store_id != store_id:
            return {
                "success": False,
                "message": "Product does not belong to this store."
            }, 403

        actual_store_id = product.store_id

        # Verify that the product's store exists.
        store = db.session.get(Store, actual_store_id)

        if store is None:
            return {
                "success": False,
                "message": "Product store not found."
            }, 404

        previous_stock = product.stock_quantity
        new_stock = previous_stock + quantity_change

        if new_stock < 0:
            return {
                "success": False,
                "message": "Insufficient stock."
            }, 400

        inventory = Inventory(
            product_id=product.id,
            store_id=actual_store_id,
            movement_type=movement_type,
            quantity_change=quantity_change,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note or None,
            created_by_type=created_by_type,
            created_by_id=created_by_id,
        )

        product.stock_quantity = new_stock
        db.session.add(inventory)

        # Flush so database constraint failures occur before success.
        db.session.flush()

        if commit:
            db.session.commit()

        return {
            "success": True,
            "message": "Inventory movement recorded successfully.",
            "data": inventory.to_dict(),
        }, 201

    except (ValueError, TypeError, OverflowError):
        if commit:
            db.session.rollback()

        return {
            "success": False,
            "message": "Invalid inventory data."
        }, 400

    except IntegrityError:
        if commit:
            db.session.rollback()

        return {
            "success": False,
            "message": "Inventory data violates a database constraint."
        }, 409

    except SQLAlchemyError:
        if commit:
            db.session.rollback()

        return {
            "success": False,
            "message": "Database error while recording inventory movement."
        }, 500


def get_inventory_history(
    vendor_id=None,
    store_id=None,
    product_id=None,
    movement_type=None,
    limit=50,
    offset=0,
):
    """
    Retrieve inventory history.

    Pass vendor_id for vendor-scoped access.
    Admin callers may omit vendor_id.
    """

    try:
        if vendor_id is not None:
            if isinstance(vendor_id, bool):
                return {
                    "success": False,
                    "message": "Invalid vendor ID."
                }, 400

            vendor_id = int(vendor_id)

            if vendor_id <= 0:
                return {
                    "success": False,
                    "message": "Invalid vendor ID."
                }, 400

        if store_id is not None:
            if isinstance(store_id, bool):
                return {
                    "success": False,
                    "message": "Invalid store ID."
                }, 400

            store_id = int(store_id)

            if store_id <= 0:
                return {
                    "success": False,
                    "message": "Invalid store ID."
                }, 400

        if product_id is not None:
            if isinstance(product_id, bool):
                return {
                    "success": False,
                    "message": "Invalid product ID."
                }, 400

            product_id = int(product_id)

            if product_id <= 0:
                return {
                    "success": False,
                    "message": "Invalid product ID."
                }, 400

        if movement_type is not None and movement_type not in ALLOWED_MOVEMENTS:
            return {
                "success": False,
                "message": "Invalid inventory movement type."
            }, 400

        if isinstance(limit, bool) or isinstance(offset, bool):
            return {
                "success": False,
                "message": "Invalid pagination values."
            }, 400

        limit = int(limit)
        offset = int(offset)

        if limit < 1 or limit > 100 or offset < 0:
            return {
                "success": False,
                "message": "Limit must be 1-100 and offset cannot be negative."
            }, 400

        query = select(Inventory)

        if vendor_id is not None:
            query = query.join(
                Store,
                Inventory.store_id == Store.id
            ).where(
                Store.vendor_id == vendor_id
            )

        if store_id is not None:
            query = query.where(Inventory.store_id == store_id)

        if product_id is not None:
            query = query.where(Inventory.product_id == product_id)

        if movement_type is not None:
            query = query.where(
                Inventory.movement_type == movement_type
            )

        count_query = select(db.func.count()).select_from(
            query.order_by(None).subquery()
        )

        total = db.session.execute(count_query).scalar_one()

        records = db.session.execute(
            query
            .order_by(Inventory.created_at.desc(), Inventory.id.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        return {
            "success": True,
            "message": "Inventory history retrieved successfully.",
            "count": len(records),
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [record.to_dict() for record in records],
        }, 200

    except (ValueError, TypeError, OverflowError):
        return {
            "success": False,
            "message": "Invalid inventory filters."
        }, 400

    except SQLAlchemyError:
        return {
            "success": False,
            "message": "Database error while retrieving inventory history."
        }, 500


def get_inventory_history_by_product(
    product_id,
    vendor_id=None,
    store_id=None,
    limit=50,
    offset=0,
):
    """Retrieve history for one product."""

    return get_inventory_history(
        vendor_id=vendor_id,
        store_id=store_id,
        product_id=product_id,
        limit=limit,
        offset=offset,
    )
 