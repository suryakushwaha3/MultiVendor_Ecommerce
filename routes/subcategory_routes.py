from flask import Blueprint, jsonify, request

from operations.subcategory_operation import (
    create_subcategory,
    get_subcategories,
    get_subcategory_by_id,
    get_subcategories_by_category,
    update_subcategory,
    update_subcategory_status,
    delete_subcategory,
)


subcategory_bp = Blueprint(
    "subcategory",
    __name__,
    url_prefix="/api/v1/subcategories"
)


# Create Subcategory
@subcategory_bp.route("", methods=["POST"])
def add_subcategory():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be valid JSON."
        }), 400

    response, status_code = create_subcategory(data)

    return jsonify(response), status_code


# Get All Subcategories
@subcategory_bp.route("", methods=["GET"])
def list_subcategories():
    response, status_code = get_subcategories()

    return jsonify(response), status_code


# Get Subcategories By Category
@subcategory_bp.route("/category/<int:category_id>", methods=["GET"])
def list_category_subcategories(category_id):
    response, status_code = get_subcategories_by_category(category_id)

    return jsonify(response), status_code


# Get Subcategory Details
@subcategory_bp.route("/<int:subcategory_id>", methods=["GET"])
def subcategory_details(subcategory_id):
    response, status_code = get_subcategory_by_id(subcategory_id)

    return jsonify(response), status_code


# Update Subcategory
@subcategory_bp.route("/<int:subcategory_id>", methods=["PATCH"])
def edit_subcategory(subcategory_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be valid JSON."
        }), 400

    response, status_code = update_subcategory(subcategory_id, data)

    return jsonify(response), status_code


# Update Subcategory Status
@subcategory_bp.route("/<int:subcategory_id>/status", methods=["PATCH"])
def change_subcategory_status(subcategory_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be valid JSON."
        }), 400

    if "is_active" not in data:
        return jsonify({
            "success": False,
            "message": "is_active field is required."
        }), 400

    response, status_code = update_subcategory_status(
        subcategory_id,
        data["is_active"]
    )

    return jsonify(response), status_code


# Delete Subcategory
@subcategory_bp.route("/<int:subcategory_id>", methods=["DELETE"])
def remove_subcategory(subcategory_id):
    response, status_code = delete_subcategory(subcategory_id)

    return jsonify(response), status_code
 