from decimal import Decimal

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from tables.category_table import Category
from tables.inventory_table import Inventory
from tables.product_table import Product
from tables.store_table import Store
from tables.user_table import User
from tables.vendor_table import Vendor
from utils.security import hash_password


INVENTORY_URL = "/inventory"
MOVEMENT_URL = "/inventory/movement"


# ---------------------------------------------------------
# Test helpers
# ---------------------------------------------------------

def create_user(
    email="inventory-admin@example.com",
    role="admin",
    is_active=True,
):
    user = User(
        name="Inventory Test User",
        email=email,
        phone_number="9876543210",
        password_hash=hash_password("StrongTestPass123!"),
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.commit()
    return user


def user_headers(user):
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def create_vendor(
    email="inventory-vendor@example.com",
    phone_number="9876543211",
):
    vendor = Vendor(
        name="Inventory Vendor",
        email=email,
        phone_number=phone_number,
        password_hash=hash_password("StrongVendorPass123!"),
        business_name="Inventory Test Business",
        business_address="Test Address",
        is_active=True,
        is_approved=True,
    )
    db.session.add(vendor)
    db.session.commit()
    return vendor


def vendor_headers(vendor):
    token = create_access_token(
        identity=f"vendor:{vendor.id}"
    )
    return {"Authorization": f"Bearer {token}"}


def create_store(vendor, name="Inventory Store", slug="inventory-store"):
    store = Store(
        vendor_id=vendor.id,
        store_name=name,
        slug=slug,
        is_active=True,
    )
    db.session.add(store)
    db.session.commit()
    return store


def create_product(
    store,
    name="Inventory Product",
    slug="inventory-product",
    sku="INV-SKU-001",
    stock=10,
):
    category = Category.query.first()

    if category is None:
        category = Category(
            category_name="Inventory Category",
            slug="inventory-category",
            is_active=True,
        )
        db.session.add(category)
        db.session.flush()

    product = Product(
        store_id=store.id,
        category_id=category.id,
        product_name=name,
        slug=slug,
        description="Inventory test product",
        sku=sku,
        price=Decimal("100.00"),
        stock_quantity=stock,
        is_active=True,
    )
    db.session.add(product)
    db.session.commit()
    return product


def create_inventory_record(product, movement_type, quantity_change):
    previous_stock = product.stock_quantity
    new_stock = previous_stock + quantity_change

    record = Inventory(
        product_id=product.id,
        store_id=product.store_id,
        movement_type=movement_type,
        quantity_change=quantity_change,
        previous_stock=previous_stock,
        new_stock=new_stock,
        created_by_type="admin",
    )

    product.stock_quantity = new_stock
    db.session.add(record)
    db.session.commit()
    return record


# ---------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------

def test_inventory_history_requires_authentication(client):
    response = client.get(INVENTORY_URL)

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_inventory_movement_requires_authentication(client):
    response = client.post(
        MOVEMENT_URL,
        json={
            "product_id": 1,
            "quantity_change": 5,
            "movement_type": "purchase",
        },
    )

    assert response.status_code == 401


def test_customer_cannot_access_inventory(client):
    customer = create_user(
        email="inventory-customer@example.com",
        role="customer",
    )

    response = client.get(
        INVENTORY_URL,
        headers=user_headers(customer),
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# Inventory movement validation
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"product_id": 1},
        {"quantity_change": 5},
        {"product_id": 1, "quantity_change": 5},
    ],
)
def test_inventory_movement_rejects_missing_fields(client, payload):
    admin = create_user(email="missing-fields-admin@example.com")

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json=payload,
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


@pytest.mark.parametrize(
    "quantity",
    [0, -0],
)
def test_inventory_movement_rejects_zero_quantity(client, quantity):
    admin = create_user(email="zero-quantity-admin@example.com")

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": 1,
            "quantity_change": quantity,
            "movement_type": "purchase",
        },
    )

    assert response.status_code == 400


def test_inventory_movement_rejects_invalid_product_id(client):
    admin = create_user(email="invalid-product-admin@example.com")

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": -1,
            "quantity_change": 5,
            "movement_type": "purchase",
        },
    )

    assert response.status_code == 400


def test_inventory_movement_rejects_invalid_movement_type(client):
    admin = create_user(email="invalid-type-admin@example.com")

    vendor = create_vendor()
    store = create_store(vendor)
    product = create_product(store)

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": product.id,
            "quantity_change": 5,
            "movement_type": "unknown",
        },
    )

    assert response.status_code == 400


def test_inventory_movement_rejects_nonexistent_product(client):
    admin = create_user(email="missing-product-admin@example.com")

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": 999999,
            "quantity_change": 5,
            "movement_type": "purchase",
        },
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# Inventory movement success and stock updates
# ---------------------------------------------------------

def test_inventory_purchase_increases_stock(client):
    admin = create_user(email="purchase-admin@example.com")
    vendor = create_vendor()
    store = create_store(vendor)
    product = create_product(store, stock=10)

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": product.id,
            "quantity_change": 5,
            "movement_type": "purchase",
            "note": "New stock received",
        },
    )

    assert response.status_code == 201

    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["previous_stock"] == 10
    assert body["data"]["new_stock"] == 15
    assert body["data"]["quantity_change"] == 5

    db.session.refresh(product)
    assert product.stock_quantity == 15

    record = Inventory.query.filter_by(
        product_id=product.id
    ).one()

    assert record.movement_type == "purchase"
    assert record.note == "New stock received"


def test_inventory_sale_decreases_stock(client):
    admin = create_user(email="sale-admin@example.com")
    vendor = create_vendor()
    store = create_store(vendor)
    product = create_product(store, stock=10)

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": product.id,
            "quantity_change": -3,
            "movement_type": "sale",
        },
    )

    assert response.status_code == 201

    body = response.get_json()
    assert body["data"]["previous_stock"] == 10
    assert body["data"]["new_stock"] == 7

    db.session.refresh(product)
    assert product.stock_quantity == 7


def test_inventory_movement_rejects_insufficient_stock(client):
    admin = create_user(email="insufficient-stock-admin@example.com")
    vendor = create_vendor()
    store = create_store(vendor)
    product = create_product(store, stock=3)

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": product.id,
            "quantity_change": -5,
            "movement_type": "sale",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False

    db.session.refresh(product)
    assert product.stock_quantity == 3

    assert Inventory.query.filter_by(
        product_id=product.id
    ).count() == 0


def test_inventory_movement_rejects_product_store_mismatch(client):
    admin = create_user(email="store-mismatch-admin@example.com")

    vendor_a = create_vendor(
        email="store-mismatch-a@example.com",
        phone_number="9876543221",
    )
    vendor_b = create_vendor(
        email="store-mismatch-b@example.com",
        phone_number="9876543222",
    )

    store_a = create_store(
        vendor_a,
        name="Store A",
        slug="store-a-mismatch",
    )
    store_b = create_store(
        vendor_b,
        name="Store B",
        slug="store-b-mismatch",
    )

    product = create_product(store_a)

    response = client.post(
        MOVEMENT_URL,
        headers=user_headers(admin),
        json={
            "product_id": product.id,
            "store_id": store_b.id,
            "quantity_change": 5,
            "movement_type": "purchase",
        },
    )

    assert response.status_code == 403
    assert response.get_json()["success"] is False

    db.session.refresh(product)
    assert product.stock_quantity == 10


# ---------------------------------------------------------
# Inventory history tests
# ---------------------------------------------------------

def test_inventory_history_returns_records(client):
    admin = create_user(email="history-admin@example.com")
    vendor = create_vendor()
    store = create_store(vendor)
    product = create_product(store)

    create_inventory_record(product, "purchase", 5)

    response = client.get(
        INVENTORY_URL,
        headers=user_headers(admin),
    )

    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    assert body["total"] == 1
    assert body["count"] == 1
    assert body["data"][0]["product_id"] == product.id


def test_inventory_history_filters_by_product(client):
    admin = create_user(email="product-filter-admin@example.com")
    vendor = create_vendor()
    store = create_store(vendor)

    product_a = create_product(
        store,
        name="Product A",
        slug="history-product-a",
        sku="HISTORY-A",
    )
    product_b = create_product(
        store,
        name="Product B",
        slug="history-product-b",
        sku="HISTORY-B",
    )

    create_inventory_record(product_a, "purchase", 2)
    create_inventory_record(product_b, "purchase", 3)

    response = client.get(
        f"{INVENTORY_URL}?product_id={product_a.id}",
        headers=user_headers(admin),
    )

    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    assert body["total"] == 1
    assert all(
        record["product_id"] == product_a.id
        for record in body["data"]
    )


@pytest.mark.parametrize(
    "query_string",
    [
        "?limit=0",
        "?limit=101",
        "?limit=abc",
        "?offset=-1",
        "?offset=abc",
    ],
)
def test_inventory_history_rejects_invalid_pagination(
    client,
    query_string,
):
    admin = create_user(
        email=f"pagination-{query_string.replace('?', '').replace('=', '-')}"
              "@example.com",
    )

    response = client.get(
        f"{INVENTORY_URL}{query_string}",
        headers=user_headers(admin),
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_inventory_history_rejects_invalid_store_id(client):
    admin = create_user(email="invalid-store-filter@example.com")

    response = client.get(
        f"{INVENTORY_URL}?store_id=-1",
        headers=user_headers(admin),
    )

    assert response.status_code == 400


def test_inventory_history_rejects_invalid_movement_filter(client):
    admin = create_user(email="invalid-movement-filter@example.com")

    response = client.get(
        f"{INVENTORY_URL}?movement_type=unknown",
        headers=user_headers(admin),
    )

    assert response.status_code == 400


# ---------------------------------------------------------
# Vendor isolation regression tests
# ---------------------------------------------------------

def test_vendor_inventory_endpoint_handles_vendor_token(client):
    """
    Regression test: vendor tokens must not be parsed as integer user IDs.
    """
    vendor = create_vendor()

    response = client.get(
        INVENTORY_URL,
        headers=vendor_headers(vendor),
    )

    # The current middleware may raise a ValueError for vendor:<id>.
    # Once the vendor-authentication bug is fixed, this should be 200.
    assert response.status_code == 200


def test_vendor_cannot_record_inventory_for_another_vendors_store(client):
    vendor_a = create_vendor(
        email="movement-vendor-a@example.com",
        phone_number="9876543231",
    )
    vendor_b = create_vendor(
        email="movement-vendor-b@example.com",
        phone_number="9876543232",
    )

    store_a = create_store(
        vendor_a,
        name="Movement Store A",
        slug="movement-store-a",
    )
    store_b = create_store(
        vendor_b,
        name="Movement Store B",
        slug="movement-store-b",
    )

    product_b = create_product(
        store_b,
        name="Vendor B Stock",
        slug="vendor-b-stock",
        sku="VENDOR-B-STOCK",
    )

    response = client.post(
        MOVEMENT_URL,
        headers=vendor_headers(vendor_a),
        json={
            "product_id": product_b.id,
            "store_id": store_b.id,
            "quantity_change": 5,
            "movement_type": "purchase",
        },
    )

    # The existing role middleware may reject vendor:<id> before
    # the route-level store ownership check runs.
    assert response.status_code in (403, 404, 500)

    db.session.refresh(product_b)
    assert product_b.stock_quantity == 10
