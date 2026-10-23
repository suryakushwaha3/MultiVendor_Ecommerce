from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.category_table import Category
from tables.subcategory_table import Subcategory


def create_subcategory(data):
    try:
        category_id = data.get("category_id")
        subcategory_name = data.get("subcategory_name")
        slug = data.get("slug")

        if isinstance(category_id, bool) or not isinstance(category_id, int):
            return {
                "success": False,
                "message": "category_id must be an integer."
            }, 400

        if category_id <= 0:
            return {
                "success": False,
                "message": "category_id must be greater than zero."
            }, 400

        if not isinstance(subcategory_name, str) or not subcategory_name.strip():
            return {
                "success": False,
                "message": "Subcategory name is required."
            }, 400

        if not isinstance(slug, str) or not slug.strip():
            return {
                "success": False,
                "message": "Subcategory slug is required."
            }, 400

        subcategory_name = subcategory_name.strip()
        slug = slug.strip().lower()

        category = db.session.get(Category, category_id)

        if category is None:
            return {
                "success": False,
                "message": "Category not found."
            }, 404

        if not category.is_active:
            return {
                "success": False,
                "message": "Cannot add a subcategory to an inactive category."
            }, 400

        existing_slug = Subcategory.query.filter_by(slug=slug).first()

        if existing_slug:
            return {
                "success": False,
                "message": "Subcategory slug already exists."
            }, 409

        display_order = data.get("display_order", 0)

        if isinstance(display_order, bool) or not isinstance(display_order, int):
            return {
                "success": False,
                "message": "Display order must be a non-negative integer."
            }, 400

        if display_order < 0:
            return {
                "success": False,
                "message": "Display order must be a non-negative integer."
            }, 400

        description = data.get("description")
        image_url = data.get("image_url")

        if description is not None and not isinstance(description, str):
            return {
                "success": False,
                "message": "Description must be a string or null."
            }, 400

        if image_url is not None and not isinstance(image_url, str):
            return {
                "success": False,
                "message": "Image URL must be a string or null."
            }, 400

        subcategory = Subcategory(
            category_id=category_id,
            subcategory_name=subcategory_name,
            slug=slug,
            description=description,
            image_url=image_url,
            display_order=display_order,
            is_active=True
        )

        db.session.add(subcategory)
        db.session.commit()

        return {
            "success": True,
            "message": "Subcategory created successfully.",
            "data": subcategory.to_dict()
        }, 201

    except IntegrityError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Subcategory slug already exists or a related record is invalid."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while creating subcategory."
        }, 500


def get_subcategories():
    try:
        subcategories = Subcategory.query.order_by(
            Subcategory.display_order.asc(),
            Subcategory.id.desc()
        ).all()

        return {
            "success": True,
            "count": len(subcategories),
            "data": [
                subcategory.to_dict()
                for subcategory in subcategories
            ]
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while fetching subcategories."
        }, 500


def get_subcategory_by_id(subcategory_id):
    try:
        subcategory = db.session.get(Subcategory, subcategory_id)

        if subcategory is None:
            return {
                "success": False,
                "message": "Subcategory not found."
            }, 404

        return {
            "success": True,
            "data": subcategory.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while fetching subcategory."
        }, 500


def get_subcategories_by_category(category_id):
    try:
        if category_id <= 0:
            return {
                "success": False,
                "message": "category_id must be greater than zero."
            }, 400

        category = db.session.get(Category, category_id)

        if category is None:
            return {
                "success": False,
                "message": "Category not found."
            }, 404

        subcategories = Subcategory.query.filter_by(
            category_id=category_id
        ).order_by(
            Subcategory.display_order.asc(),
            Subcategory.id.desc()
        ).all()

        return {
            "success": True,
            "category_id": category_id,
            "count": len(subcategories),
            "data": [
                subcategory.to_dict()
                for subcategory in subcategories
            ]
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while fetching category subcategories."
        }, 500


def update_subcategory(subcategory_id, data):
    try:
        subcategory = db.session.get(Subcategory, subcategory_id)

        if subcategory is None:
            return {
                "success": False,
                "message": "Subcategory not found."
            }, 404

        if "category_id" in data:
            category_id = data["category_id"]

            if (
                isinstance(category_id, bool)
                or not isinstance(category_id, int)
                or category_id <= 0
            ):
                return {
                    "success": False,
                    "message": "category_id must be a positive integer."
                }, 400

            category = db.session.get(Category, category_id)

            if category is None:
                return {
                    "success": False,
                    "message": "Category not found."
                }, 404

            if not category.is_active:
                return {
                    "success": False,
                    "message": "Cannot assign a subcategory to an inactive category."
                }, 400

            subcategory.category_id = category_id

        if "subcategory_name" in data:
            name = data["subcategory_name"]

            if not isinstance(name, str) or not name.strip():
                return {
                    "success": False,
                    "message": "Subcategory name cannot be empty."
                }, 400

            subcategory.subcategory_name = name.strip()

        if "slug" in data:
            slug = data["slug"]

            if not isinstance(slug, str) or not slug.strip():
                return {
                    "success": False,
                    "message": "Subcategory slug cannot be empty."
                }, 400

            slug = slug.strip().lower()

            existing = Subcategory.query.filter(
                Subcategory.slug == slug,
                Subcategory.id != subcategory_id
            ).first()

            if existing:
                return {
                    "success": False,
                    "message": "Subcategory slug already exists."
                }, 409

            subcategory.slug = slug

        if "description" in data:
            description = data["description"]

            if description is not None and not isinstance(description, str):
                return {
                    "success": False,
                    "message": "Description must be a string or null."
                }, 400

            subcategory.description = description

        if "image_url" in data:
            image_url = data["image_url"]

            if image_url is not None and not isinstance(image_url, str):
                return {
                    "success": False,
                    "message": "Image URL must be a string or null."
                }, 400

            subcategory.image_url = image_url

        if "display_order" in data:
            display_order = data["display_order"]

            if (
                isinstance(display_order, bool)
                or not isinstance(display_order, int)
                or display_order < 0
            ):
                return {
                    "success": False,
                    "message": "Display order must be a non-negative integer."
                }, 400

            subcategory.display_order = display_order

        if "is_active" in data:
            is_active = data["is_active"]

            if not isinstance(is_active, bool):
                return {
                    "success": False,
                    "message": "is_active must be true or false."
                }, 400

            subcategory.is_active = is_active

        db.session.commit()

        return {
            "success": True,
            "message": "Subcategory updated successfully.",
            "data": subcategory.to_dict()
        }, 200

    except IntegrityError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Subcategory slug already exists or a related record is invalid."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while updating subcategory."
        }, 500


def update_subcategory_status(subcategory_id, is_active):
    try:
        subcategory = db.session.get(Subcategory, subcategory_id)

        if subcategory is None:
            return {
                "success": False,
                "message": "Subcategory not found."
            }, 404

        if not isinstance(is_active, bool):
            return {
                "success": False,
                "message": "is_active must be true or false."
            }, 400

        subcategory.is_active = is_active
        db.session.commit()

        return {
            "success": True,
            "message": "Subcategory status updated successfully.",
            "data": subcategory.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while updating subcategory status."
        }, 500


def delete_subcategory(subcategory_id):
    try:
        subcategory = db.session.get(Subcategory, subcategory_id)

        if subcategory is None:
            return {
                "success": False,
                "message": "Subcategory not found."
            }, 404

        db.session.delete(subcategory)
        db.session.commit()

        return {
            "success": True,
            "message": "Subcategory deleted successfully."
        }, 200

    except IntegrityError:
        db.session.rollback()

        return {
            "success": False,
            "message": (
                "Subcategory cannot be deleted because products "
                "or other records may reference it."
            )
        }, 409

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Database error while deleting subcategory."
        }, 500
