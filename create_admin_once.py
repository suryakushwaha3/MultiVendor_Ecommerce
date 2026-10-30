from getpass import getpass

from sqlalchemy import select

from app import create_app
from app.extensions import db
from tables.user_table import User
from utils.security import hash_password


def main():
    app = create_app()

    with app.app_context():
        existing_admin = db.session.execute(
            select(User).where(User.role == "admin")
        ).scalars().first()

        if existing_admin:
            print("An admin account already exists.")
            print(f"Email: {existing_admin.email}")
            print("No changes were made.")
            return

        name = input("Admin name: ").strip()
        email = input("Admin email: ").strip().lower()
        phone = input("Admin phone number: ").strip()
        password = getpass("Admin password (minimum 8 characters): ")
        confirm_password = getpass("Confirm password: ")

        if not name or not email or not phone:
            print("Name, email and phone are required.")
            return

        if len(password) < 8 or len(password) > 128:
            print("Password must be between 8 and 128 characters.")
            return

        if password != confirm_password:
            print("Passwords do not match.")
            return

        existing_user = db.session.execute(
            select(User).where(
                (User.email == email) |
                (User.phone_number == phone)
            )
        ).scalars().first()

        if existing_user:
            print("This email or phone number already belongs to an account.")
            print("No changes were made.")
            return

        admin = User(
            name=name,
            email=email,
            phone_number=phone,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )

        try:
            db.session.add(admin)
            db.session.commit()
            print("\nAdmin account created successfully.")
            print(f"Email: {admin.email}")
            print(f"Role: {admin.role}")
            print("Keep your password private.")
        except Exception:
            db.session.rollback()
            raise


if __name__ == "__main__":
    main()
