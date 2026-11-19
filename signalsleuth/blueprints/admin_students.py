"""Admin: student accounts, pre-registered IDs, password resets, re-registration approvals."""
import os
import secrets
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from .. import db
from ..web.decorators import admin_required
from ..services.mailer import send_email
from ..config import SEED_DIR

bp = Blueprint("admin_students", __name__)


@bp.route("/admin/upload-ids", methods=["POST"])
@admin_required
def admin_upload_ids():
    """Accept Excel (.xlsx) with Student_id, name, sex — or CSV / paste."""
    entries = []
    file = request.files.get("ids_file")
    paste = request.form.get("ids_text", "").strip()

    if file and file.filename:
        fname = file.filename.lower()
        if fname.endswith((".xlsx", ".xlsm")):
            try:
                from openpyxl import load_workbook
                wb = load_workbook(file, read_only=True, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    flash("Excel file is empty.", "danger")
                    return redirect(url_for("admin_students.admin_module_students"))
                header = [str(h or "").strip().lower().replace(" ", "_") for h in rows[0]]
                def col(*names):
                    for n in names:
                        n = n.lower().replace(" ", "_")
                        if n in header:
                            return header.index(n)
                    return None
                i_id = col("student_id", "studentid", "id", "campus_id", "campusid", "student_no", "student_number")
                i_name = col("name", "full_name", "fullname", "student_name")
                i_sex = col("sex", "gender")
                if i_id is None:
                    i_id, i_name, i_sex = 0, 1, 2
                for row in rows[1:]:
                    if not row:
                        continue
                    sid = row[i_id] if i_id is not None and i_id < len(row) else None
                    sid = db.normalize_student_id(sid)
                    if not sid:
                        continue
                    name = row[i_name] if i_name is not None and i_name < len(row) else ""
                    sex = row[i_sex] if i_sex is not None and i_sex < len(row) else ""
                    entries.append((sid, str(name or "").strip(), str(sex or "").strip()))
            except Exception as e:
                flash(f"Could not read Excel: {e}", "danger")
                return redirect(url_for("admin_students.admin_module_students"))
        else:
            raw = file.read().decode("utf-8", errors="ignore")
            paste = raw

    if paste and not entries:
        for line in paste.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                entries.append((parts[0], parts[1], parts[2]))
            elif len(parts) == 2:
                entries.append((parts[0], parts[1], ""))
            else:
                entries.append((parts[0], "", ""))

    if not entries:
        flash("No student rows found. Check Excel headers (Student_id, name, sex) or paste format.", "danger")
        return redirect(url_for("admin_students.admin_module_students"))
    added, skipped = db.add_pre_users(entries)
    sample = ", ".join(e[0] for e in entries[:5])
    flash(
        f"Uploaded: {added} new, {skipped} skipped (already exist). "
        f"Parsed {len(entries)} row(s). Sample IDs: {sample}",
        "success" if added or skipped else "warning",
    )
    return redirect(url_for("admin_students.admin_module_students"))


@bp.route("/admin/player/<int:user_id>")
@admin_required
def admin_player_scores(user_id):
    """Admin view of one player's unique scores (all chapters/levels)."""
    user = db.get_user(user_id)
    if not user:
        flash("Player not found.", "danger")
        return redirect(url_for("admin_system.admin_dashboard"))
    chapters = db.list_chapters()
    by_chapter = []
    for ch in chapters:
        n = ch["chapter_num"]
        levels = db.get_user_level_scores(user_id, n)
        prog = db.get_chapter_progress(user_id, n)
        locks = db.get_chapter_level_lock_map(user_id, n)
        by_chapter.append({
            "chapter": ch,
            "levels": levels,
            "progress": prog,
            "locks": locks,
        })
    final_score, weight_detail = db.user_weighted_final(user_id)
    rank, rank_score, total_players = db.get_user_current_rank(user_id)
    return render_template(
        "admin_player.html",
        player=user,
        by_chapter=by_chapter,
        final_score=final_score,
        weight_detail=weight_detail,
        rank=rank,
        total_players=total_players,
    )


@bp.route("/admin/user/delete/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    ok, msg = db.delete_user(user_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin_students.admin_module_students"))


@bp.route("/admin/user/add", methods=["POST"])
@admin_required
def admin_add_user():
    sid = request.form.get("student_id", "").strip()
    name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip() or "changeme"
    sex = request.form.get("sex", "").strip()
    if not sid or not email or not name:
        flash("Student ID, name, and email are required.", "danger")
        return redirect(url_for("admin_system.admin_dashboard"))
    # Ensure pre-listed
    if not db.pre_user_exists(sid):
        db.add_pre_user_one(sid, name, sex)
    ok, msg = db.register_user(sid, email, password, name, sid)
    flash(msg, "success" if ok else "danger")
    if ok:
        send_email(email, "Signal Sleuth — account created by admin",
                   f"An admin created your account.\nStudent ID: {sid}\nEmail: {email}\n"
                   f"Temporary password: {password}\n{msg}\nPlease log in and change your password.\n")
    return redirect(url_for("admin_system.admin_dashboard"))


@bp.route("/admin/pre-user/add", methods=["POST"])
@admin_required
def admin_add_pre_user():
    ok, msg = db.add_pre_user_one(
        request.form.get("student_id", ""),
        request.form.get("full_name", ""),
        request.form.get("sex", ""),
    )
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin_students.admin_module_students"))


@bp.route("/admin/pre-user/delete/<int:row_id>", methods=["POST"])
@admin_required
def admin_delete_pre_user(row_id):
    ok, msg = db.delete_pre_user_by_id(row_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin_system.admin_dashboard"))


@bp.route("/admin/pre-user/delete-by-sid", methods=["POST"])
@admin_required
def admin_delete_pre_user_sid():
    ok, msg = db.delete_pre_user(request.form.get("student_id", ""))
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin_system.admin_dashboard"))


@bp.route("/admin/seed-default-ids", methods=["POST"])
@admin_required
def admin_seed_default_ids():
    """Load bundled seed CSV (NaScR… list) into pre_users."""
    import csv
    seed = str(SEED_DIR / "pre_users_seed.csv")
    if not os.path.isfile(seed):
        flash("Seed file database/seed/pre_users_seed.csv not found.", "danger")
        return redirect(url_for("admin_students.admin_module_students"))
    entries = []
    with open(seed, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get("Student_id") or row.get("student_id") or ""
            name = row.get("name") or ""
            sex = row.get("sex") or ""
            if sid.strip():
                entries.append((sid.strip(), name.strip(), sex.strip()))
    added, skipped = db.add_pre_users(entries)
    flash(f"Seed list loaded: {added} new, {skipped} already present (total in file: {len(entries)}).", "success")
    return redirect(url_for("admin_students.admin_module_students"))


@bp.route("/admin/resolve-reset/<int:req_id>", methods=["POST"])
@admin_required
def admin_resolve_reset(req_id):
    temp = request.form.get("temp_password") or secrets.token_urlsafe(8)
    user = db.resolve_password_reset(req_id, temp)
    if user:
        sent = send_email(
            user["email"],
            "Signal Sleuth — temporary password",
            f"Hello {user.get('full_name') or user.get('generated_username')},\n\n"
            f"Your temporary password is: {temp}\n\n"
            f"Username: {user.get('generated_username')}\n"
            f"Sign in with your email and this password, then change it.\n",
            user_id=user["id"],
        )
        flash(
            f"Password reset for {user['email']} (username {user.get('generated_username')}). "
            f"Temporary password: {temp}. "
            + ("Email sent." if sent else "Email not configured — copy password to student."),
            "success",
        )
    else:
        flash("Could not resolve request.", "danger")
    return redirect(url_for("admin_system.admin_dashboard"))


@bp.route("/admin/approve-rereg/<int:req_id>", methods=["POST"])
@admin_required
def admin_approve_rereg(req_id):
    if db.approve_rereg(req_id):
        flash("Re-registration approved. Student chapter progress reset with re-reg flag.", "success")
    else:
        flash("Could not approve request.", "danger")
    return redirect(url_for("admin_system.admin_dashboard"))


@bp.route("/admin/students")
@admin_required
def admin_module_students():
    db.ensure_architecture_tables()
    return render_template(
        "admin_module_students.html",
        module="students",
        users=db.list_all_users(),
    )


@bp.route("/admin/user/<int:user_id>/suspend", methods=["POST"])
@admin_required
def admin_user_suspend(user_id):
    db.set_user_suspended(user_id, True)
    db.log_admin_activity(session.get("admin_id"), "user_suspend", str(user_id), request.remote_addr)
    flash("Student suspended.", "success")
    return redirect(url_for("admin_students.admin_module_students"))
