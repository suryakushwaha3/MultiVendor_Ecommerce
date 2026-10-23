from decimal import Decimal
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

from flask_jwt_extended import create_access_token

from app.extensions import db
from tables.user_table import User
from tables.address_table import Address
from tables.order_table import Order
from tables.cart_table import Cart
from tables.cart_item_table import CartItem
from tables.vendor_table import Vendor
from tables.store_table import Store
from tables.category_table import Category
from tables.product_table import Product
from tables.product_image_table import ProductImage
from tables.order_item_table import OrderItem
from utils.security import hash_password


ORDERS_URL = "/api/v1/orders"


# =========================================================
# TEST HELPERS
# =========================================================

def create_test_customer(
    name="Test Customer",
    email="customer@example.com",
    phone_number="9876543210",
):
    customer = User(
        name=name,
        email=email,
        phone_number=phone_number,
        password_hash=hash_password("StrongTestPass123!"),
        role="customer",
        is_active=True,
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def create_test_address(customer):
    address = Address(
        user_id=customer.id,
        full_name=customer.name,
        phone_number=customer.phone_number,
        address_line1="House 123, Test Road",
        city="Varanasi",
        state="Uttar Pradesh",
        pincode="221001",
        country="India",
        address_type="home",
        is_default=True,
    )

    db.session.add(address)
    db.session.commit()

    return address


def create_test_product(
    email="vendor@example.com",
    phone="9000000001",
    name="Test Product",
    slug="test-product",
    sku="SKU-TEST-001",
    price=Decimal("1000.00"),
    stock=10,
    is_active=True,
    discount_price=None,
):
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

    store = Store(
        vendor_id=vendor.id,
        store_name=f"Store {name}",
        slug=f"store-{slug}",
        is_active=True,
    )

    db.session.add(store)
    db.session.flush()

    category = Category(
        category_name="Test Electronics",
        slug="test-electronics",
        is_active=True,
    )

    db.session.add(category)
    db.session.flush()

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


def add_product_to_customer_cart(customer, product, quantity=1):
    cart = db.session.query(Cart).filter_by(
        user_id=customer.id
    ).first()

    if cart is None:
        cart = Cart(user_id=customer.id)
        db.session.add(cart)
        db.session.flush()

    item = CartItem(
        cart_id=cart.id,
        product_id=product.id,
        quantity=quantity,
    )

    db.session.add(item)
    db.session.commit()

    return cart, item


def get_customer_token(customer):
    return create_access_token(identity=str(customer.id))


def customer_headers(customer):
    return {
        "Authorization": f"Bearer {get_customer_token(customer)}"
    }


# =========================================================
# AUTHENTICATION TESTS
# =========================================================

def test_create_order_requires_authentication(client):
    response = client.post(
        ORDERS_URL,
        json={"address_id": 1},
    )

    assert response.status_code == 401


def test_create_order_rejects_invalid_token(client):
    response = client.post(
        ORDERS_URL,
        json={"address_id": 1},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_get_customer_orders_requires_authentication(client):
    response = client.get(ORDERS_URL)

    assert response.status_code == 401


def test_get_single_order_requires_authentication(client):
    response = client.get(f"{ORDERS_URL}/1")

    assert response.status_code == 401


# =========================================================
# ADDRESS VALIDATION TESTS
# =========================================================

def test_create_order_rejects_invalid_address_id(client):
    customer = create_test_customer()
    response = client.post(
        ORDERS_URL,
        json={"address_id": "invalid"},
        headers=customer_headers(customer),
    )

    assert response.status_code == 400

    data = response.get_json()
    assert data["success"] is False
    assert "address_id" in data["message"]


def test_create_order_rejects_another_customers_address(client):
    customer_one = create_test_customer(
        name="Customer One",
        email="customer1@example.com",
        phone_number="9876543210",
    )

    customer_two = create_test_customer(
        name="Customer Two",
        email="customer2@example.com",
        phone_number="9876543211",
    )

    address_two = create_test_address(customer_two)

    response = client.post(
        ORDERS_URL,
        json={"address_id": address_two.id},
        headers=customer_headers(customer_one),
    )

    assert response.status_code == 404
    assert response.get_json()["success"] is False


# =========================================================
# EMPTY CART TESTS
# =========================================================

def test_create_order_rejects_empty_cart(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    response = client.post(
        ORDERS_URL,
        json={"address_id": address.id},
        headers=customer_headers(customer),
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_create_order_rejects_when_cart_does_not_exist(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    response = client.post(
        ORDERS_URL,
        json={"address_id": address.id},
        headers=customer_headers(customer),
    )

    # Current order operation may return the same empty-cart
    # response for a missing cart and an empty existing cart.
    assert response.status_code == 400


# =========================================================
# SUCCESSFUL CHECKOUT TESTS
# =========================================================

def test_create_order_successfully(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product()
    add_product_to_customer_cart(
        customer=customer,
        product=product,
        quantity=2,
    )

    response = client.post(
        ORDERS_URL,
        json={
            "address_id": address.id,
            "notes": "Please deliver carefully.",
        },
        headers=customer_headers(customer),
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["success"] is True

    order_data = data.get("data", data.get("order"))
    assert order_data is not None

    assert order_data["user_id"] == customer.id
    assert order_data["address_id"] == address.id
    assert order_data["order_status"] == "placed"
    assert order_data["payment_status"] == "pending"
    assert order_data["notes"] == "Please deliver carefully."

    assert Decimal(order_data["subtotal"]) == Decimal("2000.00")
    assert Decimal(order_data["total_amount"]) == Decimal("2000.00")

    assert len(order_data["items"]) == 1

    item = order_data["items"][0]
    assert item["product_id"] == product.id
    assert item["product_name"] == product.product_name
    assert item["sku"] == product.sku
    assert item["quantity"] == 2
    assert Decimal(item["unit_price"]) == Decimal("1000.00")
    assert Decimal(item["total_price"]) == Decimal("2000.00")


def test_checkout_deducts_product_stock(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product(
        email="stock-vendor@example.com",
        phone="9000000002",
        slug="stock-product",
        sku="SKU-STOCK-001",
        stock=10,
    )

    add_product_to_customer_cart(customer, product, quantity=3)

    response = client.post(
        ORDERS_URL,
        json={"address_id": address.id},
        headers=customer_headers(customer),
    )

    assert response.status_code == 201

    db.session.expire_all()
    updated_product = db.session.get(Product, product.id)

    assert updated_product.stock_quantity == 7


def test_checkout_clears_cart_items(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product(
        email="cart-vendor@example.com",
        phone="9000000003",
        slug="cart-product",
        sku="SKU-CART-001",
    )

    cart, _ = add_product_to_customer_cart(
        customer,
        product,
        quantity=1,
    )

    response = client.post(
        ORDERS_URL,
        json={"address_id": address.id},
        headers=customer_headers(customer),
    )

    assert response.status_code == 201

    db.session.expire_all()

    remaining_items = CartItem.query.filter_by(
        cart_id=cart.id
    ).all()

    assert remaining_items == []


def test_checkout_uses_discount_price(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product(
        email="discount-vendor@example.com",
        phone="9000000004",
        slug="discount-product",
        sku="SKU-DISCOUNT-001",
        price=Decimal("1000.00"),
        discount_price=Decimal("750.00"),
    )

    add_product_to_customer_cart(customer, product, quantity=2)

    response = client.post(
        ORDERS_URL,
        json={"address_id": address.id},
        headers=customer_headers(customer),
    )

    assert response.status_code == 201

    data = response.get_json()
    order_data = data.get("data", data.get("order"))

    assert Decimal(order_data["subtotal"]) == Decimal("1500.00")
    assert Decimal(order_data["total_amount"]) == Decimal("1500.00")
    assert Decimal(order_data["items"][0]["unit_price"]) == Decimal("750.00")


# =========================================================
# STOCK AND PRODUCT VALIDATION TESTS
# =========================================================

def test_checkout_rejects_insufficient_stock(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product(
        email="limited-vendor@example.com",
        phone="9000000005",
        slug="limited-product",
        sku="SKU-LIMITED-001",
        stock=2,
    )

    add_product_to_customer_cart(customer, product, quantity=3)

    response = client.post(
        ORDERS_URL,
        json={"address_id": address.id},
        headers=customer_headers(customer),
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False

    db.session.expire_all()
    updated_product = db.session.get(Product, product.id)

    assert updated_product.stock_quantity == 2


def test_checkout_rejects_inactive_product(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product(
        email="inactive-vendor@example.com",
        phone="9000000006",
        slug="inactive-product",
        sku="SKU-INACTIVE-001",
        is_active=False,
    )

    add_product_to_customer_cart(customer, product, quantity=1)

    response = client.post(
        ORDERS_URL,
        json={"address_id": address.id},
        headers=customer_headers(customer),
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False

    assert Order.query.filter_by(user_id=customer.id).count() == 0


# =========================================================
# ORDER LIST AND OWNERSHIP TESTS
# =========================================================

def test_get_customer_orders_returns_empty_list(client):
    customer = create_test_customer()

    response = client.get(
        ORDERS_URL,
        headers=customer_headers(customer),
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"] == []
    assert data["count"] == 0


def test_customer_cannot_access_another_customers_order(client):
    customer_one = create_test_customer(
        name="Customer One",
        email="customer1@example.com",
        phone_number="9876543210",
    )

    customer_two = create_test_customer(
        name="Customer Two",
        email="customer2@example.com",
        phone_number="9876543211",
    )

    address_two = create_test_address(customer_two)

    order = Order(
        order_number="ORD-TEST-00000001",
        user_id=customer_two.id,
        address_id=address_two.id,
        subtotal=100,
        discount_amount=0,
        shipping_amount=0,
        tax_amount=0,
        total_amount=100,
        payment_status="pending",
        order_status="placed",
    )

    db.session.add(order)
    db.session.commit()

    response = client.get(
        f"{ORDERS_URL}/{order.id}",
        headers=customer_headers(customer_one),
    )

    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_customer_order_list_contains_only_own_orders(client):
    customer_one = create_test_customer(
        name="Customer One",
        email="customer1@example.com",
        phone_number="9876543210",
    )

    customer_two = create_test_customer(
        name="Customer Two",
        email="customer2@example.com",
        phone_number="9876543211",
    )

    address_one = create_test_address(customer_one)
    address_two = create_test_address(customer_two)

    order_one = Order(
        order_number="ORD-TEST-00000011",
        user_id=customer_one.id,
        address_id=address_one.id,
        subtotal=100,
        discount_amount=0,
        shipping_amount=0,
        tax_amount=0,
        total_amount=100,
        payment_status="pending",
        order_status="placed",
    )

    order_two = Order(
        order_number="ORD-TEST-00000012",
        user_id=customer_two.id,
        address_id=address_two.id,
        subtotal=200,
        discount_amount=0,
        shipping_amount=0,
        tax_amount=0,
        total_amount=200,
        payment_status="pending",
        order_status="placed",
    )

    db.session.add_all([order_one, order_two])
    db.session.commit()

    response = client.get(
        ORDERS_URL,
        headers=customer_headers(customer_one),
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["count"] == 1

    returned_orders = data["data"]
    assert len(returned_orders) == 1
    assert returned_orders[0]["id"] == order_one.id
    assert all(
        order["user_id"] == customer_one.id
        for order in returned_orders
    )




def test_checkout_rolls_back_when_order_item_creation_fails(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product(
        email="rollback-vendor@example.com",
        phone="9000000091",
        slug="rollback-product",
        sku="SKU-ROLLBACK-001",
        stock=10,
    )

    cart, _ = add_product_to_customer_cart(
        customer,
        product,
        quantity=2,
    )

    with patch(
        "operations.order_operation.OrderItem",
        side_effect=SQLAlchemyError(
            "Simulated order item failure"
        ),
    ):
        response = client.post(
            ORDERS_URL,
            json={"address_id": address.id},
            headers=customer_headers(customer),
        )

    assert response.status_code == 500
    assert response.get_json()["success"] is False

    db.session.expire_all()

    updated_product = db.session.get(Product, product.id)

    assert updated_product.stock_quantity == 10

    assert (
        Order.query.filter_by(user_id=customer.id).count()
        == 0
    )

    assert (
        CartItem.query.filter_by(cart_id=cart.id).count()
        == 1
    )


def test_checkout_rolls_back_when_commit_fails(client):
    customer = create_test_customer()
    address = create_test_address(customer)

    product = create_test_product(
        email="commit-rollback-vendor@example.com",
        phone="9000000092",
        slug="commit-rollback-product",
        sku="SKU-COMMIT-ROLLBACK-001",
        stock=10,
    )

    cart, _ = add_product_to_customer_cart(
        customer,
        product,
        quantity=2,
    )

    with patch(
        "operations.order_operation.db.session.commit",
        side_effect=SQLAlchemyError(
            "Simulated commit failure"
        ),
    ):
        response = client.post(
            ORDERS_URL,
            json={"address_id": address.id},
            headers=customer_headers(customer),
        )

    assert response.status_code == 500
    assert response.get_json()["success"] is False

    db.session.expire_all()

    updated_product = db.session.get(Product, product.id)

    assert updated_product.stock_quantity == 10

    assert (
        Order.query.filter_by(user_id=customer.id).count()
        == 0
    )

    assert (
        CartItem.query.filter_by(cart_id=cart.id).count()
        == 1
    )