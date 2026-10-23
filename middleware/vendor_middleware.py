from functools import wraps

from flask import jsonify, g
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity
)

from app.extensions import db
from tables.vendor_table import Vendor


def vendor_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        # Verify JWT token
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()

        except Exception:
            return jsonify({
                "success": False,
                "message": (
                    "Authentication required. "
                    "Please provide a valid token."
                )
            }), 401

        # Verify vendor identity
        if (
            not isinstance(identity, str)
            or not identity.startswith("vendor:")
        ):
            return jsonify({
                "success": False,
                "message": "Vendor authentication required."
            }), 403

        # Extract vendor ID
        try:
            vendor_id = int(identity.split(":", 1)[1])

            if vendor_id <= 0:
                raise ValueError("Invalid vendor ID")

        except (ValueError, IndexError):
            return jsonify({
                "success": False,
                "message": "Invalid vendor identity."
            }), 401

        # Get vendor from database
        vendor = db.session.get(Vendor, vendor_id)

        if vendor is None:
            return jsonify({
                "success": False,
                "message": "Vendor account not found."
            }), 404

        # Check vendor status
        if not vendor.is_active:
            return jsonify({
                "success": False,
                "message": "Your vendor account is inactive."
            }), 403

        if not vendor.is_approved:
            return jsonify({
                "success": False,
                "message": "Your vendor account is awaiting approval."
            }), 403

        # Make vendor ID available to routes
        g.vendor_id = vendor.id
        request_vendor_id = vendor.id

        from flask import request
        request.vendor_id = request_vendor_id

        return fn(*args, **kwargs)

    return wrapper