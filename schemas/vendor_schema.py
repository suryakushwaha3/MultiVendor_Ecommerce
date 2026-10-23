from marshmallow import (
    Schema,
    fields,
    validate,
    validates,
    ValidationError,
)


# ============================================================
# Vendor Registration Schema
# ============================================================

class VendorCreateSchema(Schema):

    name = fields.String(
        required=True,
        validate=validate.Length(
            min=2,
            max=100,
            error="Name must be between 2 and 100 characters."
        )
    )

    email = fields.Email(
        required=True,
        validate=validate.Length(
            max=255,
            error="Email cannot exceed 255 characters."
        )
    )

    phone_number = fields.String(
        required=True,
        validate=validate.Length(
            min=10,
            max=20,
            error="Phone number must be between 10 and 20 characters."
        )
    )

    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(
            min=8,
            max=128,
            error="Password must be between 8 and 128 characters."
        )
    )

    business_name = fields.String(
        required=True,
        validate=validate.Length(
            min=2,
            max=150,
            error="Business name must be between 2 and 150 characters."
        )
    )

    business_address = fields.String(
        allow_none=True,
        load_default=None
    )

    @validates("name")
    def validate_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Name cannot be empty.")

    @validates("email")
    def validate_email(self, value, **kwargs):
        if value != value.strip():
            raise ValidationError(
                "Email cannot contain surrounding spaces."
            )

    @validates("phone_number")
    def validate_phone_number(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Phone number cannot be empty.")

    @validates("business_name")
    def validate_business_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Business name cannot be empty.")


# ============================================================
# Vendor Login Schema
# ============================================================

class VendorLoginSchema(Schema):

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(
            min=1,
            max=128,
            error="Password is required."
        )
    )


# ============================================================
# Vendor Profile Update Schema
# ============================================================

class VendorUpdateSchema(Schema):

    name = fields.String(
        validate=validate.Length(min=2, max=100)
    )

    email = fields.Email(
        validate=validate.Length(max=255)
    )

    phone_number = fields.String(
        validate=validate.Length(min=10, max=20)
    )

    business_name = fields.String(
        validate=validate.Length(min=2, max=150)
    )

    business_address = fields.String(
        allow_none=True
    )

    @validates("name")
    def validate_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Name cannot be empty.")

    @validates("email")
    def validate_email(self, value, **kwargs):
        if value != value.strip():
            raise ValidationError(
                "Email cannot contain surrounding spaces."
            )

    @validates("phone_number")
    def validate_phone_number(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Phone number cannot be empty.")

    @validates("business_name")
    def validate_business_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Business name cannot be empty.")


# ============================================================
# Admin Vendor Management Schema
# ============================================================

class AdminVendorUpdateSchema(Schema):

    is_approved = fields.Boolean()

    is_active = fields.Boolean()


# ============================================================
# Vendor Response Schema
# ============================================================

class VendorResponseSchema(Schema):

    id = fields.Integer(dump_only=True)

    name = fields.String()

    email = fields.Email()

    phone_number = fields.String()

    business_name = fields.String()

    business_address = fields.String(allow_none=True)

    is_approved = fields.Boolean()

    is_active = fields.Boolean()

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

vendor_create_schema = VendorCreateSchema()

vendor_login_schema = VendorLoginSchema()

vendor_update_schema = VendorUpdateSchema()

admin_vendor_update_schema = AdminVendorUpdateSchema()

vendor_response_schema = VendorResponseSchema()

vendor_response_list_schema = VendorResponseSchema(many=True)
 