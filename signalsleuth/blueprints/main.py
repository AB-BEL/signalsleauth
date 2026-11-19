"""Public landing page and the legacy standalone Chapter 1 game."""
from flask import Blueprint, redirect, render_template, send_from_directory, session, url_for
from .. import db
from ..config import GAMES_DIR

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("student.dashboard"))
    if session.get("admin_id"):
        return redirect(url_for("admin_system.admin_dashboard"))
    return render_template("index.html", season=db.get_season())


@bp.route("/legacy-game")
def legacy_game():
    return send_from_directory(str(GAMES_DIR), "SignalSleuth_Chapter1.html")
