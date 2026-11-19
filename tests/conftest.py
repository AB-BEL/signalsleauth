"""Test fixtures. Tests need a MySQL database (use a throw-away one!).

    export MYSQL_HOST=127.0.0.1 MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=signalsleuth_test
    pip install pytest && pytest -q
"""
import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SECRET_KEY", "test-secret-key")


@pytest.fixture(scope="session")
def app():
    from signalsleuth import create_app, db

    ok, err = db.ping()
    if not ok:
        pytest.skip(f"MySQL not reachable: {err}")
    db.init_db()
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(app):
    """Logged-in admin with the default password already replaced."""
    from signalsleuth import db

    admin = db.verify_admin("admin", "admin123") or {}
    c = app.test_client()
    with c.session_transaction() as s:
        row = _admin_row()
        s["admin_id"] = row["id"]
        s["admin_user"] = row["username"]
        s["role"] = "admin"
    return c


def _admin_row():
    from signalsleuth import db

    with db.get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id, username FROM admins WHERE username = %s", (db.DEFAULT_ADMIN_USER,))
            return c.fetchone()


@pytest.fixture()
def student(app):
    """A freshly registered student: returns (client, email, password, user_id)."""
    from signalsleuth import db

    sid = "T" + uuid.uuid4().hex[:8].upper()
    email = f"{sid.lower()}@example.com"
    db.add_pre_user_one(sid, "Test Student", "F")
    ok, msg = db.register_user(sid, email, "secret12", "Test Student", sid)
    assert ok, msg
    c = app.test_client()
    r = c.post("/login", data={"email": email, "password": "secret12"})
    assert r.status_code == 302
    user = db.get_user_by_email(email)
    return c, email, "secret12", user["id"]


@pytest.fixture()
def game_uploaded(app):
    """Chapter 1 has an uploaded game (students cannot enter a chapter without one)."""
    from signalsleuth import db
    from signalsleuth.services import storage

    storage.save_game_file("t_game.html", b"<html><head></head><body>game</body></html>")
    db.set_chapter_game_file(1, "t_game.html")
    yield "t_game.html"
    ch = db.get_chapter(1) or {}
    for name in {"t_game.html", ch.get("game_filename")}:
        if name:
            storage.delete_game_file(name)
    db.set_chapter_game_file(1, None)
