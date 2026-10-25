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

    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60

    # Database Configuration
    _database_url = os.getenv("DATABASE_URL")

    if _database_url:
        # Normalize legacy PostgreSQL URL schemes.
        if _database_url.startswith("postgres://"):
            _database_url = "postgresql://" + _database_url[len("postgres://"):]

        # Explicitly use psycopg 3 for PostgreSQL.
        if _database_url.startswith("postgresql://"):
            _database_url = "postgresql+psycopg://" + _database_url[len("postgresql://"):]

        SQLALCHEMY_DATABASE_URI = _database_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///multivendor.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload Configuration
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # API Configuration
    API_VERSION = "v1"

    JSON_SORT_KEYS = False
