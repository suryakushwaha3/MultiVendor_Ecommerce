from sqlalchemy import func, select, distinct
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from tables.store_table import Store
from tables.product_table import Product
from tables.order_table import Order
from tables.order_item_table import OrderItem

def get_vendor_dashboard(vendor_id):
    try:
        # Vendor ke apne stores
        store_ids_query = select(Store.id).where(
            Store.vendor_id == vendor_id
        )

        total_stores = db.session.scalar(
            select(func.count()).select_from(Store).where(
                Store.vendor_id == vendor_id
            )
        ) or 0

        active_stores = db.session.scalar(
            select(func.count()).select_from(Store).where(
                Store.vendor_id == vendor_id,
                Store.is_active.is_(True)
            )
        ) or 0

        # Vendor ke apne products
        product_filter = Product.store_id.in_(store_ids_query)

        total_products = db.session.scalar(
            select(func.count()).select_from(Product).where(
                product_filter
            )
        ) or 0

        active_products = db.session.scalar(
            select(func.count()).select_from(Product).where(
                product_filter,
                Product.is_active.is_(True)
            )
        ) or 0

        total_stock = db.session.scalar(
            select(func.coalesce(func.sum(Product.stock_quantity), 0))
            .where(product_filter)
        ) or 0

        low_stock_products = db.session.scalar(
            select(func.count()).select_from(Product).where(
                product_filter,
                Product.stock_quantity <= 5
            )
        ) or 0

        # Sirf vendor ke products se related orders
        vendor_order_ids = (
            select(OrderItem.order_id)
            .join(Product, OrderItem.product_id == Product.id)
            .where(product_filter)
        )

        total_orders = db.session.scalar(
            select(func.count(distinct(OrderItem.order_id)))
            .select_from(OrderItem)
            .join(Product, OrderItem.product_id == Product.id)
            .where(product_filter)
        ) or 0

        pending_orders = db.session.scalar(
            select(func.count(distinct(OrderItem.order_id)))
            .select_from(OrderItem)
            .join(Product, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                product_filter,
                Order.order_status.in_(["placed", "pending"])
            )
        ) or 0

        # Vendor ke apne order items ki sales.
        # Cancelled orders ko sales mein include nahi karte.
        total_sales = db.session.scalar(
            select(
                func.coalesce(func.sum(OrderItem.total_price), 0)
            )
            .select_from(OrderItem)
            .join(Product, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                product_filter,
                Order.order_status.notin_(["cancelled", "refunded"])
            )
        ) or 0

        return {
            "success": True,
            "message": "Vendor dashboard data fetched successfully.",
            "dashboard": {
                "stores": {
                    "total": total_stores,
                    "active": active_stores
                },
                "products": {
                    "total": total_products,
                    "active": active_products,
                    "total_stock": total_stock,
                    "low_stock": low_stock_products
                },
                "orders": {
                    "total": total_orders,
                    "pending": pending_orders
                },
                "sales": {
                    "total": str(total_sales)
                }
            }
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to fetch vendor dashboard data."
        }, 500