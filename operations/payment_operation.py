from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from tables.order_table import Order
from tables.payment_table import Payment


def create_payment(user_id, data):
    try:
        order = db.session.execute(
            select(Order).where(
                Order.id == data["order_id"],
                Order.user_id == user_id
            )
        ).scalar_one_or_none()

        if order is None:
            return {
                "success": False,
                "message": "Order not found."
            }, 404

        if order.order_status in ("cancelled", "refunded"):
            return {
                "success": False,
                "message": "Payment is not allowed for this order."
            }, 400

        if order.payment_status == "success":
            return {
                "success": False,
                "message": "This order has already been paid."
            }, 409

        existing_payment = db.session.execute(
            select(Payment).where(
                Payment.order_id == order.id,
                Payment.payment_status == "pending"
            )
        ).scalar_one_or_none()

        if existing_payment is not None:
            return {
                "success": True,
                "message": "A pending payment already exists.",
                "payment": existing_payment.to_dict()
            }, 200

        amount = Decimal(str(order.total_amount))

        if amount < 0:
            return {
                "success": False,
                "message": "Invalid order amount."
            }, 400

        payment = Payment(
            order_id=order.id,
            payment_method=data["payment_method"],
            amount=amount,
            currency="INR",
            payment_status="pending"
        )

        db.session.add(payment)
        db.session.commit()

        return {
            "success": True,
            "message": "Payment initiated successfully. Awaiting payment confirmation.",
            "payment": payment.to_dict()
        }, 201

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Unable to initiate payment."
        }, 500