from flask import Blueprint, jsonify, request

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.commission_operation import (
    create_commission,
    get_commissions,
    get_commission_by_id,
    update_commission,
    set_commission_status,
    delete_commission,
)

commission_bp = Blueprint(
    "commission",
    __name__,
    url_prefix="/api/v1/admin/commissions",
)


def make_response(result):
    body, status_code = result
    return jsonify(body), status_code


@commission_bp.route("", methods=["POST"])
@token_required
@role_required("admin")
def create_commission_route():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            "success": False,
            "message": "A valid JSON body is required.",
        }), 400

    return make_response(create_commission(data))


@commission_bp.route("", methods=["GET"])
@token_required
@role_required("admin")
def get_commissions_route():
    return make_response(get_commissions())


@commission_bp.route("/<int:commission_id>", methods=["GET"])
@token_required
@role_required("admin")
def get_commission_route(commission_id):
    return make_response(get_commission_by_id(commission_id))


@commission_bp.route("/<int:commission_id>", methods=["PUT", "PATCH"])
@token_required
@role_required("admin")
def update_commission_route(commission_id):
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            "success": False,
            "message": "A valid JSON body is required.",
        }), 400

    return make_response(update_commission(commission_id, data))


@commission_bp.route("/<int:commission_id>/status", methods=["PATCH"])
@token_required
@role_required("admin")
def update_commission_status_route(commission_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "status" not in data:
        return jsonify({
            "success": False,
            "message": "status is required.",
        }), 400

    return make_response(
        set_commission_status(commission_id, data["status"])
    )


@commission_bp.route("/<int:commission_id>", methods=["DELETE"])
@token_required
@role_required("admin")
def delete_commission_route(commission_id):
    return make_response(delete_commission(commission_id))
