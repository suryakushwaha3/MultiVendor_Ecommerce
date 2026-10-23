from flask import Blueprint, jsonify, request

from operations.banner_operation import (
    create_banner,
    get_banners,
    get_banner_by_id,
    update_banner,
    update_banner_status,
    delete_banner,
)


banner_bp = Blueprint(
    "banner",
    __name__,
    url_prefix="/api/v1/banners"
)


def _response(result):
    body, status_code = result
    return jsonify(body), status_code


# =========================================================
# Get All Banners / Create Banner
# =========================================================

@banner_bp.route("", methods=["GET", "POST"])
def banners():
    if request.method == "POST":
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Request body must be a valid JSON object."
            }), 400

        return _response(create_banner(data))

    position = request.args.get("position")
    active_only = request.args.get("active_only", "false").lower()
    visible_only = request.args.get("visible_only", "false").lower()

    if active_only not in ("true", "false"):
        return jsonify({
            "success": False,
            "message": "active_only must be true or false."
        }), 400

    if visible_only not in ("true", "false"):
        return jsonify({
            "success": False,
            "message": "visible_only must be true or false."
        }), 400

    return _response(
        get_banners(
            position=position,
            active_only=active_only == "true",
            visible_only=visible_only == "true"
        )
    )


# =========================================================
# Get, Update, Delete Banner by ID
# =========================================================

@banner_bp.route("/<int:banner_id>", methods=["GET", "PATCH", "DELETE"])
def banner_details(banner_id):
    if request.method == "GET":
        return _response(get_banner_by_id(banner_id))

    if request.method == "PATCH":
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Request body must be a valid JSON object."
            }), 400

        return _response(update_banner(banner_id, data))

    return _response(delete_banner(banner_id))


# =========================================================
# Activate / Deactivate Banner
# =========================================================

@banner_bp.route("/<int:banner_id>/status", methods=["PATCH"])
def banner_status(banner_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be a valid JSON object."
        }), 400

    if "is_active" not in data:
        return jsonify({
            "success": False,
            "message": "is_active is required."
        }), 400

    return _response(
        update_banner_status(
            banner_id=banner_id,
            is_active=data["is_active"]
        )
    )
 