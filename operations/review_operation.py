from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.review_table import Review
from tables.product_table import Product
from tables.order_table import Order
from tables.order_item_table import OrderItem


def _error(message, status_code):
    return {
        "success": False,
        "message": message,
    }, status_code


def _get_review(review_id, user_id=None):
    query = select(Review).where(Review.id == review_id)

    if user_id is not None:
        query = query.where(Review.user_id == user_id)

    return db.session.execute(query).scalar_one_or_none()


# =========================================================
# Create Review
# =========================================================

def create_review(user_id, data):
    if not isinstance(data, dict):
        return _error("A valid JSON object is required.", 400)

    product_id = data.get("product_id")
    rating = data.get("rating")
    title = data.get("title")
    comment = data.get("comment")
    order_item_id = data.get("order_item_id")

    # Validate product ID
    if isinstance(product_id, bool) or not isinstance(product_id, int):
        return _error("product_id must be an integer.", 400)

    if product_id <= 0:
        return _error("product_id must be greater than zero.", 400)

    # Validate rating
    if isinstance(rating, bool) or not isinstance(rating, int):
        return _error("rating must be an integer from 1 to 5.", 400)

    if rating < 1 or rating > 5:
        return _error("rating must be between 1 and 5.", 400)

    # Validate optional title
    if title is not None:
        if not isinstance(title, str):
            return _error("title must be text.", 400)

        title = title.strip() or None

        if title is not None and len(title) > 150:
            return _error("title must not exceed 150 characters.", 400)

    # Validate optional comment
    if comment is not None:
        if not isinstance(comment, str):
            return _error("comment must be text.", 400)

        comment = comment.strip() or None

    # Require an order item to verify the purchase.
    if isinstance(order_item_id, bool) or not isinstance(order_item_id, int):
        return _error(
            "order_item_id is required and must be an integer.",
            400,
        )

    if order_item_id <= 0:
        return _error("order_item_id must be greater than zero.", 400)

    try:
        product = db.session.get(Product, product_id)

        if product is None or not product.is_active:
            return _error("Active product not found.", 404)

        # Check that this order item belongs to the customer,
        # matches the product, and belongs to a delivered order.
        purchase = db.session.execute(
            select(OrderItem, Order)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                OrderItem.id == order_item_id,
                OrderItem.product_id == product_id,
                Order.user_id == user_id,
                func.lower(Order.order_status) == "delivered",
            )
        ).first()

        if purchase is None:
            return _error(
                "A delivered purchase of this product is required to review it.",
                403,
            )

        existing_review = db.session.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.product_id == product_id,
            )
        ).scalar_one_or_none()

        if existing_review is not None:
            return _error(
                "You have already reviewed this product.",
                409,
            )

        review = Review(
            user_id=user_id,
            product_id=product_id,
            order_item_id=order_item_id,
            rating=rating,
            title=title,
            comment=comment,
            is_verified_purchase=True,
            is_approved=False,
        )

        db.session.add(review)
        db.session.commit()

        return {
            "success": True,
            "message": "Review submitted successfully and is awaiting approval.",
            "data": review.to_dict(),
        }, 201

    except IntegrityError:
        db.session.rollback()
        return _error(
            "A review for this product already exists.",
            409,
        )

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Unable to submit review.", 500)


# =========================================================
# Get Approved Reviews for a Product
# =========================================================

def get_product_reviews(product_id):
    if product_id <= 0:
        return _error("Invalid product ID.", 400)

    try:
        product = db.session.get(Product, product_id)

        if product is None:
            return _error("Product not found.", 404)

        reviews = db.session.execute(
            select(Review)
            .where(
                Review.product_id == product_id,
                Review.is_approved.is_(True),
            )
            .order_by(Review.created_at.desc(), Review.id.desc())
        ).scalars().all()

        return {
            "success": True,
            "message": "Product reviews fetched successfully.",
            "count": len(reviews),
            "data": [review.to_dict() for review in reviews],
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Unable to fetch product reviews.", 500)


# =========================================================
# Get Logged-in User's Reviews
# =========================================================

def get_my_reviews(user_id):
    try:
        reviews = db.session.execute(
            select(Review)
            .where(Review.user_id == user_id)
            .order_by(Review.created_at.desc(), Review.id.desc())
        ).scalars().all()

        return {
            "success": True,
            "message": "Your reviews fetched successfully.",
            "count": len(reviews),
            "data": [review.to_dict() for review in reviews],
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Unable to fetch your reviews.", 500)


# =========================================================
# Update Own Review
# =========================================================

def update_review(user_id, review_id, data):
    if not isinstance(data, dict) or not data:
        return _error("A non-empty JSON object is required.", 400)

    allowed_fields = {"rating", "title", "comment"}
    unknown_fields = set(data.keys()) - allowed_fields

    if unknown_fields:
        return {
            "success": False,
            "message": "Unsupported fields supplied.",
            "errors": sorted(unknown_fields),
        }, 400

    try:
        review = _get_review(review_id, user_id)

        if review is None:
            return _error("Review not found.", 404)

        if "rating" in data:
            rating = data["rating"]

            if isinstance(rating, bool) or not isinstance(rating, int):
                return _error("rating must be an integer from 1 to 5.", 400)

            if rating < 1 or rating > 5:
                return _error("rating must be between 1 and 5.", 400)

            review.rating = rating

        if "title" in data:
            title = data["title"]

            if title is not None and not isinstance(title, str):
                return _error("title must be text or null.", 400)

            if isinstance(title, str):
                title = title.strip() or None

                if title is not None and len(title) > 150:
                    return _error(
                        "title must not exceed 150 characters.",
                        400,
                    )

            review.title = title

        if "comment" in data:
            comment = data["comment"]

            if comment is not None and not isinstance(comment, str):
                return _error("comment must be text or null.", 400)

            review.comment = (
                comment.strip() or None
                if isinstance(comment, str)
                else None
            )

        # Any edited review must be moderated again.
        review.is_approved = False

        db.session.commit()

        return {
            "success": True,
            "message": "Review updated and sent for approval.",
            "data": review.to_dict(),
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Unable to update review.", 500)


# =========================================================
# Delete Own Review
# =========================================================

def delete_review(user_id, review_id):
    try:
        review = _get_review(review_id, user_id)

        if review is None:
            return _error("Review not found.", 404)

        db.session.delete(review)
        db.session.commit()

        return {
            "success": True,
            "message": "Review deleted successfully.",
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Unable to delete review.", 500)


# =========================================================
# Admin: Approve or Reject Review
# =========================================================

def moderate_review(review_id, is_approved):
    if not isinstance(is_approved, bool):
        return _error("is_approved must be true or false.", 400)

    try:
        review = db.session.get(Review, review_id)

        if review is None:
            return _error("Review not found.", 404)

        review.is_approved = is_approved

        db.session.commit()

        action = "approved" if is_approved else "rejected"

        return {
            "success": True,
            "message": f"Review {action} successfully.",
            "data": review.to_dict(),
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Unable to moderate review.", 500)


# =========================================================
# Product Rating Summary
# =========================================================

def get_product_rating_summary(product_id):
    if product_id <= 0:
        return _error("Invalid product ID.", 400)

    try:
        product = db.session.get(Product, product_id)

        if product is None:
            return _error("Product not found.", 404)

        result = db.session.execute(
            select(
                func.count(Review.id),
                func.avg(Review.rating),
            ).where(
                Review.product_id == product_id,
                Review.is_approved.is_(True),
            )
        ).one()

        rating_count = result[0] or 0
        average_rating = (
            round(float(result[1]), 2)
            if result[1] is not None
            else 0.0
        )

        distribution_rows = db.session.execute(
            select(
                Review.rating,
                func.count(Review.id),
            )
            .where(
                Review.product_id == product_id,
                Review.is_approved.is_(True),
            )
            .group_by(Review.rating)
        ).all()

        distribution = {str(rating): 0 for rating in range(1, 6)}

        for rating, count in distribution_rows:
            distribution[str(rating)] = count

        return {
            "success": True,
            "message": "Product rating summary fetched successfully.",
            "data": {
                "product_id": product_id,
                "average_rating": average_rating,
                "rating_count": rating_count,
                "rating_distribution": distribution,
            },
        }, 200

    except SQLAlchemyError:
        db.session.rollback()
        return _error("Unable to fetch rating summary.", 500)
 