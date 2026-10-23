from marshmallow import Schema, fields, validate, validates_schema, ValidationError


# =========================================================
# Constants
# =========================================================

ALLOWED_ADDRESS_TYPES = ("home", "work", "other")


# =========================================================
# Create Address Schema
# =========================================================

class AddressCreateSchema(Schema):
    """Validate data for creating a customer address."""

    full_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
    )

    phone_number = fields.String(
        required=True,
        validate=validate.Length(min=1, max=20),
    )

    address_line1 = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
    )

    address_line2 = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=255),
    )

    landmark = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=150),
    )

    city = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
    )

    state = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
    )

    pincode = fields.String(
        required=True,
        validate=validate.Length(min=1, max=10),
    )

    country = fields.String(
        load_default="India",
        validate=validate.Length(min=1, max=100),
    )

    address_type = fields.String(
        load_default="home",
        validate=validate.OneOf(ALLOWED_ADDRESS_TYPES),
    )

    is_default = fields.Boolean(
        load_default=False,
    )

    class Meta:
        unknown = "raise"

    @validates_schema
    def validate_required_strings(self, data, **kwargs):
        """Reject empty strings for required fields."""

        required_fields = (
            "full_name",
            "phone_number",
            "address_line1",
            "city",
            "state",
            "pincode",
        )

        errors = {}

        for field_name in required_fields:
            value = data.get(field_name)

            if isinstance(value, str) and not value.strip():
                errors[field_name] = ["This field is required."]

            elif isinstance(value, str):
                data[field_name] = value.strip()

        if errors:
            raise ValidationError(errors)


# =========================================================
# Update Address Schema
# =========================================================

class AddressUpdateSchema(Schema):
    """Validate partial updates to an existing address."""

    full_name = fields.String(
        validate=validate.Length(min=1, max=100),
    )

    phone_number = fields.String(
        validate=validate.Length(min=1, max=20),
    )

    address_line1 = fields.String(
        validate=validate.Length(min=1, max=255),
    )

    address_line2 = fields.String(
        allow_none=True,
        validate=validate.Length(max=255),
    )

    landmark = fields.String(
        allow_none=True,
        validate=validate.Length(max=150),
    )

    city = fields.String(
        validate=validate.Length(min=1, max=100),
    )

    state = fields.String(
        validate=validate.Length(min=1, max=100),
    )

    pincode = fields.String(
        validate=validate.Length(min=1, max=10),
    )

    country = fields.String(
        validate=validate.Length(min=1, max=100),
    )

    address_type = fields.String(
        validate=validate.OneOf(ALLOWED_ADDRESS_TYPES),
    )

    is_default = fields.Boolean()

    class Meta:
        unknown = "raise"

    @validates_schema
    def validate_non_empty_strings(self, data, **kwargs):
        """Reject empty strings for fields that are supplied."""

        errors = {}

        for field_name, value in data.items():
            if field_name in {
                "address_line2",
                "landmark",
            }:
                continue

            if isinstance(value, str):
                value = value.strip()

                if not value:
                    errors[field_name] = [
                        "This field cannot be empty."
                    ]
                else:
                    data[field_name] = value

        if errors:
            raise ValidationError(errors)


# =========================================================
# Address Response Schema
# =========================================================

class AddressResponseSchema(Schema):
    """Serialize one address in API responses."""

    id = fields.Integer()
    user_id = fields.Integer()

    full_name = fields.String()
    phone_number = fields.String()

    address_line1 = fields.String()
    address_line2 = fields.String(allow_none=True)
    landmark = fields.String(allow_none=True)

    city = fields.String()
    state = fields.String()
    pincode = fields.String()
    country = fields.String()

    address_type = fields.String()
    is_default = fields.Boolean()

    created_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)


# =========================================================
# Response Schemas
# =========================================================

class SingleAddressResponseSchema(Schema):
    """Serialize a single-address API response."""

    success = fields.Boolean()
    message = fields.String()
    data = fields.Nested(
        AddressResponseSchema,
        allow_none=True,
    )


class AddressListResponseSchema(Schema):
    """Serialize the customer-addresses API response."""

    success = fields.Boolean()
    message = fields.String()
    count = fields.Integer()
    data = fields.List(
        fields.Nested(AddressResponseSchema)
    )


# =========================================================
# Reusable Schema Instances
# =========================================================

address_create_schema = AddressCreateSchema()
address_update_schema = AddressUpdateSchema()

address_response_schema = AddressResponseSchema()
single_address_response_schema = SingleAddressResponseSchema()
addresses_response_schema = AddressListResponseSchema()
 