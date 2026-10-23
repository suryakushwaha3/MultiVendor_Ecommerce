import re


def validate_required(value, field_name="Field"):
    if value is None or not str(value).strip():
        return False, f"{field_name} is required."
    return True, None


def validate_email(email):
    if not isinstance(email, str):
        return False, "A valid email address is required."

    email = email.strip()

    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if not re.fullmatch(pattern, email):
        return False, "A valid email address is required."

    return True, None


def validate_positive_number(value, field_name="Value"):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False, f"{field_name} must be a valid number."

    if number <= 0:
        return False, f"{field_name} must be greater than zero."

    return True, None


def validate_phone(phone):
    if not isinstance(phone, str):
        return False, "A valid phone number is required."

    phone = phone.strip()

    if not re.fullmatch(r"\+?[0-9]{10,15}", phone):
        return False, "Phone number must contain 10 to 15 digits."

    return True, None
