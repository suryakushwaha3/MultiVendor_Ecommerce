from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from tables.address_table import Address


# =========================================================
# Constants
# =========================================================

ALLOWED_ADDRESS_TYPES = {"home", "work", "other"}

REQUIRED_FIELDS = (
    "full_name",
    "phone_number",
    "address_line1",
    "city",
    "state",
    "pincode",
)


# =========================================================
# Helpers
# =========================================================

def _error(message, status_code):
    return {
        "success": False,
        "message": message,
    }, status_code


def _validate_address_data(data, partial=False):
    """Validate address fields and return cleaned data."""

    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    allowed_fields = {
        "full_name",
        "phone_number",
        "address_line1",
        "address_line2",
        "landmark",
        "city",
        "state",
        "pincode",
        "country",
        "address_type",
        "is_default",
    }

    unknown_fields = set(data.keys()) - allowed_fields

    if unknown_fields:
        return None, (
            "Unknown fields: "
            + ", ".join(sorted(unknown_fields))
        )

    if not partial:
        missing_fields = [
            field
            for field in REQUIRED_FIELDS
            if field not in data
        ]

        if missing_fields:
            return None, (
                "Missing required fields: "
                + ", ".join(missing_fields)
            )

    cleaned = {}

    string_limits = {
        "full_name": 100,
        "phone_number": 20,
        "address_line1": 255,
        "address_line2": 255,
        "landmark": 150,
        "city": 100,
        "state": 100,
        "pincode": 10,
        "country": 100,
        "address_type": 20,
    }

    for field, max_length in string_limits.items():
        if field not in data:
            continue

        value = data[field]

        if value is None and field in {
            "address_line2",
            "landmark",
        }:
            cleaned[field] = None
            continue

        if not isinstance(value, str):
            return None, f"{field} must be a string."

        value = value.strip()

        if field in REQUIRED_FIELDS and not value:
            return None, f"{field} is required."

        if field == "address_type":
            value = value.lower()

            if value not in ALLOWED_ADDRESS_TYPES:
                return None, (
                    "address_type must be home, work, or other."
                )

        if len(value) > max_length:
            return None, (
                f"{field} must not exceed {max_length} characters."
            )

        cleaned[field] = value or None

    if "is_default" in data:
        if not isinstance(data["is_default"], bool):
            return None, "is_default must be a boolean."

        cleaned["is_default"] = data["is_default"]

    if "country" not in cleaned and not partial:
        cleaned["country"] = "India"

    if "address_type" not in cleaned and not partial:
        cleaned["address_type"] = "home"

    return cleaned, None


def _set_default_address(user_id, address):
    """Make one address default for the customer."""

    addresses = db.session.execute(
        select(Address).where(Address.user_id == user_id)
    ).scalars().all()

    for item in addresses:
        item.is_default = item.id == address.id

    address.is_default = True


# =========================================================
# Create Address
# =========================================================

def create_address(user_id, data):
    """Create a delivery address for the logged-in customer."""

    cleaned, error = _validate_address_data(data)

    if error:
        return _error(error, 400)

    try:
        address = Address(
            user_id=user_id,
            **{
                key: value
                for key, value in cleaned.items()
                if key != "is_default"
            },
        )

        db.session.add(address)
        db.session.flush()

        # Make this address default if explicitly requested,
        # or if the customer has no existing address.
        existing_address = db.session.execute(
            select(Address.id)
            .where(
                Address.user_id == user_id,
                Address.id != address.id,
            )
            .limit(1)
        ).first()

        requested_default = cleaned.get("is_default", False)

        if requested_default or existing_address is None:
            _set_default_address(user_id, address)
        else:
            address.is_default = False

        db.session.flush()
        result = address.to_dict()

        db.session.commit()

        return {
            "success": True,
            "message": "Address created successfully.",
            "data": result,
        }, 201

    except SQLAlchemyError:
        db.session.rollback()

        return _error("Unable to create address.", 500)


# =========================================================
# Get Customer Addresses
# =========================================================

def get_customer_addresses(user_id):
    """Return all addresses belonging to the customer."""

    try:
        addresses = db.session.execute(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(
                Address.is_default.desc(),
                Address.created_at.desc(),
                Address.id.desc(),
            )
        ).scalars().all()

        return {
            "success": True,
            "message": "Addresses fetched successfully.",
            "data": [
                address.to_dict()
                for address in addresses
            ],
            "count": len(addresses),
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error("Unable to fetch addresses.", 500)


# =========================================================
# Get Address By ID
# =========================================================

def get_address_by_id(user_id, address_id):
    """Fetch one address belonging to the customer."""

    if address_id <= 0:
        return _error("Invalid address ID.", 400)

    try:
        address = db.session.execute(
            select(Address).where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
        ).scalar_one_or_none()

        if address is None:
            return _error("Address not found.", 404)

        return {
            "success": True,
            "message": "Address fetched successfully.",
            "data": address.to_dict(),
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error("Unable to fetch address.", 500)


# =========================================================
# Update Address
# =========================================================

def update_address(user_id, address_id, data):
    """Update an address belonging to the customer."""

    if address_id <= 0:
        return _error("Invalid address ID.", 400)

    cleaned, error = _validate_address_data(
        data,
        partial=True,
    )

    if error:
        return _error(error, 400)

    if not cleaned:
        return _error("No fields provided to update.", 400)

    try:
        address = db.session.execute(
            select(Address)
            .where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if address is None:
            db.session.rollback()
            return _error("Address not found.", 404)

        requested_default = cleaned.pop("is_default", None)

        for field, value in cleaned.items():
            setattr(address, field, value)

        if requested_default is True:
            _set_default_address(user_id, address)

        elif requested_default is False and address.is_default:
            # Do not leave the customer without a default address
            # when other addresses exist.
            other_address = db.session.execute(
                select(Address)
                .where(
                    Address.user_id == user_id,
                    Address.id != address.id,
                )
                .order_by(Address.created_at.asc(), Address.id.asc())
                .limit(1)
            ).scalar_one_or_none()

            address.is_default = False

            if other_address is not None:
                other_address.is_default = True

        db.session.flush()
        result = address.to_dict()

        db.session.commit()

        return {
            "success": True,
            "message": "Address updated successfully.",
            "data": result,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error("Unable to update address.", 500)


# =========================================================
# Set Default Address
# =========================================================

def set_default_address(user_id, address_id):
    """Set an address as the customer's default address."""

    if address_id <= 0:
        return _error("Invalid address ID.", 400)

    try:
        address = db.session.execute(
            select(Address)
            .where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if address is None:
            db.session.rollback()
            return _error("Address not found.", 404)

        _set_default_address(user_id, address)

        db.session.flush()
        result = address.to_dict()

        db.session.commit()

        return {
            "success": True,
            "message": "Default address updated successfully.",
            "data": result,
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error("Unable to set default address.", 500)


# =========================================================
# Delete Address
# =========================================================

def delete_address(user_id, address_id):
    """Delete an address belonging to the customer."""

    if address_id <= 0:
        return _error("Invalid address ID.", 400)

    try:
        address = db.session.execute(
            select(Address)
            .where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if address is None:
            db.session.rollback()
            return _error("Address not found.", 404)

        was_default = address.is_default

        # Orders may reference this address. Preserve it if the
        # database foreign key prevents deletion.
        db.session.delete(address)
        db.session.flush()

        if was_default:
            replacement = db.session.execute(
                select(Address)
                .where(Address.user_id == user_id)
                .order_by(Address.created_at.asc(), Address.id.asc())
                .limit(1)
            ).scalar_one_or_none()

            if replacement is not None:
                replacement.is_default = True

        db.session.commit()

        return {
            "success": True,
            "message": "Address deleted successfully.",
            "data": {
                "address_id": address_id,
            },
        }, 200

    except SQLAlchemyError:
        db.session.rollback()

        return _error(
            "Unable to delete address. It may be linked to an existing order.",
            409,
        )
 