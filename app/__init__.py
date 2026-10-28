from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()
from config import Config
from app.extensions import db, migrate, jwt


def create_app(config_class=Config):

    # ==========================================
    # Create Flask Application
    # ==========================================
    app = Flask(__name__)

    # ==========================================
    # Load Configuration
    # ==========================================
    app.config.from_object(config_class)

    # ==========================================
    # Initialize Extensions
    # ==========================================
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # ==========================================
    # Register Database Models
    # ==========================================
    import tables

    # ==========================================
    # Register Authentication Routes
    # ==========================================
    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    # ==========================================
    # Register User Routes
    # ==========================================
    from routes.user_routes import user_bp
    app.register_blueprint(user_bp)

    # ==========================================
    # Register Payment Routes
    # ==========================================
    from routes.payment_routes import payment_bp
    app.register_blueprint(payment_bp)

    # ==========================================
    # Register Vendor Routes
    # ==========================================
    from routes.vendor_routes import vendor_bp
    app.register_blueprint(vendor_bp)

    # ==========================================
    # Register Admin Routes
    # ==========================================
    from routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    # ==========================================
    # Register Store Routes
    # ==========================================
    from routes.store_routes import store_bp
    app.register_blueprint(store_bp)

    # ==========================================
    # Register Product Routes
    # ==========================================
    from routes.product_routes import product_bp
    app.register_blueprint(product_bp)

    # ==========================================
    # Register Category Routes
    # ==========================================
    from routes.category_routes import category_bp
    app.register_blueprint(category_bp)

    # ==========================================
    # Register Cart Routes
    # ==========================================
    from routes.cart_routes import cart_bp
    app.register_blueprint(cart_bp)

    # ==========================================
    # Register Order Routes
    # ==========================================
    from routes.order_routes import order_bp
    app.register_blueprint(order_bp)

    # ==========================================
    # Register Address Routes
    # ==========================================
    from routes.address_routes import address_bp
    app.register_blueprint(address_bp)

    # ==========================================
    # Register Review Routes
    # ==========================================
    from routes.review_routes import review_bp
    app.register_blueprint(review_bp)

    # ==========================================
    # Register Wishlist Routes
    # ==========================================
    from routes.wishlist_routes import wishlist_bp
    app.register_blueprint(wishlist_bp)

    # ==========================================
    # Register Subcategory Routes
    # ==========================================
    from routes.subcategory_routes import subcategory_bp
    app.register_blueprint(subcategory_bp)

    # ==========================================
    # Register Banner Routes
    # ==========================================
    from routes.banner_routes import banner_bp
    app.register_blueprint(banner_bp)

    # ==========================================
    # Register Inventory Routes
    # ==========================================
    from routes.inventory_routes import inventory_bp
    app.register_blueprint(inventory_bp)

    # ==========================================
    # Register Coupon Routes
    # ==========================================
    from routes.coupon_routes import coupon_bp
    app.register_blueprint(coupon_bp)

    # ==========================================
    # Register Commission Routes
    # ==========================================
    from routes.commission_routes import commission_bp
    app.register_blueprint(commission_bp)

    # ==========================================
    # Register Notification Routes
    # ==========================================
    from routes.notification_routes import notification_bp
    app.register_blueprint(notification_bp)

    # ==========================================
    # Main API Route
    # ==========================================
    @app.route("/", methods=["GET"])
    def home():
        """
        Check API Status.
        ---
        tags:
          - General
        responses:
          200:
            description: API is running successfully
        """
        return jsonify({
            "success": True,
            "message": "MultiVendor E-Commerce API is running.",
            "version": "v1",
        }), 200

    # ==========================================
    # Health Check
    # ==========================================
    @app.route("/health", methods=["GET"])
    def health_check():
        """
        Check Application Health.
        ---
        tags:
          - General
        responses:
          200:
            description: Application is healthy
        """
        return jsonify({
            "success": True,
            "status": "healthy",
            "message": "Application is running.",
        }), 200

    # ==========================================
    # Return Flask Application
    # ==========================================
    return app
 
