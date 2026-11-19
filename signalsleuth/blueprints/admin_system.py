"""Admin: dashboard, branding/settings, security, backup and storage status."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from .. import db
from ..services import storage, monetization
from ..web.decorators import admin_required

bp = Blueprint("admin_system", __name__)


@bp.route("/admin")
@admin_required
def admin_dashboard():
    try:
        db.ensure_architecture_tables()
    except Exception as e:
        print("architecture tables:", e)
    stats = db.admin_dashboard_stats()
    season = db.get_season()
    try:
        db.log_admin_activity(session.get("admin_id"), "dashboard_view", ip=request.remote_addr)
    except Exception:
        pass
    return render_template(
        "admin_module_dashboard.html",
        module="dashboard",
        stats=stats,
        season=season,
    )


@bp.route("/admin/storage-status")
@admin_required
def admin_storage_status():
    return jsonify({"ok": True, "storage": storage.storage_status()})


@bp.route("/admin/settings")
@admin_required
def admin_module_settings():
    return render_template(
        "admin_module_settings.html",
        module="settings",
        season=db.get_season(),
        pass_percent=db.get_setting("pass_percent", "50"),
        arch_ver=db.get_setting("architecture_version", "2.0"),
        app_name=db.get_setting("app_name", "Signal Sleuth"),
        course_name=db.get_setting("course_name", "Your course"),
        ads_enabled=monetization.ads_enabled(),
    )


@bp.route("/admin/settings/branding", methods=["POST"])
@admin_required
def admin_save_branding():
    db.set_setting("app_name", (request.form.get("app_name") or "Signal Sleuth").strip()[:120])
    db.set_setting("course_name", (request.form.get("course_name") or "Your course").strip()[:200])
    db.log_admin_activity(session.get("admin_id"), "branding_update", request.remote_addr)
    flash("Branding updated. Platform stays course-agnostic (HTML games + question bank).", "success")
    return redirect(url_for("admin_system.admin_module_settings"))


@bp.route("/admin/security")
@admin_required
def admin_module_security():
    return render_template(
        "admin_module_security.html",
        module="security",
        activity=db.list_admin_activity(80),
    )


@bp.route("/admin/backup")
@admin_required
def admin_module_backup():
    return render_template(
        "admin_module_backup.html",
        module="backup",
        storage=storage.storage_status(),
    )
