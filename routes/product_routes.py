import os

from flask import (
    Blueprint,
    jsonify,
    request,
    current_app,
    send_from_directory
)

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from middleware.vendor_middleware import vendor_required

from tables.product_table import Product

from operations.product_operation import (
    create_product,
    get_vendor_products,
    get_vendor_product_by_id,
    update_product,
    update_product_status,
    delete_product,
)

from operations.product_image_operation import save_product_images


product_bp = Blueprint(
    "product",
    __name__,
    url_prefix="/api/v1/vendor/products"
)


# =========================================================
# Create Product + Upload Multiple Images
# =========================================================

@product_bp.route("", methods=["POST"])
@vendor_required
def add_product():
    """Create a product and upload its images in one request."""

    data = request.form.to_dict()
    image_files = request.files.getlist("images")

    if not data:
        return jsonify({
            "success": False,
            "message": "Product details are required as form data."
        }), 400

    image_files = [
        image for image in image_files
        if image and image.filename
    ]

    if not image_files:
        return jsonify({
            "success": False,
            "message": "At least one product image is required."
        }), 400

    result, status_code = create_product(
        data=data,
        vendor_id=request.vendor_id,
        commit=False
    )

    if status_code != 201:
        return jsonify(result), status_code

    product_id = result["data"]["id"]
    saved_files = []

    try:
        image_result, image_status = save_product_images(
            product_id=product_id,
            image_files=image_files
        )

        saved_files = image_result.get("saved_files", [])

        if image_status != 201 or not image_result.get("success"):
            db.session.rollback()

            for file_path in saved_files:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except OSError:
                    current_app.logger.exception(
                        "Failed to clean up product image."
                    )

            return jsonify({
                "success": False,
                "message": image_result.get(
                    "message",
                    "Product image upload failed."
                )
            }), image_status

        # Save product and image records in one transaction.
        db.session.commit()

        product = db.session.get(Product, product_id)

        if product is None:
            return jsonify({
                "success": False,
                "message": "Product was saved but could not be retrieved."
            }), 500

        return jsonify({
            "success": True,
            "message": "Product and images created successfully.",
            "data": product.to_dict()
        }), 201

    except SQLAlchemyError:
        db.session.rollback()

        for file_path in saved_files:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except OSError:
                current_app.logger.exception(
                    "Failed to clean up product image."
                )

        return jsonify({
            "success": False,
            "message": "Database error while saving product images."
        }), 500


# =========================================================
# Get All Vendor Products
# =========================================================

@product_bp.route("", methods=["GET"])
@vendor_required
def list_products():
    """Get all products belonging to the authenticated vendor."""

    store_id = request.args.get("store_id", type=int)

    if request.args.get("store_id") and store_id is None:
        return jsonify({
            "success": False,
            "message": "store_id must be a valid integer."
        }), 400

    result, status_code = get_vendor_products(
        vendor_id=request.vendor_id,
        store_id=store_id
    )

    return jsonify(result), status_code


# =========================================================
# Get Product Details
# =========================================================

@product_bp.route("/<int:product_id>", methods=["GET"])
@vendor_required
def product_details(product_id):
    """Get details of a specific vendor-owned product."""

    result, status_code = get_vendor_product_by_id(
        product_id=product_id,
        vendor_id=request.vendor_id
    )

    return jsonify(result), status_code


# =========================================================
# Update Product
# =========================================================

@product_bp.route("/<int:product_id>", methods=["PATCH"])
@vendor_required
def edit_product(product_id):
    """Update a vendor-owned product."""

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "success": False,
            "message": "A non-empty JSON object is required."
        }), 400

    result, status_code = update_product(
        product_id=product_id,
        vendor_id=request.vendor_id,
        data=data
    )

    return jsonify(result), status_code


# =========================================================
# Update Product Status
# =========================================================

@product_bp.route(
    "/<int:product_id>/status",
    methods=["PATCH"]
)
@vendor_required
def change_product_status(product_id):
    """Activate or deactivate a product."""

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or "is_active" not in data:
        return jsonify({
            "success": False,
            "message": "is_active is required."
        }), 400

    value = data["is_active"]

    if isinstance(value, bool):
        is_active = value

    elif isinstance(value, str) and value.lower() in (
        "true", "false", "1", "0"
    ):
        is_active = value.lower() in ("true", "1")

    else:
        return jsonify({
            "success": False,
            "message": "is_active must be true or false."
        }), 400

    result, status_code = update_product_status(
        product_id=product_id,
        vendor_id=request.vendor_id,
        is_active=is_active
    )

    return jsonify(result), status_code


# =========================================================
# Delete Product
# =========================================================

@product_bp.route("/<int:product_id>", methods=["DELETE"])
@vendor_required
def remove_product(product_id):
    """Delete a vendor-owned product."""

    result, status_code = delete_product(
        product_id=product_id,
        vendor_id=request.vendor_id
    )

    return jsonify(result), status_code


# =========================================================
# Serve Product Images
# =========================================================

@product_bp.route(
    "/uploads/<path:filename>",
    methods=["GET"]
)
def product_image(filename):
    """Serve uploaded product images."""

    upload_folder = os.path.abspath(
        os.path.join(
            current_app.root_path,
            "..",
            "uploads",
            "products"
        )
    )

    return send_from_directory(
        upload_folder,
        filename
    )