"""Admin: season, chapters, deadlines, game uploads and chapter modules."""
import os
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from .. import db
from ..services import storage
from ..web.decorators import admin_required
from ..constants import ALLOWED_GAME_EXT
from werkzeug.utils import secure_filename

bp = Blueprint("admin_chapters", __name__)


@bp.route("/admin/season", methods=["POST"])
@admin_required
def admin_season():
    db.set_season(
        request.form.get("name", "Season"),
        request.form.get("start_date", ""),
        request.form.get("end_date", ""),
    )
    flash("Season dates updated.", "success")
    return redirect(url_for("admin_system.admin_dashboard"))


@bp.route("/admin/chapter/<int:num>/toggle", methods=["POST"])
@admin_required
def admin_toggle_chapter(num):
    chapters = {c["chapter_num"]: c for c in db.list_chapters()}
    ch = chapters.get(num)
    if ch:
        db.set_chapter_active(num, not ch["is_active"])
        flash(f"Chapter {num} {'activated' if not ch['is_active'] else 'deactivated'}.", "success")
    return redirect(url_for("admin_chapters.admin_module_chapters"))


@bp.route("/admin/chapter/<int:num>/deadline", methods=["POST"])
@admin_required
def admin_chapter_deadline(num):
    start = request.form.get("start_date", "").strip()
    end = request.form.get("end_date", "").strip()
    db.set_chapter_deadline(num, start, end)
    flash(f"Chapter {num} deadline set: {start or '—'} → {end or '—'}.", "success")
    return redirect(url_for("admin_chapters.admin_module_chapters"))


@bp.route("/admin/chapter/<int:num>/upload-game", methods=["POST"])
@admin_required
def admin_upload_game(num):
    f = request.files.get("game_file")
    if not f or not f.filename:
        flash("No file selected.", "danger")
        return redirect(url_for("admin_system.admin_dashboard"))
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_GAME_EXT:
        flash("Only .html / .htm game files are allowed.", "danger")
        return redirect(url_for("admin_system.admin_dashboard"))
    safe = secure_filename(f"chapter_{num}_{f.filename}")
    if not safe.lower().endswith((".html", ".htm")):
        safe = f"chapter_{num}.html"
    ch = db.get_chapter(num)
    # Remove previous package (local and/or object storage)
    if ch and ch.get("game_filename") and ch["game_filename"] != safe:
        try:
            storage.delete_game_file(ch["game_filename"])
        except Exception as e:
            print("delete old game:", e)
    try:
        storage.save_game_file(safe, f.stream)
    except Exception as e:
        flash(f"Upload storage failed: {e}", "danger")
        return redirect(url_for("admin_system.admin_dashboard"))
    db.set_chapter_game_file(num, safe)
    try:
        db.record_game_version(num, safe, admin_id=session.get("admin_id"), notes="admin upload")
        db.log_admin_activity(session.get("admin_id"), "game_upload", f"chapter {num}: {safe}", request.remote_addr)
        db.log_audit("admin", session.get("admin_id"), "game_upload", "chapter", num, safe)
    except Exception as e:
        print("version log:", e)
    # Auto-activate when a game is uploaded (admin can still deactivate)
    if ch and not ch.get("is_active"):
        db.set_chapter_active(num, True)
    flash(f"Chapter {num} game uploaded: {safe}", "success")
    return redirect(url_for("admin_system.admin_dashboard"))


@bp.route("/admin/chapter-title", methods=["POST"])
@admin_required
def admin_set_chapter_title():
    n = int(request.form.get("chapter_num", 0) or 0)
    title = request.form.get("title", "").strip()
    if n < 1 or n > 10:
        flash("Invalid chapter.", "danger")
    else:
        db.set_chapter_title(n, title)
        flash(f"Chapter {n} title set to: {title or n}", "success")
    return redirect(url_for("admin_chapters.admin_module_chapters"))


@bp.route("/admin/chapters")
@admin_required
def admin_module_chapters():
    return render_template(
        "admin_module_chapters.html",
        module="chapters",
        chapters=db.list_chapters(),
    )


@bp.route("/admin/games")
@admin_required
def admin_module_games():
    return render_template(
        "admin_module_games.html",
        module="games",
        chapters=db.list_chapters(),
        versions=db.list_game_versions(),
        storage=storage.storage_status(),
    )


@bp.route("/admin/levels")
@admin_required
def admin_module_levels():
    return render_template("admin_module_levels.html", module="levels")
