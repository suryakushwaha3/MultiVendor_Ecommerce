import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from tables.product_image_table import ProductImage


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def save_product_images(product_id, image_files):
    """
    Save multiple product images and add their records
    to the database session.

    Database commit is handled by the calling route.
    """

    if not image_files:
        return {
            "success": True,
            "message": "No images provided.",
            "data": [],
            "saved_files": []
        }, 200

    upload_folder = os.path.abspath(
        os.path.join(
            current_app.root_path,
            "..",
            "uploads",
            "products"
        )
    )

    os.makedirs(upload_folder, exist_ok=True)

    saved_files = []
    image_records = []

    try:
        for index, image in enumerate(image_files):

            if not image or not image.filename:
                continue

            original_name = secure_filename(image.filename)

            if "." not in original_name:
                raise ValueError("Invalid image filename.")

            extension = original_name.rsplit(".", 1)[1].lower()

            if extension not in ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported image format: {original_name}"
                )

            if (
                not image.mimetype
                or not image.mimetype.startswith("image/")
            ):
                raise ValueError(
                    f"Invalid image type: {original_name}"
                )

            image.stream.seek(0, os.SEEK_END)
            file_size = image.stream.tell()
            image.stream.seek(0)

            if file_size == 0:
                raise ValueError(
                    f"Image file is empty: {original_name}"
                )

            if file_size > MAX_IMAGE_SIZE:
                raise ValueError(
                    f"Image must be 5 MB or smaller: {original_name}"
                )

            filename = f"{uuid.uuid4().hex}.{extension}"

            file_path = os.path.join(
                upload_folder,
                filename
            )

            image.save(file_path)
            saved_files.append(file_path)

            image_record = ProductImage(
                product_id=product_id,
                image_url=(
                    f"/api/v1/vendor/products/uploads/{filename}"
                ),
                alt_text=os.path.splitext(original_name)[0][:250],
                is_primary=(index == 0),
                display_order=index
            )

            db.session.add(image_record)
            image_records.append(image_record)

        return {
            "success": True,
            "message": "Product images added successfully.",
            "data": [
                {
                    "image_url": record.image_url,
                    "alt_text": record.alt_text,
                    "is_primary": record.is_primary,
                    "display_order": record.display_order
                }
                for record in image_records
            ],
            "saved_files": saved_files
        }, 201

    except (ValueError, OSError) as error:

        for file_path in saved_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                current_app.logger.exception(
                    "Failed to remove uploaded product image."
                )

        db.session.rollback()

        return {
            "success": False,
            "message": str(error),
            "saved_files": []
        }, 400