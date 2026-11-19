"""Signal Sleuth – multi-user educational game server (application package).

Use the factory::

    from signalsleuth import create_app
    app = create_app()

Layout
------
config.py        environment + paths
db/              MySQL data layer (one module per concern)
services/        storage, mail, tokens, pdf, monetization hooks
web/             decorators, template filters, request hooks
blueprints/      HTTP routes grouped by feature (student, admin_*, mobile_api, ...)
"""


def create_app():
    from flask import Flask

    from . import config

    config.validate()

    app = Flask(
        __name__,
        template_folder=str(config.TEMPLATES_DIR),
        static_folder=str(config.STATIC_DIR),
        static_url_path="/static",
    )
    app.secret_key = config.SECRET_KEY or config.DEV_SECRET_KEY
    app.config.update(
        SESSION_COOKIE_NAME="signalsleuth_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 12,  # 12 hours
        MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH,
    )

    # Writable upload cache (never fatal: the filesystem may be read-only).
    try:
        config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    from .web import hooks
    hooks.register(app)

    _init_cors(app)
    _init_database()

    from .blueprints import register_blueprints
    register_blueprints(app)
    return app


def _init_cors(app):
    try:
        from flask_cors import CORS
    except ImportError:
        print("WARNING: flask-cors not installed. Run: pip install flask-cors")
        return
    # origins="*" must NOT be combined with supports_credentials=True.
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )


def _init_database():
    from . import config, db

    mode = config.DB_INIT
    if mode == "never":
        return
    try:
        if mode == "always" or (mode == "auto" and not config.IS_VERCEL):
            db.init_db()
        else:
            db.ensure_initialized()
    except Exception as exc:  # the app still starts; /api/health reports the DB state
        print("Warning: database initialisation failed:", exc)
