import os


class Config:

    # Application Security
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-key-change-before-deployment"
    )

    # JWT Authentication
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "development-jwt-secret-change-before-deployment"
    )

    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60  # 1 hour

    # Database Configuration
    # Development: SQLite
    # Deployment: MySQL through DATABASE_URL

    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL")
        or "sqlite:///multivendor.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload Configuration
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB per request

    # API Configuration
    API_VERSION = "v1"

    JSON_SORT_KEYS = False