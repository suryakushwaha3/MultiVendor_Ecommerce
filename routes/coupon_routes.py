
from flask import Blueprint, jsonify, request

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.coupon_operation import (
    create_coupon,
    get_coupons,
    get_coupon_by_id,
    update_coupon,
    set_coupon_status,
    delete_coupon,
)

coupon_bp = Blueprint(
    "coupon",
    __name__,
    url_prefix="/api/v1/admin/coupons",
)


def make_response(result):
    body, status_code = result
    return jsonify(body), status_code


@coupon_bp.route("", methods=["POST"])
@token_required
@role_required("admin")
def create_coupon_route():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            "success": False,
            "message": "A valid JSON body is required.",
        }), 400

    return make_response(create_coupon(data))


@coupon_bp.route("", methods=["GET"])
@token_required
@role_required("admin")
def get_coupons_route():
    return make_response(get_coupons())


@coupon_bp.route("/<int:coupon_id>", methods=["GET"])
@token_required
@role_required("admin")
def get_coupon_route(coupon_id):
    return make_response(get_coupon_by_id(coupon_id))


@coupon_bp.route("/<int:coupon_id>", methods=["PUT", "PATCH"])
@token_required
@role_required("admin")
def update_coupon_route(coupon_id):
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            "success": False,
            "message": "A valid JSON body is required.",
        }), 400

    return make_response(update_coupon(coupon_id, data))


@coupon_bp.route("/<int:coupon_id>/status", methods=["PATCH"])
@token_required
@role_required("admin")
def update_coupon_status_route(coupon_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "is_active" not in data:
        return jsonify({
            "success": False,
            "message": "is_active is required.",
        }), 400

    return make_response(
        set_coupon_status(coupon_id, data["is_active"])
    )


@coupon_bp.route("/<int:coupon_id>", methods=["DELETE"])
@token_required
@role_required("admin")
def delete_coupon_route(coupon_id):
    return make_response(delete_coupon(coupon_id))
