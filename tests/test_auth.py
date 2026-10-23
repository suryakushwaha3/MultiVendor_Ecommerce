import pytest

from app.extensions import db
from tables.user_table import User
from utils.security import hash_password


def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["status"] == "healthy"


def test_signup_rejects_missing_json(client):
    response = client.post("/api/v1/auth/signup")

    assert response.status_code == 400

    data = response.get_json()
    assert data["success"] is False
    assert "JSON" in data["message"]


def test_login_rejects_missing_json(client):
    response = client.post("/api/v1/auth/login")

    assert response.status_code == 400

    data = response.get_json()
    assert data["success"] is False
    assert "JSON" in data["message"]


def test_signup_success(client):
    payload = {
        "name": "Test Customer",
        "email": "customer@example.com",
        "phone_number": "9876543210",
        "password": "StrongTestPass123!"
    }

    response = client.post(
        "/api/v1/auth/signup",
        json=payload
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["success"] is True
    assert data["user"]["email"] == "customer@example.com"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_signup_duplicate_email(client):
    payload = {
        "name": "Test Customer",
        "email": "customer@example.com",
        "phone_number": "9876543210",
        "password": "StrongTestPass123!"
    }

    first_response = client.post(
        "/api/v1/auth/signup",
        json=payload
    )

    assert first_response.status_code == 201

    duplicate_payload = {
        **payload,
        "phone_number": "9876543211"
    }

    response = client.post(
        "/api/v1/auth/signup",
        json=duplicate_payload
    )

    assert response.status_code == 409

    data = response.get_json()
    assert data["success"] is False
    assert "Email" in data["message"]


def test_signup_duplicate_phone(client):
    payload = {
        "name": "First Customer",
        "email": "first@example.com",
        "phone_number": "9876543210",
        "password": "StrongTestPass123!"
    }

    first_response = client.post(
        "/api/v1/auth/signup",
        json=payload
    )

    assert first_response.status_code == 201

    duplicate_payload = {
        "name": "Second Customer",
        "email": "second@example.com",
        "phone_number": "9876543210",
        "password": "StrongTestPass123!"
    }

    response = client.post(
        "/api/v1/auth/signup",
        json=duplicate_payload
    )

    assert response.status_code == 409

    data = response.get_json()
    assert data["success"] is False
    assert "Phone number" in data["message"]


def test_signup_rejects_invalid_email(client):
    payload = {
        "name": "Test Customer",
        "email": "not-an-email",
        "phone_number": "9876543210",
        "password": "StrongTestPass123!"
    }

    response = client.post(
        "/api/v1/auth/signup",
        json=payload
    )

    assert response.status_code == 400

    data = response.get_json()
    assert data["success"] is False
    assert data["message"] == "Validation failed."


def test_signup_rejects_short_password(client):
    payload = {
        "name": "Test Customer",
        "email": "customer@example.com",
        "phone_number": "9876543210",
        "password": "123"
    }

    response = client.post(
        "/api/v1/auth/signup",
        json=payload
    )

    assert response.status_code == 400

    data = response.get_json()
    assert data["success"] is False
    assert data["message"] == "Validation failed."


def test_login_success(client):
    user = User(
        name="Test Customer",
        email="customer@example.com",
        phone_number="9876543210",
        password_hash=hash_password("StrongTestPass123!")
    )

    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "customer@example.com",
            "password": "StrongTestPass123!"
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["token_type"] == "Bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0
    assert data["user"]["email"] == "customer@example.com"


def test_login_rejects_wrong_password(client):
    user = User(
        name="Test Customer",
        email="customer@example.com",
        phone_number="9876543210",
        password_hash=hash_password("StrongTestPass123!")
    )

    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "customer@example.com",
            "password": "WrongPassword123!"
        }
    )

    assert response.status_code == 401

    data = response.get_json()

    assert data["success"] is False
    assert data["message"] == "Invalid email or password."


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "StrongTestPass123!"
        }
    )

    assert response.status_code == 401

    data = response.get_json()

    assert data["success"] is False
    assert data["message"] == "Invalid email or password."


def test_login_rejects_inactive_user(client):
    user = User(
        name="Inactive Customer",
        email="inactive@example.com",
        phone_number="9876543210",
        password_hash=hash_password("StrongTestPass123!"),
        is_active=False
    )

    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "StrongTestPass123!"
        }
    )

    # Current login_user implementation does not check is_active.
    # This test documents the expected security behavior.
    assert response.status_code == 403