import pytest

from app import create_app
from app.extensions import db


class TestConfig:
    TESTING = True

    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-only-jwt-secret-key-at-least-32-bytes"

    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_ACCESS_TOKEN_EXPIRES = False


@pytest.fixture
def app():
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()