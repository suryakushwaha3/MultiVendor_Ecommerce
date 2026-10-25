from decimal import Decimal
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import create_access_token

from app.extensions import db
from tables.user_table import User
from tables.cart_table import Cart
from tables.cart_item_table import CartItem
from tables.product_table import Product
from tables.vendor_table import Vendor
from tables.store_table import Store
from tables.category_table import Category
from tables.product_image_table import ProductImage
from utils.security import hash_password


CART_URL = "/api/v1/cart"


# =========================================================
# TEST HELPERS
# =========================================================

def create_customer(
    name="Test Customer",
    email="customer@example.com",
    phone="9876543210",
):
    customer = User(
        name=name,
        email=email,
        phone_number=phone,
        password_hash=hash_password("StrongTestPass123!"),
        role="customer",
        is_active=True,
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def create_product(
    email="vendor@example.com",
    phone="9000000001",
    name="Test Product",
    slug="test-product",
    sku="SKU-TEST-001",
    price=Decimal("1000.00"),
    discount_price=None,
    stock=10,
    is_active=True,
):
    # -----------------------------------------------------
    # Create vendor
    # -----------------------------------------------------
    vendor = Vendor(
        name=f"Vendor {email}",
        email=email,
        phone_number=phone,
        password_hash=hash_password("StrongVendorPass123!"),
        business_name=f"Business {email}",
        business_address="Test Address",
        is_active=True,
        is_approved=True,
    )

    db.session.add(vendor)
    db.session.flush()

    # -----------------------------------------------------
    # Create store
    # -----------------------------------------------------
    store = Store(
        vendor_id=vendor.id,
        store_name=f"Store {name}",
        slug=f"store-{slug}",
        is_active=True,
    )

    db.session.add(store)
    db.session.flush()

    # -----------------------------------------------------
    # FIX: Reuse category if it already exists
    # -----------------------------------------------------
    category = Category.query.filter_by(
        slug="test-electronics"
    ).first()

    if category is None:
        category = Category(
            category_name="Test Electronics",
            slug="test-electronics",
            is_active=True,
        )

        db.session.add(category)
        db.session.flush()

    # -----------------------------------------------------
    # Create product
    # -----------------------------------------------------
    product = Product(
        store_id=store.id,
        category_id=category.id,
        product_name=name,
        slug=slug,
        description=f"Description for {name}",
        sku=sku,
        price=price,
        discount_price=discount_price,
        stock_quantity=stock,
        is_active=is_active,
        is_featured=False,
    )

    db.session.add(product)
    db.session.flush()

    # -----------------------------------------------------
    # Create product image
    # -----------------------------------------------------
    image = ProductImage(
        product_id=product.id,
        image_url=f"https://example.com/{slug}.jpg",
        alt_text=name,
        is_primary=True,
        display_order=0,
    )

    db.session.add(image)
    db.session.commit()

    return product


def get_token(customer):
    return create_access_token(
        identity=str(customer.id)
    )


def auth_headers(customer):
    return {
        "Authorization": f"Bearer {get_token(customer)}"
    }


def add_item(client, customer, product, quantity=1):
    return client.post(
        f"{CART_URL}/items",
        json={
            "product_id": product.id,
            "quantity": quantity,
        },
        headers=auth_headers(customer),
    )


# =========================================================
# AUTHENTICATION TESTS
# =========================================================

def test_get_cart_requires_authentication(client):
    response = client.get(CART_URL)

    assert response.status_code == 401


def test_add_item_requires_authentication(client):
    response = client.post(
        f"{CART_URL}/items",
        json={
            "product_id": 1,
            "quantity": 1,
        },
    )

    assert response.status_code == 401


# =========================================================
# GET CART TESTS
# =========================================================

def test_get_cart_creates_empty_cart(client):
    customer = create_customer()

    response = client.get(
        CART_URL,
        headers=auth_headers(customer),
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["cart"]["user_id"] == customer.id
    assert data["cart"]["items"] == []
    assert data["cart"]["item_count"] == 0
    assert data["cart"]["total_quantity"] == 0

    assert Decimal(
        data["cart"]["subtotal"]
    ) == Decimal("0.00")

    assert Cart.query.filter_by(
        user_id=customer.id
    ).count() == 1


# =========================================================
# ADD TO CART TESTS
# =========================================================

def test_add_product_to_cart(client):
    customer = create_customer()
    product = create_product()

    response = add_item(
        client,
        customer,
        product,
        quantity=2,
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["success"] is True
    assert data["cart"]["item_count"] == 1
    assert data["cart"]["total_quantity"] == 2

    assert Decimal(
        data["cart"]["subtotal"]
    ) == Decimal("2000.00")

    item = data["cart"]["items"][0]

    assert item["product_id"] == product.id
    assert item["product_name"] == product.product_name
    assert item["quantity"] == 2

    assert Decimal(
        item["unit_price"]
    ) == Decimal("1000.00")

    assert Decimal(
        item["line_total"]
    ) == Decimal("2000.00")

    assert (
        item["image_url"]
        == "https://example.com/test-product.jpg"
    )


def test_add_product_uses_discount_price(client):
    customer = create_customer()

    product = create_product(
        email="discount-vendor@example.com",
        phone="9000000002",
        slug="discount-product",
        sku="SKU-DISCOUNT-001",
        price=Decimal("1000.00"),
        discount_price=Decimal("750.00"),
    )

    response = add_item(
        client,
        customer,
        product,
        quantity=2,
    )

    assert response.status_code == 201

    cart = response.get_json()["cart"]

    assert Decimal(
        cart["items"][0]["unit_price"]
    ) == Decimal("750.00")

    assert Decimal(
        cart["items"][0]["line_total"]
    ) == Decimal("1500.00")

    assert Decimal(
        cart["subtotal"]
    ) == Decimal("1500.00")


def test_adding_same_product_increases_quantity(client):
    customer = create_customer()
    product = create_product()

    first_response = add_item(
        client,
        customer,
        product,
        quantity=2,
    )

    second_response = add_item(
        client,
        customer,
        product,
        quantity=3,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    cart = second_response.get_json()["cart"]

    assert cart["item_count"] == 1
    assert cart["total_quantity"] == 5
    assert cart["items"][0]["quantity"] == 5

    assert CartItem.query.filter_by(
        cart_id=cart["cart_id"],
        product_id=product.id,
    ).count() == 1


def test_add_product_defaults_quantity_to_one(client):
    customer = create_customer()
    product = create_product()

    response = client.post(
        f"{CART_URL}/items",
        json={
            "product_id": product.id,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 201

    assert (
        response.get_json()["cart"]["total_quantity"]
        == 1
    )


def test_add_nonexistent_product_returns_404(client):
    customer = create_customer()

    response = client.post(
        f"{CART_URL}/items",
        json={
            "product_id": 99999,
            "quantity": 1,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_add_inactive_product_is_rejected(client):
    customer = create_customer()

    product = create_product(
        is_active=False,
    )

    response = add_item(
        client,
        customer,
        product,
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_add_quantity_above_stock_is_rejected(client):
    customer = create_customer()

    product = create_product(
        stock=3,
    )

    response = add_item(
        client,
        customer,
        product,
        quantity=4,
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["success"] is False
    assert data["available_stock"] == 3

    assert Cart.query.filter_by(
        user_id=customer.id
    ).count() == 0


def test_increasing_quantity_above_stock_is_rejected(client):
    customer = create_customer()

    product = create_product(
        stock=5,
    )

    first_response = add_item(
        client,
        customer,
        product,
        quantity=3,
    )

    assert first_response.status_code == 201

    second_response = add_item(
        client,
        customer,
        product,
        quantity=3,
    )

    assert second_response.status_code == 400

    data = second_response.get_json()

    assert data["current_quantity"] == 3
    assert data["available_stock"] == 5

    db.session.expire_all()

    item = CartItem.query.filter_by(
        product_id=product.id,
    ).one()

    assert item.quantity == 3


# =========================================================
# INPUT VALIDATION TESTS
# =========================================================

def test_add_item_rejects_invalid_json(client):
    customer = create_customer()

    response = client.post(
        f"{CART_URL}/items",
        data="invalid-json",
        content_type="application/json",
        headers=auth_headers(customer),
    )

    assert response.status_code == 400


def test_add_item_rejects_string_product_id(client):
    customer = create_customer()

    response = client.post(
        f"{CART_URL}/items",
        json={
            "product_id": "1",
            "quantity": 1,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 400


def test_add_item_rejects_boolean_product_id(client):
    customer = create_customer()

    response = client.post(
        f"{CART_URL}/items",
        json={
            "product_id": True,
            "quantity": 1,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 400


def test_add_item_rejects_zero_quantity(client):
    customer = create_customer()
    product = create_product()

    response = add_item(
        client,
        customer,
        product,
        quantity=0,
    )

    assert response.status_code == 400


def test_add_item_rejects_negative_quantity(client):
    customer = create_customer()
    product = create_product()

    response = add_item(
        client,
        customer,
        product,
        quantity=-1,
    )

    assert response.status_code == 400


def test_add_item_rejects_boolean_quantity(client):
    customer = create_customer()
    product = create_product()

    response = client.post(
        f"{CART_URL}/items",
        json={
            "product_id": product.id,
            "quantity": True,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 400


# =========================================================
# UPDATE CART ITEM TESTS
# =========================================================

def test_update_cart_item_quantity(client):
    customer = create_customer()
    product = create_product()

    add_response = add_item(
        client,
        customer,
        product,
        quantity=2,
    )

    cart = add_response.get_json()["cart"]

    cart_item_id = cart["items"][0]["cart_item_id"]

    response = client.patch(
        f"{CART_URL}/items/{cart_item_id}",
        json={
            "quantity": 4,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 200

    updated_cart = response.get_json()["cart"]

    assert updated_cart["items"][0]["quantity"] == 4
    assert updated_cart["total_quantity"] == 4

    assert Decimal(
        updated_cart["subtotal"]
    ) == Decimal("4000.00")


def test_update_cart_item_rejects_quantity_above_stock(client):
    customer = create_customer()

    product = create_product(
        stock=5,
    )

    add_response = add_item(
        client,
        customer,
        product,
        quantity=2,
    )

    item_id = (
        add_response.get_json()["cart"]["items"][0]["cart_item_id"]
    )

    response = client.patch(
        f"{CART_URL}/items/{item_id}",
        json={
            "quantity": 6,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 400

    db.session.expire_all()

    item = db.session.get(
        CartItem,
        item_id,
    )

    assert item.quantity == 2


def test_update_cart_item_rejects_zero_quantity(client):
    customer = create_customer()
    product = create_product()

    add_response = add_item(
        client,
        customer,
        product,
    )

    item_id = (
        add_response.get_json()["cart"]["items"][0]["cart_item_id"]
    )

    response = client.patch(
        f"{CART_URL}/items/{item_id}",
        json={
            "quantity": 0,
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 400


def test_update_cart_item_rejects_string_quantity(client):
    customer = create_customer()
    product = create_product()

    add_response = add_item(
        client,
        customer,
        product,
    )

    item_id = (
        add_response.get_json()["cart"]["items"][0]["cart_item_id"]
    )

    response = client.patch(
        f"{CART_URL}/items/{item_id}",
        json={
            "quantity": "3",
        },
        headers=auth_headers(customer),
    )

    assert response.status_code == 400


def test_update_other_customer_cart_item_is_rejected(client):
    customer_one = create_customer(
        email="customer-one@example.com",
        phone="9876543211",
    )

    customer_two = create_customer(
        email="customer-two@example.com",
        phone="9876543212",
    )

    product = create_product()

    add_response = add_item(
        client,
        customer_one,
        product,
        quantity=2,
    )

    item_id = (
        add_response.get_json()["cart"]["items"][0]["cart_item_id"]
    )

    response = client.patch(
        f"{CART_URL}/items/{item_id}",
        json={
            "quantity": 5,
        },
        headers=auth_headers(customer_two),
    )

    assert response.status_code == 404

    db.session.expire_all()

    item = db.session.get(
        CartItem,
        item_id,
    )

    assert item.quantity == 2


# =========================================================
# REMOVE CART ITEM TESTS
# =========================================================

def test_remove_cart_item(client):
    customer = create_customer()
    product = create_product()

    add_response = add_item(
        client,
        customer,
        product,
    )

    cart = add_response.get_json()["cart"]

    item_id = cart["items"][0]["cart_item_id"]

    response = client.delete(
        f"{CART_URL}/items/{item_id}",
        headers=auth_headers(customer),
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["cart"]["items"] == []
    assert data["cart"]["item_count"] == 0


def test_remove_other_customer_cart_item_is_rejected(client):
    customer_one = create_customer(
        email="remove-one@example.com",
        phone="9876543213",
    )

    customer_two = create_customer(
        email="remove-two@example.com",
        phone="9876543214",
    )

    product = create_product()

    add_response = add_item(
        client,
        customer_one,
        product,
    )

    item_id = (
        add_response.get_json()["cart"]["items"][0]["cart_item_id"]
    )

    response = client.delete(
        f"{CART_URL}/items/{item_id}",
        headers=auth_headers(customer_two),
    )

    assert response.status_code == 404

    assert db.session.get(
        CartItem,
        item_id,
    ) is not None


def test_remove_nonexistent_cart_item_returns_404(client):
    customer = create_customer()

    response = client.delete(
        f"{CART_URL}/items/99999",
        headers=auth_headers(customer),
    )

    assert response.status_code == 404


# =========================================================
# CLEAR CART TESTS
# =========================================================

def test_clear_cart(client):
    customer = create_customer()

    product_one = create_product(
        email="clear-one@example.com",
        phone="9000000011",
        slug="clear-product-one",
        sku="SKU-CLEAR-001",
    )

    product_two = create_product(
        email="clear-two@example.com",
        phone="9000000012",
        slug="clear-product-two",
        sku="SKU-CLEAR-002",
    )

    first_response = add_item(
        client,
        customer,
        product_one,
        quantity=2,
    )

    second_response = add_item(
        client,
        customer,
        product_two,
        quantity=3,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.delete(
        CART_URL,
        headers=auth_headers(customer),
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["cart"]["items"] == []
    assert data["cart"]["item_count"] == 0
    assert data["cart"]["total_quantity"] == 0

    cart = Cart.query.filter_by(
        user_id=customer.id,
    ).one()

    assert len(cart.items) == 0


def test_clear_nonexistent_cart_succeeds(client):
    customer = create_customer()

    response = client.delete(
        CART_URL,
        headers=auth_headers(customer),
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True
    assert data["cart"] is None


# =========================================================
# DATABASE ERROR / ROLLBACK TESTS
# =========================================================

def test_add_item_rolls_back_when_commit_fails(client):
    customer = create_customer()
    product = create_product()

    with patch(
        "operations.cart_operation.db.session.commit",
        side_effect=SQLAlchemyError(
            "Simulated commit failure"
        ),
    ):
        response = add_item(
            client,
            customer,
            product,
            quantity=2,
        )

    assert response.status_code == 500
    assert response.get_json()["success"] is False

    db.session.expire_all()

    assert Cart.query.filter_by(
        user_id=customer.id,
    ).count() == 0

    assert CartItem.query.count() == 0


def test_update_item_rolls_back_when_commit_fails(client):
    customer = create_customer()
    product = create_product()

    add_response = add_item(
        client,
        customer,
        product,
        quantity=2,
    )

    item_id = (
        add_response.get_json()["cart"]["items"][0]["cart_item_id"]
    )

    with patch(
        "operations.cart_operation.db.session.commit",
        side_effect=SQLAlchemyError(
            "Simulated commit failure"
        ),
    ):
        response = client.patch(
            f"{CART_URL}/items/{item_id}",
            json={
                "quantity": 4,
            },
            headers=auth_headers(customer),
        )

    assert response.status_code == 500
    assert response.get_json()["success"] is False

    db.session.expire_all()

    item = db.session.get(
        CartItem,
        item_id,
    )

    assert item.quantity == 2


def test_remove_item_rolls_back_when_commit_fails(client):
    customer = create_customer()
    product = create_product()

    add_response = add_item(
        client,
        customer,
        product,
    )

    item_id = (
        add_response.get_json()["cart"]["items"][0]["cart_item_id"]
    )

    with patch(
        "operations.cart_operation.db.session.commit",
        side_effect=SQLAlchemyError(
            "Simulated commit failure"
        ),
    ):
        response = client.delete(
            f"{CART_URL}/items/{item_id}",
            headers=auth_headers(customer),
        )

    assert response.status_code == 500
    assert response.get_json()["success"] is False

    db.session.expire_all()

    assert db.session.get(
        CartItem,
        item_id,
    ) is not None


def test_clear_cart_rolls_back_when_commit_fails(client):
    customer = create_customer()
    product = create_product()

    add_response = add_item(
        client,
        customer,
        product,
        quantity=2,
    )

    cart_id = add_response.get_json()["cart"]["cart_id"]

    with patch(
        "operations.cart_operation.db.session.commit",
        side_effect=SQLAlchemyError(
            "Simulated commit failure"
        ),
    ):
        response = client.delete(
            CART_URL,
            headers=auth_headers(customer),
        )

    assert response.status_code == 500
    assert response.get_json()["success"] is False

    db.session.expire_all()

    cart = db.session.get(
        Cart,
        cart_id,
    )

    assert cart is not None
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2