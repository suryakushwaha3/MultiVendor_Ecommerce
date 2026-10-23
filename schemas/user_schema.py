from marshmallow import (
    Schema,
    fields,
    validate,
    validates,
    ValidationError,
)


# ============================================================
# User Registration Schema
# ============================================================

class UserCreateSchema(Schema):

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

    @validates("name")
    def validate_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Name cannot be empty.")

    @validates("email")
    def validate_email(self, value, **kwargs):
        if value != value.strip():
            raise ValidationError("Email cannot contain surrounding spaces.")

    @validates("phone_number")
    def validate_phone_number(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Phone number cannot be empty.")


# ============================================================
# User Login Schema
# ============================================================

class UserLoginSchema(Schema):

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
# User Update Schema
# ============================================================

class UserUpdateSchema(Schema):

    name = fields.String(
        validate=validate.Length(min=2, max=100)
    )

    email = fields.Email(
        validate=validate.Length(max=255)
    )

    phone_number = fields.String(
        validate=validate.Length(min=10, max=20)
    )

    @validates("name")
    def validate_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Name cannot be empty.")

    @validates("email")
    def validate_email(self, value, **kwargs):
        if value != value.strip():
            raise ValidationError("Email cannot contain surrounding spaces.")

    @validates("phone_number")
    def validate_phone_number(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Phone number cannot be empty.")


# ============================================================
# Admin User Update Schema
# ============================================================

class AdminUserUpdateSchema(Schema):

    name = fields.String(
        validate=validate.Length(min=2, max=100)
    )

    email = fields.Email(
        validate=validate.Length(max=255)
    )

    phone_number = fields.String(
        validate=validate.Length(min=10, max=20)
    )

    role = fields.String(
        validate=validate.OneOf(
            ["customer", "vendor", "admin"],
            error="Role must be customer, vendor or admin."
        )
    )

    is_active = fields.Boolean()


# ============================================================
# User Response Schema
# ============================================================

class UserResponseSchema(Schema):

    id = fields.Integer(dump_only=True)

    name = fields.String()

    email = fields.Email()

    phone_number = fields.String()

    role = fields.String()

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

user_create_schema = UserCreateSchema()

user_login_schema = UserLoginSchema()

user_update_schema = UserUpdateSchema()

admin_user_update_schema = AdminUserUpdateSchema()

user_response_schema = UserResponseSchema()

user_response_list_schema = UserResponseSchema(many=True)