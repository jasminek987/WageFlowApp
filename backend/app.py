# app.py
import os
import sys
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Ensure backend root (where db.py lives) is importable
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def create_app() -> Flask:
    load_dotenv()  # loads DATABASE_URL, JWT_SECRET, HOST, PORT, etc.
    app = Flask(__name__)

    # Accept both with/without trailing slash (prevents 308s that break CORS)
    app.url_map.strict_slashes = False

    # CORS for Angular dev server
    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:4200", "http://127.0.0.1:4200"]}},
        supports_credentials=True,
        expose_headers=["Authorization", "Content-Type"],
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Health checks
    @app.get("/api/ping")
    def ping():
        return jsonify({"ok": True})

    @app.get("/api/health")
    def health():
        return jsonify({"status": "up"})

    # Blueprints
    from src.routes.auth import auth_bp
    from src.routes.employees import employees_bp
    from src.routes.timesheets import timesheets_bp
    from src.routes.payslips import payslips_bp

    app.register_blueprint(auth_bp,        url_prefix="/api/auth")
    app.register_blueprint(employees_bp,   url_prefix="/api/employees")
    app.register_blueprint(timesheets_bp,  url_prefix="/api/timesheets")
    app.register_blueprint(payslips_bp,    url_prefix="/api/payslips")

    # Debug helper to see routes from the browser
    @app.get("/api/debug/routes")
    def debug_routes():
        routes = []
        for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
            methods = sorted(m for m in r.methods if m not in {"HEAD", "OPTIONS"})
            routes.append({"methods": methods, "rule": r.rule})
        return jsonify(routes)

    # JSON errors
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "server_error"}), 500

    return app



if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5050"))

    app = create_app()

    print("=== Registered routes ===")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ",".join(sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"}))
        print(f"{methods:15s} {rule.rule}")
    print("=========================")

    print(f"Starting Flask on http://{host}:{port}")
    app.run(host=host, port=port, debug=True, use_reloader=False)

