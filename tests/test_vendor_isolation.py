from decimal import Decimal

from app.extensions import db
from tables.address_table import Address
from tables.category_table import Category
from tables.order_item_table import OrderItem
from tables.order_table import Order
from tables.product_table import Product
from tables.store_table import Store
from tables.user_table import User
from tables.vendor_table import Vendor
from utils.security import hash_password


def create_vendor(email, phone_number):
    vendor = Vendor(
        name=f"Vendor {email}",
        email=email,
        phone_number=phone_number,
        password_hash=hash_password("StrongVendorPass123!"),
        business_name=f"Business {email}",
        business_address="Test Address",
        is_active=True,
        is_approved=True,
    )
    db.session.add(vendor)
    db.session.flush()
    return vendor


def create_store(vendor, name, slug):
    store = Store(
        vendor_id=vendor.id,
        store_name=name,
        slug=slug,
        is_active=True,
    )
    db.session.add(store)
    db.session.flush()
    return store


def create_product(store, category, name, slug, sku, price, stock):
    product = Product(
        store_id=store.id,
        category_id=category.id,
        product_name=name,
        slug=slug,
        description=f"Test product {name}",
        sku=sku,
        price=Decimal(str(price)),
        stock_quantity=stock,
        is_active=True,
    )
    db.session.add(product)
    db.session.flush()
    return product


def create_order_customer():
    user = User(
        name="Test Buyer",
        email="buyer@example.com",
        phone_number="9876543201",
        password_hash=hash_password("StrongTestPass123!"),
        role="customer",
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()

    address = Address(
        user_id=user.id,
        full_name="Test Buyer",
        phone_number="9876543201",
        address_line1="Test Street",
        city="Varanasi",
        state="Uttar Pradesh",
        pincode="221001",
        country="India",
        address_type="home",
        is_default=True,
    )
    db.session.add(address)
    db.session.flush()

    return user, address


def create_order_item(order, product, amount, quantity=1):
    amount = Decimal(str(amount))

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.product_name,
        sku=product.sku,
        quantity=quantity,
        unit_price=amount,
        discount_amount=Decimal("0.00"),
        total_price=amount * quantity,
    )
    db.session.add(item)
    return item


def test_vendor_dashboard_isolates_mixed_order_sales(client):
    # Create two independent vendors.
    vendor_a = create_vendor(
        "vendor-a@example.com",
        "9876543211",
    )
    vendor_b = create_vendor(
        "vendor-b@example.com",
        "9876543212",
    )

    # Give each vendor their own store.
    store_a = create_store(
        vendor_a,
        "Store A",
        "store-a",
    )
    store_b = create_store(
        vendor_b,
        "Store B",
        "store-b",
    )

    category = Category(
        category_name="Test Electronics",
        slug="test-electronics",
        is_active=True,
    )
    db.session.add(category)
    db.session.flush()

    # Vendor A owns two products.
    product_a1 = create_product(
        store_a,
        category,
        "Product A1",
        "product-a1",
        "SKU-A1",
        "500.00",
        10,
    )
    product_a2 = create_product(
        store_a,
        category,
        "Product A2",
        "product-a2",
        "SKU-A2",
        "200.00",
        3,
    )

    # Vendor B owns one product.
    product_b1 = create_product(
        store_b,
        category,
        "Product B1",
        "product-b1",
        "SKU-B1",
        "800.00",
        20,
    )

    user, address = create_order_customer()

    # One order contains products from both vendors.
    mixed_order = Order(
        order_number="TEST-MIXED-001",
        user_id=user.id,
        address_id=address.id,
        subtotal=Decimal("1300.00"),
        discount_amount=Decimal("0.00"),
        shipping_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("1300.00"),
        payment_status="paid",
        order_status="placed",
    )
    db.session.add(mixed_order)
    db.session.flush()

    create_order_item(
        mixed_order,
        product_a1,
        "500.00",
    )
    create_order_item(
        mixed_order,
        product_b1,
        "800.00",
    )

    db.session.commit()

    # Import the existing vendor-token helper locally to avoid
    # depending on another test module's fixtures or test functions.
    from flask_jwt_extended import create_access_token

    token_a = create_access_token(
        identity=f"vendor:{vendor_a.id}"
    )
    token_b = create_access_token(
        identity=f"vendor:{vendor_b.id}"
    )

    response_a = client.get(
        "/api/v1/vendor/dashboard",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    response_b = client.get(
        "/api/v1/vendor/dashboard",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    dashboard_a = response_a.get_json()["dashboard"]
    dashboard_b = response_b.get_json()["dashboard"]

    # Vendor A sees only their own store and products.
    assert dashboard_a["stores"]["total"] == 1
    assert dashboard_a["products"]["total"] == 2
    assert dashboard_a["products"]["total_stock"] == 13
    assert dashboard_a["products"]["low_stock"] == 1

    # Vendor B sees only their own store and product.
    assert dashboard_b["stores"]["total"] == 1
    assert dashboard_b["products"]["total"] == 1
    assert dashboard_b["products"]["total_stock"] == 20
    assert dashboard_b["products"]["low_stock"] == 0

    # Both vendors have one product in the same order.
    assert dashboard_a["orders"]["total"] == 1
    assert dashboard_b["orders"]["total"] == 1

    # Sales must be based on each vendor's own order items.
    assert Decimal(dashboard_a["sales"]["total"]) == Decimal("500.00")
    assert Decimal(dashboard_b["sales"]["total"]) == Decimal("800.00")

    # Vendor A's sales must not include Vendor B's product.
    assert Decimal(dashboard_a["sales"]["total"]) != Decimal("1300.00")

    # Vendor B's sales must not include Vendor A's product.
    assert Decimal(dashboard_b["sales"]["total"]) != Decimal("1300.00")


def test_vendor_dashboard_excludes_cancelled_and_refunded_sales(client):
    from decimal import Decimal

    from flask_jwt_extended import create_access_token

    # Create vendor and store.
    vendor = create_vendor(
        "status-vendor@example.com",
        "9876543231",
    )

    store = create_store(
        vendor,
        "Status Test Store",
        "status-test-store",
    )

    category = Category(
        category_name="Status Test Category",
        slug="status-test-category",
        is_active=True,
    )
    db.session.add(category)
    db.session.flush()

    product = create_product(
        store,
        category,
        "Status Test Product",
        "status-test-product",
        "SKU-STATUS-001",
        "500.00",
        50,
    )

    user, address = create_order_customer()

    # Create orders with different statuses.
    order_cases = [
        ("STATUS-PLACED", "placed", "500.00"),
        ("STATUS-DELIVERED", "delivered", "400.00"),
        ("STATUS-CANCELLED", "cancelled", "700.00"),
        ("STATUS-REFUNDED", "refunded", "300.00"),
    ]

    for order_number, status, amount in order_cases:
        order = Order(
            order_number=order_number,
            user_id=user.id,
            address_id=address.id,
            subtotal=Decimal(amount),
            discount_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal(amount),
            payment_status="paid",
            order_status=status,
        )
        db.session.add(order)
        db.session.flush()

        create_order_item(
            order,
            product,
            amount,
        )

    db.session.commit()

    token = create_access_token(
        identity=f"vendor:{vendor.id}"
    )

    response = client.get(
        "/api/v1/vendor/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    dashboard = response.get_json()["dashboard"]

    # All four orders contain this vendor's product.
    assert dashboard["orders"]["total"] == 4

    # Only placed and delivered sales should be included:
    # 500 + 400 = 900.
    assert Decimal(dashboard["sales"]["total"]) == Decimal("900.00")


def test_vendor_dashboard_with_no_stores_or_products(client):
    from decimal import Decimal
    from flask_jwt_extended import create_access_token

    vendor = create_vendor(
        "empty-vendor@example.com",
        "9876543232",
    )

    token = create_access_token(
        identity=f"vendor:{vendor.id}"
    )

    response = client.get(
        "/api/v1/vendor/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["success"] is True

    dashboard = data["dashboard"]

    assert dashboard["stores"]["total"] == 0
    assert dashboard["stores"]["active"] == 0

    assert dashboard["products"]["total"] == 0
    assert dashboard["products"]["active"] == 0
    assert dashboard["products"]["total_stock"] == 0
    assert dashboard["products"]["low_stock"] == 0

    assert dashboard["orders"]["total"] == 0
    assert dashboard["orders"]["pending"] == 0

    assert Decimal(dashboard["sales"]["total"]) == Decimal("0")
 