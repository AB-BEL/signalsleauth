"""Student registration, login, logout and password management."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from .. import db
from ..web.decorators import login_required
from ..services.mailer import send_email
from ..services import throttle

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        sid = request.form.get("student_id", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        campus_id = request.form.get("campus_id", "").strip() or sid
        if not sid:
            flash("Student ID is required to check eligibility.", "danger")
        elif not full_name:
            flash("Full name is required.", "danger")
        elif not email:
            flash("Email is required.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        else:
            ok, msg = db.register_user(sid, email, password, full_name, campus_id)
            flash(msg, "success" if ok else "danger")
            if ok:
                send_email(
                    email,
                    "Signal Sleuth — registration confirmed",
                    f"Welcome to Signal Sleuth.\n\n{msg}\n\nSign in with your email and password.\n"
                    f"Your username is shown on your dashboard and in the league table.\n",
                )
                return redirect(url_for("auth.login"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        wait = throttle.seconds_blocked("student", email)
        if wait:
            flash(f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s).", "danger")
            return render_template("login.html"), 429
        user = db.verify_user(email, request.form.get("password", ""))
        if user:
            throttle.record_success("student", email)
            # Isolate this player completely from any previous session
            session.clear()
            session.permanent = True
            session["user_id"] = int(user["id"])
            session["student_id"] = user["student_id"]
            session["email"] = user["email"]
            session["username"] = user.get("generated_username") or user["student_id"]
            session["role"] = "student"
            session.modified = True
            flash(f"Welcome, {session['username']}! This is your personal dashboard.", "success")
            resp = redirect(url_for("student.dashboard"))
            # Bust any intermediary cache
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            return resp
        throttle.record_failure("student", email)
        flash("Invalid email or password.", "danger")
    # If already logged in as student, go to their dashboard
    if session.get("user_id") and session.get("role") == "student":
        return redirect(url_for("student.dashboard"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    # Small page clears browser localStorage game keys, then leaves
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Logging out…</title></head>"
        "<body><p>Logging out…</p><script>"
        "try {"
        "  var keys = [];"
        "  for (var i = 0; i < localStorage.length; i++) keys.push(localStorage.key(i));"
        "  keys.forEach(function(k) {"
        "    if (k && (k.indexOf('signalSleuth') === 0 || k.indexOf('ss_ch') === 0 || k.indexOf('ss_token') === 0))"
        "      localStorage.removeItem(k);"
        "  });"
        "  sessionStorage.clear();"
        "} catch (e) {}"
        "location.replace('/');"
        "</script></body></html>"
    )


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        ok, msg = db.request_password_reset(request.form.get("email", ""))
        flash(msg, "success" if ok else "danger")
        return redirect(url_for("auth.login"))
    return render_template("forgot_password.html")


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        user = db.get_user(session["user_id"])
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        if not db.verify_user(user["email"], current):
            flash("Current password is incorrect.", "danger")
        elif len(new) < 6:
            flash("New password must be at least 6 characters.", "danger")
        else:
            db.update_user_password(user["id"], new)
            flash("Password updated.", "success")
            return redirect(url_for("student.dashboard"))
    return render_template("change_password.html")
