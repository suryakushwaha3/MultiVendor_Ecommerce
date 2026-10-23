from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from middleware.auth_middleware import token_required
from middleware.role_middleware import role_required

from operations.review_operation import (
    create_review,
    get_product_reviews,
    get_my_reviews,
    update_review,
    delete_review,
    moderate_review,
    get_product_rating_summary,
)


review_bp = Blueprint(
    "review_bp",
    __name__,
    url_prefix="/api/v1/reviews",
)


def _get_json_body():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None

    return data


# =========================================================
# Create Review
# POST /api/v1/reviews
# =========================================================

@review_bp.route("", methods=["POST"])
@token_required
@role_required("customer")
def create_review_route():
    user_id = int(get_jwt_identity())
    data = _get_json_body()

    if data is None:
        return jsonify({
            "success": False,
            "message": "A valid JSON object is required.",
        }), 400

    result, status_code = create_review(
        user_id=user_id,
        data=data,
    )

    return jsonify(result), status_code


# =========================================================
# Get Approved Product Reviews
# GET /api/v1/reviews/product/<product_id>
# =========================================================

@review_bp.route("/product/<int:product_id>", methods=["GET"])
def get_product_reviews_route(product_id):
    result, status_code = get_product_reviews(product_id)
    return jsonify(result), status_code


# =========================================================
# Get Product Rating Summary
# GET /api/v1/reviews/product/<product_id>/summary
# =========================================================

@review_bp.route(
    "/product/<int:product_id>/summary",
    methods=["GET"],
)
def get_product_rating_summary_route(product_id):
    result, status_code = get_product_rating_summary(product_id)
    return jsonify(result), status_code


# =========================================================
# Get Logged-in Customer's Reviews
# GET /api/v1/reviews/my
# =========================================================

@review_bp.route("/my", methods=["GET"])
@token_required
@role_required("customer")
def get_my_reviews_route():
    user_id = int(get_jwt_identity())

    result, status_code = get_my_reviews(user_id)
    return jsonify(result), status_code


# =========================================================
# Update Own Review
# PUT /api/v1/reviews/<review_id>
# =========================================================

@review_bp.route("/<int:review_id>", methods=["PUT"])
@token_required
@role_required("customer")
def update_review_route(review_id):
    user_id = int(get_jwt_identity())
    data = _get_json_body()

    if data is None:
        return jsonify({
            "success": False,
            "message": "A valid JSON object is required.",
        }), 400

    result, status_code = update_review(
        user_id=user_id,
        review_id=review_id,
        data=data,
    )

    return jsonify(result), status_code


# =========================================================
# Delete Own Review
# DELETE /api/v1/reviews/<review_id>
# =========================================================

@review_bp.route("/<int:review_id>", methods=["DELETE"])
@token_required
@role_required("customer")
def delete_review_route(review_id):
    user_id = int(get_jwt_identity())

    result, status_code = delete_review(
        user_id=user_id,
        review_id=review_id,
    )

    return jsonify(result), status_code


# =========================================================
# Admin: Approve or Reject Review
# PATCH /api/v1/reviews/<review_id>/moderate
# =========================================================

@review_bp.route(
    "/<int:review_id>/moderate",
    methods=["PATCH"],
)
@token_required
@role_required("admin")
def moderate_review_route(review_id):
    data = _get_json_body()

    if data is None:
        return jsonify({
            "success": False,
            "message": "A valid JSON object is required.",
        }), 400

    if set(data.keys()) != {"is_approved"}:
        return jsonify({
            "success": False,
            "message": "Only the is_approved field is accepted.",
        }), 400

    is_approved = data["is_approved"]

    if not isinstance(is_approved, bool):
        return jsonify({
            "success": False,
            "message": "is_approved must be a boolean.",
        }), 400

    result, status_code = moderate_review(
        review_id=review_id,
        is_approved=is_approved,
    )

    return jsonify(result), status_code
 