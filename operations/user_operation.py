from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from tables.user_table import User
from utils.security import hash_password


def register_user(data):
    """
    Register a new user after checking email and phone uniqueness.
    """

    name = data["name"].strip()
    email = data["email"].strip().lower()
    phone_number = data["phone_number"].strip()
    password = data["password"]

    try:
        # Check whether email or phone number already exists.
        existing_user = db.session.execute(
            select(User).where(
                or_(
                    User.email == email,
                    User.phone_number == phone_number
                )
            )
        ).scalar_one_or_none()

        if existing_user:
            if existing_user.email == email:
                return {
                    "success": False,
                    "message": "Email is already registered."
                }, 409

            return {
                "success": False,
                "message": "Phone number is already registered."
            }, 409

        # Create a new user.
        user = User(
            name=name,
            email=email,
            phone_number=phone_number,
            password_hash=hash_password(password)
        )

        db.session.add(user)
        db.session.commit()

        return {
            "success": True,
            "message": "User registered successfully.",
            "user": user.to_dict()
        }, 201

    except IntegrityError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Email or phone number is already registered."
        }, 409

    except SQLAlchemyError:
        db.session.rollback()

        return {
            "success": False,
            "message": "Unable to register user at this time."
        }, 500
