from flask import Blueprint
from flask_jwt_extended import get_jwt_identity

from middleware.vendor_middleware import vendor_required
from operations.vendor_operation import get_vendor_dashboard


vendor_bp = Blueprint(
    "vendor",
    __name__,
    url_prefix="/api/v1/vendor"
)


@vendor_bp.route("/dashboard", methods=["GET"])
@vendor_required
def vendor_dashboard():
    identity = get_jwt_identity()
    vendor_id = int(identity.split(":", 1)[1])

    response, status_code = get_vendor_dashboard(vendor_id)

    return response, status_code