from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password: str) -> str:
    """
    Convert a plain-text password into a secure password hash.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password cannot be empty.")

    return generate_password_hash(password, method="scrypt")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plain-text password against its stored hash.
    """
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False

    if not password or not password_hash:
        return False

    try:
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False