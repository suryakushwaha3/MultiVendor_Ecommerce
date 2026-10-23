from flask_jwt_extended import create_access_token

from app.extensions import db
from tables.user_table import User
from utils.security import hash_password


def create_test_user(
    name="Test Customer",
    email="customer@example.com",
    phone_number="9876543210",
    role="customer",
    is_active=True
):
    user = User(
        name=name,
        email=email,
        phone_number=phone_number,
        password_hash=hash_password("StrongTestPass123!"),
        role=role,
        is_active=is_active
    )

    db.session.add(user)
    db.session.commit()

    return user


def get_token(user_id):
    return create_access_token(identity=str(user_id))


def test_profile_requires_authentication(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_profile_with_valid_token(client):
    user = create_test_user()
    token = get_token(user.id)

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["user"]["id"] == user.id
    assert data["user"]["email"] == user.email
    assert "password_hash" not in data["user"]


def test_profile_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401


def test_profile_does_not_expose_another_users_data(client):
    user_one = create_test_user(
        name="Customer One",
        email="customer1@example.com",
        phone_number="9876543210"
    )

    user_two = create_test_user(
        name="Customer Two",
        email="customer2@example.com",
        phone_number="9876543211"
    )

    token = get_token(user_one.id)

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["user"]["id"] == user_one.id
    assert data["user"]["email"] == user_one.email
    assert data["user"]["id"] != user_two.id
    assert data["user"]["email"] != user_two.email


def test_admin_endpoint_rejects_customer(client):
    user = create_test_user()
    token = get_token(user.id)

    response = client.get(
        "/api/v1/users/admin-test",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_admin_endpoint_accepts_admin(client):
    admin = create_test_user(
        name="Test Admin",
        email="admin@example.com",
        phone_number="9876543212",
        role="admin"
    )

    token = get_token(admin.id)

    response = client.get(
        "/api/v1/users/admin-test",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["message"] == "Admin access granted."


def test_admin_endpoint_rejects_missing_token(client):
    response = client.get("/api/v1/users/admin-test")

    assert response.status_code == 401

def test_inactive_user_cannot_access_profile_with_old_token(client):
    # Create an active user
    user = create_test_user(
        name="Test Customer",
        email="deactivate@example.com",
        phone_number="9876543215",
        is_active=True
    )

    # Generate a token while the user is active
    token = get_token(user.id)

    # Deactivate the user after token generation
    user.is_active = False
    db.session.commit()

    # Attempt to access the profile with the old token
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    # The inactive account should not be allowed access
    assert response.status_code == 403


from flask_jwt_extended import create_access_token

from app.extensions import db
from tables.vendor_table import Vendor
from utils.security import hash_password


def create_test_vendor(
    email="vendor@example.com",
    phone_number="9876543218",
    is_active=True,
    is_approved=True
):
    vendor = Vendor(
        name="Test Vendor",
        email=email,
        phone_number=phone_number,
        password_hash=hash_password("StrongVendorPass123!"),
        business_name="Test Business",
        business_address="Test Address",
        is_active=is_active,
        is_approved=is_approved
    )

    db.session.add(vendor)
    db.session.commit()

    return vendor


def get_vendor_token(vendor_id):
    return create_access_token(
        identity=f"vendor:{vendor_id}"
    )


def test_vendor_dashboard_requires_token(client):
    response = client.get("/api/v1/vendor/dashboard")

    assert response.status_code == 401


def test_vendor_dashboard_rejects_customer_token(client):
    customer = create_test_user(
        name="Regular Customer",
        email="regular-customer@example.com",
        phone_number="9876543220"
    )

    customer_token = get_token(customer.id)

    response = client.get(
        "/api/v1/vendor/dashboard",
        headers={
            "Authorization": f"Bearer {customer_token}"
        }
    )

    assert response.status_code == 403


def test_approved_active_vendor_can_access_dashboard(client):
    vendor = create_test_vendor()
    token = get_vendor_token(vendor.id)

    response = client.get(
        "/api/v1/vendor/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_inactive_vendor_old_token_is_rejected(client):
    vendor = create_test_vendor(
        email="inactive-vendor@example.com",
        phone_number="9876543221"
    )

    token = get_vendor_token(vendor.id)

    # Deactivate the vendor after token generation.
    vendor.is_active = False
    db.session.commit()

    response = client.get(
        "/api/v1/vendor/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_unapproved_vendor_token_is_rejected(client):
    vendor = create_test_vendor(
        email="pending-vendor@example.com",
        phone_number="9876543222",
        is_approved=False
    )

    token = get_vendor_token(vendor.id)

    response = client.get(
        "/api/v1/vendor/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
 
    
 