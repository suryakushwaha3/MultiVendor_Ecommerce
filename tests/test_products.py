from decimal import Decimal
from io import BytesIO

from flask_jwt_extended import create_access_token

from app.extensions import db
from tables.category_table import Category
from tables.product_table import Product
from tables.product_image_table import ProductImage
from tables.store_table import Store
from tables.vendor_table import Vendor
from utils.security import hash_password


PRODUCT_URL = "/api/v1/vendor/products"


def create_test_vendor(email, phone):
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
    return vendor


def create_test_store(vendor, name, slug):
    store = Store(
        vendor_id=vendor.id,
        store_name=name,
        slug=slug,
        is_active=True,
    )
    db.session.add(store)
    db.session.flush()
    return store


def create_test_category():
    category = Category(
        category_name="Test Electronics",
        slug="test-electronics",
        is_active=True,
    )
    db.session.add(category)
    db.session.flush()
    return category


def create_test_product(store, category, name, slug, sku):
    product = Product(
        store_id=store.id,
        category_id=category.id,
        product_name=name,
        slug=slug,
        description=f"Description for {name}",
        sku=sku,
        price=Decimal("1000.00"),
        stock_quantity=10,
        is_active=True,
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
    db.session.flush()

    return product


def vendor_headers(vendor):
    token = create_access_token(
        identity=f"vendor:{vendor.id}"
    )
    return {
        "Authorization": f"Bearer {token}"
    }


def valid_product_form(store, category):
    return {
        "store_id": str(store.id),
        "category_id": str(category.id),
        "product_name": "Test Headphones",
        "slug": "test-headphones",
        "description": "Wireless headphones for testing",
        "sku": "TEST-HEADPHONES-001",
        "price": "1500.00",
        "discount_price": "1200.00",
        "stock_quantity": "10",
        "weight": "0.500",
        "is_featured": "false",
    }


def test_product_list_requires_authentication(client):
    response = client.get(PRODUCT_URL)

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_product_list_rejects_invalid_token(client):
    response = client.get(
        PRODUCT_URL,
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_product_list_shows_only_authenticated_vendors_products(client):
    vendor_a = create_test_vendor(
        "product-a@example.com",
        "9876543211",
    )
    vendor_b = create_test_vendor(
        "product-b@example.com",
        "9876543212",
    )

    store_a = create_test_store(vendor_a, "Store A", "store-a")
    store_b = create_test_store(vendor_b, "Store B", "store-b")

    category = create_test_category()

    create_test_product(
        store_a, category, "Vendor A Product", "vendor-a-product", "SKU-A"
    )
    create_test_product(
        store_b, category, "Vendor B Product", "vendor-b-product", "SKU-B"
    )

    db.session.commit()

    response = client.get(
        PRODUCT_URL,
        headers=vendor_headers(vendor_a),
    )

    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True

    product_names = [
        product["product_name"]
        for product in body["data"]
    ]

    assert "Vendor A Product" in product_names
    assert "Vendor B Product" not in product_names


def test_vendor_cannot_view_another_vendors_product(client):
    vendor_a = create_test_vendor(
        "details-a@example.com",
        "9876543213",
    )
    vendor_b = create_test_vendor(
        "details-b@example.com",
        "9876543214",
    )

    store_b = create_test_store(vendor_b, "Store B", "details-store-b")
    category = create_test_category()

    product_b = create_test_product(
        store_b,
        category,
        "Private Vendor B Product",
        "private-vendor-b-product",
        "SKU-PRIVATE-B",
    )

    db.session.commit()

    response = client.get(
        f"{PRODUCT_URL}/{product_b.id}",
        headers=vendor_headers(vendor_a),
    )

    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_vendor_cannot_update_another_vendors_product(client):
    vendor_a = create_test_vendor(
        "update-a@example.com",
        "9876543215",
    )
    vendor_b = create_test_vendor(
        "update-b@example.com",
        "9876543216",
    )

    store_b = create_test_store(vendor_b, "Store B", "update-store-b")
    category = create_test_category()

    product_b = create_test_product(
        store_b,
        category,
        "Original Product",
        "original-product",
        "SKU-ORIGINAL",
    )

    db.session.commit()

    response = client.patch(
        f"{PRODUCT_URL}/{product_b.id}",
        headers=vendor_headers(vendor_a),
        json={"product_name": "Unauthorized Update"},
    )

    assert response.status_code == 404

    db.session.refresh(product_b)
    assert product_b.product_name == "Original Product"


def test_vendor_cannot_delete_another_vendors_product(client):
    vendor_a = create_test_vendor(
        "delete-a@example.com",
        "9876543217",
    )
    vendor_b = create_test_vendor(
        "delete-b@example.com",
        "9876543218",
    )

    store_b = create_test_store(vendor_b, "Store B", "delete-store-b")
    category = create_test_category()

    product_b = create_test_product(
        store_b,
        category,
        "Protected Product",
        "protected-product",
        "SKU-PROTECTED",
    )
    product_id = product_b.id

    db.session.commit()

    response = client.delete(
        f"{PRODUCT_URL}/{product_id}",
        headers=vendor_headers(vendor_a),
    )

    assert response.status_code == 404
    assert db.session.get(Product, product_id) is not None


def test_product_creation_without_image_returns_400(client):
    vendor = create_test_vendor(
        "create-no-image@example.com",
        "9876543219",
    )
    store = create_test_store(vendor, "Create Store", "create-store")
    category = create_test_category()

    form = valid_product_form(store, category)

    response = client.post(
        PRODUCT_URL,
        headers=vendor_headers(vendor),
        data=form,
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_product_creation_with_invalid_price_returns_400(client):
    vendor = create_test_vendor(
        "create-price@example.com",
        "9876543220",
    )
    store = create_test_store(vendor, "Price Store", "price-store")
    category = create_test_category()

    form = valid_product_form(store, category)
    form["price"] = "0"

    response = client.post(
        PRODUCT_URL,
        headers=vendor_headers(vendor),
        data=form,
        content_type="multipart/form-data",
    )

    # Route checks for an image before calling create_product.
    assert response.status_code == 400
    assert "image" in response.get_json()["message"].lower()


def test_product_creation_rejects_another_vendors_store(client):
    vendor_a = create_test_vendor(
        "foreign-store-a@example.com",
        "9876543221",
    )
    vendor_b = create_test_vendor(
        "foreign-store-b@example.com",
        "9876543222",
    )

    store_b = create_test_store(
        vendor_b, "Foreign Store", "foreign-store"
    )
    category = create_test_category()

    form = valid_product_form(store_b, category)

    response = client.post(
        PRODUCT_URL,
        headers=vendor_headers(vendor_a),
        data={
            **form,
            "images": (
                BytesIO(b"fake-image-data"),
                "test.jpg",
            ),
        },
        content_type="multipart/form-data",
    )

    # Ownership check happens before the image is saved.
    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_product_listing_rejects_invalid_store_id(client):
    vendor = create_test_vendor(
        "bad-filter@example.com",
        "9876543223",
    )

    response = client.get(
        f"{PRODUCT_URL}?store_id=not-a-number",
        headers=vendor_headers(vendor),
    )

    assert response.status_code == 400



def test_product_creation_with_invalid_price_returns_400(app, client):
    with app.app_context():
        vendor = create_test_vendor(
            "price-test@example.com",
            "9876500011"
        )
        db.session.add(vendor)
        db.session.commit()

        store = create_test_store(
            vendor,
            "Price Test Store",
            "price-test-store"
        )
        category = create_test_category()

        db.session.add_all([store, category])
        db.session.commit()

        data = valid_product_form(store, category)
        data["price"] = "0"

        headers = vendor_headers(vendor)

        response = client.post(
            PRODUCT_URL,
            data={
                **data,
                "images": (
                    BytesIO(b"fake-image-data"),
                    "product.jpg"
                ),
            },
            headers=headers,
            content_type="multipart/form-data",
        )

        assert response.status_code == 400

def test_product_creation_with_valid_image_returns_201(app, client):
    import os

    from PIL import Image

    with app.app_context():
        vendor = create_test_vendor(
            "image-test@example.com",
            "9876500012"
        )
        db.session.add(vendor)
        db.session.commit()

        store = create_test_store(
            vendor,
            "Image Test Store",
            "image-test-store"
        )
        category = create_test_category()

        db.session.add_all([store, category])
        db.session.commit()

        headers = vendor_headers(vendor)
        data = valid_product_form(store, category)

    image_buffer = BytesIO()
    Image.new("RGB", (10, 10), color="white").save(
        image_buffer,
        format="JPEG"
    )
    image_buffer.seek(0)

    response = client.post(
        PRODUCT_URL,
        data={
            **data,
            "images": (image_buffer, "test-product.jpg"),
        },
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    response_data = response.get_json()
    assert response_data["success"] is True

    product_data = response_data["data"]
    assert product_data["product_name"] == data["product_name"]
    assert len(product_data["images"]) == 1

    image_data = product_data["images"][0]
    assert image_data["is_primary"] is True
    assert image_data["image_url"].endswith(".jpg")

    # Confirm product and image records exist in the test database.
    with app.app_context():
        product = db.session.get(Product, product_data["id"])
        assert product is not None
        assert len(product.images) == 1

    # Remove the test upload from the filesystem.
    upload_folder = os.path.abspath(
        os.path.join(
            app.root_path,
            "..",
            "uploads",
            "products"
        )
    )

    filename = image_data["image_url"].rsplit("/", 1)[-1]
    uploaded_file = os.path.join(upload_folder, filename)

    if os.path.isfile(uploaded_file):
        os.remove(uploaded_file)
 