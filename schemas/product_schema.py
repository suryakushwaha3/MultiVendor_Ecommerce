from decimal import Decimal, InvalidOperation


class ProductCreateSchema:

    REQUIRED_FIELDS = [
        "store_id",
        "category_id",
        "product_name",
        "slug",
        "description",
        "sku",
        "price",
        "stock_quantity",
    ]

    OPTIONAL_FIELDS = [
        "subcategory_id",
        "brand",
        "discount_price",
        "weight",
        "is_featured",
    ]

    @staticmethod
    def validate(data):
        errors = {}

        # Required fields
        for field in ProductCreateSchema.REQUIRED_FIELDS:
            value = data.get(field)

            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                errors[field] = f"{field} is required."

        # Stop if required fields are missing
        if errors:
            return False, errors

        # Integer fields
        for field in ("store_id", "category_id", "stock_quantity"):
            try:
                value = data[field]

                if isinstance(value, bool):
                    raise ValueError

                if isinstance(value, str) and not value.strip():
                    raise ValueError

                number = int(value)

                if str(number) != str(value).strip():
                    raise ValueError

                if field in ("store_id", "category_id") and number <= 0:
                    errors[field] = f"{field} must be greater than zero."

                elif field == "stock_quantity" and number < 0:
                    errors[field] = "Stock quantity cannot be negative."

            except (ValueError, TypeError):
                errors[field] = f"{field} must be a valid integer."

        # Optional integer field
        subcategory_id = data.get("subcategory_id")

        if subcategory_id not in (None, ""):
            try:
                if isinstance(subcategory_id, bool):
                    raise ValueError

                number = int(subcategory_id)

                if number <= 0 or str(number) != str(subcategory_id).strip():
                    raise ValueError

            except (ValueError, TypeError):
                errors["subcategory_id"] = (
                    "Subcategory ID must be a positive integer."
                )

        # Text fields
        for field in ("product_name", "slug", "description", "sku"):
            value = data.get(field)

            if isinstance(value, str):
                data[field] = value.strip()

                if not data[field]:
                    errors[field] = f"{field} cannot be empty."

        # Price validation
        for field in ("price", "discount_price", "weight"):
            value = data.get(field)

            if value in (None, ""):
                if field == "price":
                    errors[field] = "Price is required."
                else:
                    data[field] = None

                continue

            try:
                if isinstance(value, bool):
                    raise InvalidOperation

                number = Decimal(str(value))

                if not number.is_finite():
                    raise InvalidOperation

                if field == "price" and number <= 0:
                    errors[field] = "Price must be greater than zero."

                elif field == "discount_price" and number < 0:
                    errors[field] = "Discount price cannot be negative."

                elif field == "weight" and number <= 0:
                    errors[field] = "Weight must be greater than zero."

                elif field == "discount_price":
                    price_value = data.get("price")

                    try:
                        original_price = Decimal(str(price_value))

                        if original_price.is_finite() and number >= original_price:
                            errors[field] = (
                                "Discount price must be less than original price."
                            )

                    except (InvalidOperation, ValueError, TypeError):
                        pass

            except (InvalidOperation, ValueError, TypeError):
                errors[field] = f"{field} must be a valid number."

        # Optional brand
        brand = data.get("brand")

        if brand is not None and not isinstance(brand, str):
            errors["brand"] = "Brand must be text."
        elif isinstance(brand, str):
            data["brand"] = brand.strip() or None

        # Featured status
        is_featured = data.get("is_featured", False)

        if isinstance(is_featured, bool):
            data["is_featured"] = is_featured

        elif isinstance(is_featured, str):
            normalized = is_featured.strip().lower()

            if normalized in ("true", "1"):
                data["is_featured"] = True

            elif normalized in ("false", "0"):
                data["is_featured"] = False

            else:
                errors["is_featured"] = (
                    "is_featured must be true or false."
                )

        else:
            errors["is_featured"] = "is_featured must be true or false."

        return len(errors) == 0, errors


class ProductUpdateSchema:

    @staticmethod
    def validate(data):
        if not isinstance(data, dict) or not data:
            return False, {"body": "At least one field is required."}

        allowed_fields = {
            "category_id",
            "subcategory_id",
            "product_name",
            "slug",
            "description",
            "brand",
            "sku",
            "price",
            "discount_price",
            "stock_quantity",
            "weight",
            "is_featured",
        }

        errors = {}
        unknown_fields = set(data.keys()) - allowed_fields

        if unknown_fields:
            errors["fields"] = (
                "Unsupported fields: " + ", ".join(sorted(unknown_fields))
            )

        if errors:
            return False, errors

        # Validate supplied fields using the same rules as product creation.
        complete_data = {
            "store_id": "1",
            "category_id": data.get("category_id", "1"),
            "product_name": data.get("product_name", "Temporary Product"),
            "slug": data.get("slug", "temporary-product"),
            "description": data.get("description", "Temporary description"),
            "sku": data.get("sku", "TEMP-SKU"),
            "price": data.get("price", "1"),
            "stock_quantity": data.get("stock_quantity", "0"),
            "is_featured": data.get("is_featured", False),
        }

        for field in ProductCreateSchema.OPTIONAL_FIELDS:
            if field in data:
                complete_data[field] = data[field]

        valid, validation_errors = ProductCreateSchema.validate(complete_data)

        # Return only errors for fields the user actually supplied.
        relevant_errors = {
            field: message
            for field, message in validation_errors.items()
            if field in data
        }

        return valid and not relevant_errors, relevant_errors


class ProductStatusSchema:

    @staticmethod
    def validate(data):
        if not isinstance(data, dict):
            return False, {"body": "A JSON object is required."}

        if "is_active" not in data:
            return False, {"is_active": "is_active is required."}

        value = data["is_active"]

        if isinstance(value, bool):
            return True, {}

        if isinstance(value, str) and value.strip().lower() in (
            "true", "false", "1", "0"
        ):
            return True, {}

        return False, {
            "is_active": "is_active must be true or false."
        }