from flask import Blueprint, jsonify, request

from operations.category_operation import (
    create_category,
    get_categories,
    get_category_by_id,
    update_category,
    update_category_status,
    delete_category
)


category_bp = Blueprint(
    "category",
    __name__,
    url_prefix="/api/v1/categories"
)


# Create Category
@category_bp.route("", methods=["POST"])
def add_category():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be valid JSON."
        }), 400

    response, status_code = create_category(data)

    return jsonify(response), status_code


# Get All Categories
@category_bp.route("", methods=["GET"])
def list_categories():
    response, status_code = get_categories()

    return jsonify(response), status_code


# Get Category Details
@category_bp.route("/<int:category_id>", methods=["GET"])
def category_details(category_id):
    response, status_code = get_category_by_id(category_id)

    return jsonify(response), status_code


# Update Category
@category_bp.route("/<int:category_id>", methods=["PATCH"])
def edit_category(category_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be valid JSON."
        }), 400

    response, status_code = update_category(category_id, data)

    return jsonify(response), status_code


# Update Category Status
@category_bp.route("/<int:category_id>/status", methods=["PATCH"])
def change_category_status(category_id):
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

    response, status_code = update_category_status(
        category_id,
        data["is_active"]
    )

    return jsonify(response), status_code


# Delete Category
@category_bp.route("/<int:category_id>", methods=["DELETE"])
def remove_category(category_id):
    response, status_code = delete_category(category_id)

    return jsonify(response), status_code