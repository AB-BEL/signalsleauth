"""Administrator login, logout and password change."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from .. import db
from ..web.decorators import admin_required
from ..services import throttle

bp = Blueprint("admin_auth", __name__)


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        wait = throttle.seconds_blocked("admin", username)
        if wait:
            flash(f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s).", "danger")
            return render_template("admin_login.html"), 429
        admin = db.verify_admin(username, request.form.get("password", ""))
        if admin:
            throttle.record_success("admin", username)
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_user"] = admin["username"]
            session["role"] = "admin"
            if db.admin_uses_default_password(admin["id"]):
                # Factory password still in use: force a change before anything else.
                session["admin_must_change_password"] = True
                flash("You are using the default admin password. Choose a new one to continue.", "warning")
                return redirect(url_for("admin_auth.admin_change_password"))
            flash("Admin logged in.", "success")
            return redirect(url_for("admin_system.admin_dashboard"))
        throttle.record_failure("admin", username)
        flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")


@bp.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("main.index"))


@bp.route("/admin/change-password", methods=["GET", "POST"])
@admin_required
def admin_change_password():
    if request.method == "POST":
        new = request.form.get("new_password", "")
        if len(new) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif new == db.DEFAULT_ADMIN_PASS:
            flash("Please choose a password different from the default one.", "danger")
        else:
            db.update_admin_password(session["admin_id"], new)
            session.pop("admin_must_change_password", None)
            flash("Admin password updated.", "success")
            return redirect(url_for("admin_system.admin_dashboard"))
    return render_template(
        "admin_change_password.html",
        forced=bool(session.get("admin_must_change_password")),
    )
