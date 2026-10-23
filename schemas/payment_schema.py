from marshmallow import Schema, fields, validate


# =========================================================
# Create Payment Request Schema
# =========================================================

class PaymentCreateSchema(Schema):

    order_id = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(
            min=1,
            error="order_id must be greater than zero."
        ),
        error_messages={
            "required": "order_id is required.",
            "invalid": "order_id must be a valid integer."
        }
    )

    payment_method = fields.String(
        required=True,
        validate=validate.OneOf(
            [
                "cod",
                "upi",
                "card",
                "netbanking",
                "wallet"
            ],
            error="Unsupported payment method."
        )
    )


# =========================================================
# Payment Response Schema
# Matches Payment.to_dict()
# =========================================================

class PaymentResponseSchema(Schema):

    id = fields.Integer(required=True)

    order_id = fields.Integer(required=True)

    payment_method = fields.String(required=True)

    transaction_id = fields.String(
        allow_none=True
    )

    amount = fields.Decimal(
        required=True,
        as_string=True,
        places=2
    )

    currency = fields.String(
        required=True,
        validate=validate.Length(equal=3)
    )

    payment_status = fields.String(required=True)

    gateway_name = fields.String(
        allow_none=True
    )

    gateway_order_id = fields.String(
        allow_none=True
    )

    gateway_payment_id = fields.String(
        allow_none=True
    )

    failure_reason = fields.String(
        allow_none=True
    )

    paid_at = fields.DateTime(
        allow_none=True
    )

    created_at = fields.DateTime(
        required=True,
        allow_none=True
    )

    updated_at = fields.DateTime(
        required=True,
        allow_none=True
    )
 