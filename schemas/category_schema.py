import re
from marshmallow import Schema, fields, validate, validates, validates_schema, ValidationError


class CategoryCreateSchema(Schema):
    category_name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=100)
    )

    slug = fields.String(
        required=True,
        validate=[
            validate.Length(min=2, max=120),
            validate.Regexp(
                r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                error="Slug must contain lowercase letters, numbers and hyphens only."
            )
        ]
    )

    description = fields.String(
        load_default=None,
        allow_none=True
    )

    image_url = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=500)
    )

    is_active = fields.Boolean(
        load_default=True
    )

    display_order = fields.Integer(
        load_default=0,
        validate=validate.Range(min=0)
    )

    @validates("category_name")
    def validate_category_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Category name cannot be empty.")

    @validates("slug")
    def normalize_slug(self, value, **kwargs):
        if value != value.strip():
            raise ValidationError("Slug cannot contain surrounding spaces.")

    @validates("image_url")
    def validate_image_url(self, value, **kwargs):
        if value is None:
            return

        if not value.strip():
            raise ValidationError("Image URL cannot be empty.")

        if not value.startswith(("https://", "http://")):
            raise ValidationError("Image URL must start with http:// or https://.")


class CategoryUpdateSchema(Schema):
    category_name = fields.String(
        validate=validate.Length(min=2, max=100)
    )

    slug = fields.String(
        validate=[
            validate.Length(min=2, max=120),
            validate.Regexp(
                r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                error="Slug must contain lowercase letters, numbers and hyphens only."
            )
        ]
    )

    description = fields.String(
        allow_none=True
    )

    image_url = fields.String(
        allow_none=True,
        validate=validate.Length(max=500)
    )

    is_active = fields.Boolean()

    display_order = fields.Integer(
        validate=validate.Range(min=0)
    )

    @validates("category_name")
    def validate_category_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Category name cannot be empty.")

    @validates("image_url")
    def validate_image_url(self, value, **kwargs):
        if value is None:
            return

        if not value.strip():
            raise ValidationError("Image URL cannot be empty.")

        if not value.startswith(("https://", "http://")):
            raise ValidationError("Image URL must start with http:// or https://.")

    @validates_schema
    def validate_update_data(self, data, **kwargs):
        if not data:
            raise ValidationError(
                "At least one field is required for an update."
            )


class CategoryResponseSchema(Schema):
    id = fields.Integer(dump_only=True)
    category_name = fields.String()
    slug = fields.String()
    description = fields.String(allow_none=True)
    image_url = fields.String(allow_none=True)
    is_active = fields.Boolean()
    display_order = fields.Integer()
    created_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)


category_create_schema = CategoryCreateSchema()
category_update_schema = CategoryUpdateSchema()
category_response_schema = CategoryResponseSchema()
category_response_list_schema = CategoryResponseSchema(many=True)
 