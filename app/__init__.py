import os
from flask import Flask, send_from_directory
from .config import config
from .extensions import db, jwt, cors


def create_app(config_name: str = "development") -> Flask:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dir = os.path.join(base_dir, "frontend")

    app = Flask(
        __name__,
        static_folder=frontend_dir,
        template_folder=frontend_dir,
    )
    app.config.from_object(config[config_name])

    # ── Extensions ────────────────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # ── Blueprints ────────────────────────────────────────────────────────
    from .routes.auth import auth_bp
    from .routes.expenses import expenses_bp
    from .routes.dashboard import dashboard_bp
    from .routes.subscriptions import subscriptions_bp
    from .routes.rooms import rooms_bp
    from .routes.trips import trips_bp
    from .routes.analytics import analytics_bp
    from .routes.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(expenses_bp, url_prefix="/api/expenses")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(subscriptions_bp, url_prefix="/api/subscriptions")
    app.register_blueprint(rooms_bp, url_prefix="/api/rooms")
    app.register_blueprint(trips_bp, url_prefix="/api/trips")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    # ── Frontend SPA catch-all ────────────────────────────────────────────
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        full = os.path.join(frontend_dir, path)
        if path and os.path.exists(full):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, "index.html")

    # ── Create tables ────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()

    return app
