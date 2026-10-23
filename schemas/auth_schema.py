import re

from marshmallow import Schema, fields, validate, validates, ValidationError


class UserSignupSchema(Schema):
    name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=100)
    )

    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )

    phone_number = fields.String(
        required=True,
        validate=validate.Length(min=10, max=20)
    )

    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, max=128)
    )

    @validates("name")
    def validate_name(self, value, **kwargs):
        if not value.strip():
            raise ValidationError("Name cannot be empty.")

        if not re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*", value, re.UNICODE):
            raise ValidationError("Name contains invalid characters.")

    @validates("phone_number")
    def validate_phone_number(self, value, **kwargs):
        if not re.fullmatch(r"\+?[0-9]{10,15}", value):
            raise ValidationError(
                "Enter a valid phone number containing 10–15 digits."
            )


class UserLoginSchema(Schema):
    email = fields.Email(required=True)

    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=1, max=128)
    )

class VendorLoginSchema(Schema):
    email = fields.Email(required=True)

    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=1, max=128)
    )