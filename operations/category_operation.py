from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.category_table import Category


def create_category(data):
    try:
        category_name = data.get("category_name")
        slug = data.get("slug")

        if not isinstance(category_name, str) or not category_name.strip():
            return {
                "success": False,
                "message": "Category name is required."
            }, 400

        if not isinstance(slug, str) or not slug.strip():
            return {
                "success": False,
                "message": "Category slug is required."
            }, 400

        category_name = category_name.strip()
        slug = slug.strip().lower()

        if Category.query.filter_by(category_name=category_name).first():
            return {
                "success": False,
                "message": "Category name already exists."
            }, 409

        if Category.query.filter_by(slug=slug).first():
            return {
                "success": False,
                "message": "Category slug already exists."
            }, 409

        display_order = data.get("display_order", 0)

        try:
            display_order = int(display_order)
            if display_order < 0:
                raise ValueError
        except (ValueError, TypeError):
            return {
                "success": False,
                "message": "Display order must be a non-negative integer."
            }, 400

        category = Category(
            category_name=category_name,
            slug=slug,
            description=data.get("description"),
            image_url=data.get("image_url"),
            display_order=display_order,
            is_active=True
        )

        db.session.add(category)
        db.session.commit()

        return {
            "success": True,
            "message": "Category created successfully.",
            "data": category.to_dict()
        }, 201

    except IntegrityError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Category name or slug already exists."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Database error while creating category."
        }, 500


def get_categories():
    try:
        categories = Category.query.order_by(
            Category.display_order.asc(),
            Category.id.desc()
        ).all()

        return {
            "success": True,
            "count": len(categories),
            "data": [category.to_dict() for category in categories]
        }, 200

    except SQLAlchemyError:
        return {
            "success": False,
            "message": "Database error while fetching categories."
        }, 500


def get_category_by_id(category_id):
    category = db.session.get(Category, category_id)

    if category is None:
        return {
            "success": False,
            "message": "Category not found."
        }, 404

    return {
        "success": True,
        "data": category.to_dict()
    }, 200


def update_category(category_id, data):
    try:
        category = db.session.get(Category, category_id)

        if category is None:
            return {
                "success": False,
                "message": "Category not found."
            }, 404

        if "category_name" in data:
            category_name = data["category_name"]

            if not isinstance(category_name, str) or not category_name.strip():
                return {
                    "success": False,
                    "message": "Category name cannot be empty."
                }, 400

            category_name = category_name.strip()

            existing = Category.query.filter(
                Category.category_name == category_name,
                Category.id != category_id
            ).first()

            if existing:
                return {
                    "success": False,
                    "message": "Category name already exists."
                }, 409

            category.category_name = category_name

        if "slug" in data:
            slug = data["slug"]

            if not isinstance(slug, str) or not slug.strip():
                return {
                    "success": False,
                    "message": "Category slug cannot be empty."
                }, 400

            slug = slug.strip().lower()

            existing = Category.query.filter(
                Category.slug == slug,
                Category.id != category_id
            ).first()

            if existing:
                return {
                    "success": False,
                    "message": "Category slug already exists."
                }, 409

            category.slug = slug

        if "description" in data:
            category.description = data["description"]

        if "image_url" in data:
            category.image_url = data["image_url"]

        if "display_order" in data:
            try:
                display_order = int(data["display_order"])
                if display_order < 0:
                    raise ValueError
                category.display_order = display_order
            except (ValueError, TypeError):
                return {
                    "success": False,
                    "message": "Display order must be a non-negative integer."
                }, 400

        db.session.commit()

        return {
            "success": True,
            "message": "Category updated successfully.",
            "data": category.to_dict()
        }, 200

    except IntegrityError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Category name or slug already exists."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Database error while updating category."
        }, 500


def update_category_status(category_id, is_active):
    try:
        category = db.session.get(Category, category_id)

        if category is None:
            return {
                "success": False,
                "message": "Category not found."
            }, 404

        if not isinstance(is_active, bool):
            return {
                "success": False,
                "message": "is_active must be true or false."
            }, 400

        category.is_active = is_active
        db.session.commit()

        return {
            "success": True,
            "message": "Category status updated successfully.",
            "data": category.to_dict()
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Database error while updating category status."
        }, 500


def delete_category(category_id):
    try:
        category = db.session.get(Category, category_id)

        if category is None:
            return {
                "success": False,
                "message": "Category not found."
            }, 404

        db.session.delete(category)
        db.session.commit()

        return {
            "success": True,
            "message": "Category deleted successfully."
        }, 200

    except IntegrityError:
        db.session.rollback()
        return {
            "success": False,
            "message": (
                "Category cannot be deleted because products or "
                "subcategories may reference it."
            )
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        return {
            "success": False,
            "message": "Database error while deleting category."
        }, 500