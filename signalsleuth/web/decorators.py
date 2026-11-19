"""Access-control decorators for student, admin and token-authenticated routes."""
from functools import wraps

from flask import flash, jsonify, redirect, request, session, url_for

from ..services.tokens import user_from_token


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session or session.get("role") == "admin":
            flash("Please log in with your student account.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapped


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "admin_id" not in session:
            flash("Admin login required.", "warning")
            return redirect(url_for("admin_auth.admin_login"))
        # Factory password still in use: only the change-password page is allowed.
        if session.get("admin_must_change_password") and request.endpoint != "admin_auth.admin_change_password":
            flash("Please change the default admin password first.", "warning")
            return redirect(url_for("admin_auth.admin_change_password"))
        return f(*args, **kwargs)
    return wrapped


def api_login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        user = user_from_token()
        if not user:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        request.mobile_user = user
        return f(*args, **kwargs)
    return wrapped
