from flask import Blueprint, request
from marshmallow import ValidationError

from middleware.auth_middleware import token_required
from schemas.payment_schema import PaymentCreateSchema
from operations.payment_operation import create_payment
from flask_jwt_extended import get_jwt_identity


payment_bp = Blueprint(
    "payment",
    __name__,
    url_prefix="/api/v1/payments"
)

payment_create_schema = PaymentCreateSchema()


@payment_bp.route("/initiate", methods=["POST"])
@token_required
def initiate_payment():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "success": False,
            "message": "A valid JSON request body is required."
        }, 400

    try:
        validated_data = payment_create_schema.load(data)

    except ValidationError as error:
        return {
            "success": False,
            "message": "Validation failed.",
            "errors": error.messages
        }, 400

    identity = get_jwt_identity()

    # Payment initiation is only available to customer accounts.
    if not isinstance(identity, str) or not identity.isdigit():
        return {
            "success": False,
            "message": "Customer authentication required."
        }, 403

    response, status_code = create_payment(
        user_id=int(identity),
        data=validated_data
    )

    return response, status_code