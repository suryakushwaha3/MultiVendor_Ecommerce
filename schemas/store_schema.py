from marshmallow import Schema, fields, validate


class StoreCreateSchema(Schema):
    store_name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=150)
    )

    slug = fields.String(
        required=True,
        validate=[
            validate.Length(min=2, max=180),
            validate.Regexp(
                r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                error="Slug must contain lowercase letters, numbers, and hyphens only."
            )
        ]
    )

    description = fields.String(
        load_default=None,
        allow_none=True
    )

    logo_url = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=500)
    )

    banner_url = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=500)
    )

    address = fields.String(
        load_default=None,
        allow_none=True
    )


class StoreUpdateSchema(Schema):
    store_name = fields.String(
        validate=validate.Length(min=2, max=150)
    )

    slug = fields.String(
        validate=[
            validate.Length(min=2, max=180),
            validate.Regexp(
                r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                error="Slug must contain lowercase letters, numbers, and hyphens only."
            )
        ]
    )

    description = fields.String(allow_none=True)

    logo_url = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )

    banner_url = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )

    address = fields.String(allow_none=True)


class StoreResponseSchema(Schema):
    id = fields.Integer(dump_only=True)
    vendor_id = fields.Integer(dump_only=True)
    store_name = fields.String(dump_only=True)
    slug = fields.String(dump_only=True)
    description = fields.String(dump_only=True, allow_none=True)
    logo_url = fields.String(dump_only=True, allow_none=True)
    banner_url = fields.String(dump_only=True, allow_none=True)
    address = fields.String(dump_only=True, allow_none=True)
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True, allow_none=True)
    updated_at = fields.DateTime(dump_only=True, allow_none=True)