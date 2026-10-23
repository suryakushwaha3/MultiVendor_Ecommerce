from marshmallow import (
    Schema,
    fields,
    validate,
    validates,
    ValidationError,
)


# ============================================================
# Create Order Schema
# ============================================================

class OrderCreateSchema(Schema):

    address_id = fields.Integer(
        required=True,
        validate=validate.Range(
            min=1,
            error="Address ID must be a positive integer."
        )
    )

    notes = fields.String(
        allow_none=True,
        load_default=None
    )

    # Client cannot submit prices, totals, statuses or user_id.
    # These must be calculated/set by trusted backend operations.


# ============================================================
# Order Item Response Schema
# ============================================================

class OrderItemResponseSchema(Schema):

    id = fields.Integer(dump_only=True)

    order_id = fields.Integer(dump_only=True)

    product_id = fields.Integer(dump_only=True)

    product_name = fields.String()

    product_image_url = fields.String(allow_none=True)

    sku = fields.String()

    quantity = fields.Integer(
        validate=validate.Range(min=1)
    )

    unit_price = fields.Decimal(
        as_string=True,
        places=2
    )

    discount_amount = fields.Decimal(
        as_string=True,
        places=2
    )

    total_price = fields.Decimal(
        as_string=True,
        places=2
    )

    created_at = fields.DateTime(
        allow_none=True,
        dump_only=True
    )


# ============================================================
# Order Response Schema
# ============================================================

class OrderResponseSchema(Schema):

    id = fields.Integer(dump_only=True)

    order_number = fields.String()

    user_id = fields.Integer(dump_only=True)

    address_id = fields.Integer()

    subtotal = fields.Decimal(
        as_string=True,
        places=2
    )

    discount_amount = fields.Decimal(
        as_string=True,
        places=2
    )

    shipping_amount = fields.Decimal(
        as_string=True,
        places=2
    )

    tax_amount = fields.Decimal(
        as_string=True,
        places=2
    )

    total_amount = fields.Decimal(
        as_string=True,
        places=2
    )

    payment_status = fields.String()

    order_status = fields.String()

    notes = fields.String(allow_none=True)

    items = fields.List(
        fields.Nested(OrderItemResponseSchema),
        dump_only=True
    )

    created_at = fields.DateTime(
        allow_none=True,
        dump_only=True
    )

    updated_at = fields.DateTime(
        allow_none=True,
        dump_only=True
    )

# ============================================================
# Schema Instances
# ============================================================

order_create_schema = OrderCreateSchema()

order_response_schema = OrderResponseSchema()

orders_response_schema = Schema.from_dict({
    "success": fields.Boolean(),
    "message": fields.String(),
    "data": fields.List(
        fields.Nested(OrderResponseSchema)
    ),
    "count": fields.Integer(),
})()

single_order_response_schema = Schema.from_dict({
    "success": fields.Boolean(),
    "message": fields.String(),
    "data": fields.Nested(OrderResponseSchema),
})()