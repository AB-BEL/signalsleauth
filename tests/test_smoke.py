"""End-to-end smoke tests: every page renders, access control works, health/cron behave."""
import pytest

from signalsleuth import config, db


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True and body["database"] == "up"


def test_health_reports_database_down(client, monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: (False, "boom"))
    r = client.get("/api/health")
    assert r.status_code == 503
    assert r.get_json()["database"] == "down"
    assert "boom" not in r.get_data(as_text=True)  # no internal details leaked


def test_cron_requires_secret(client, monkeypatch):
    monkeypatch.setattr(config, "CRON_SECRET", "s3cret")
    assert client.get("/api/cron/weekly-snapshot").status_code == 401
    assert client.get("/api/cron/weekly-snapshot", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get("/api/cron/weekly-snapshot", headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200 and ok.get_json()["ok"] is True


def test_cron_disabled_without_secret(client, monkeypatch):
    monkeypatch.setattr(config, "CRON_SECRET", "")
    assert client.get("/api/cron/weekly-snapshot", headers={"Authorization": "Bearer "}).status_code == 401


def test_public_pages(client):
    for path in ["/", "/login", "/register", "/forgot-password", "/legacy-game"]:
        assert client.get(path).status_code == 200, path


def test_protected_pages_redirect_to_login(client):
    for path in ["/dashboard", "/rankings", "/play/1"]:
        r = client.get(path)
        assert r.status_code == 302 and "/login" in r.headers["Location"], path
    r = client.get("/admin")
    assert r.status_code == 302 and "/admin/login" in r.headers["Location"]
    assert client.get("/api/me").status_code == 401


def test_default_admin_password_must_be_changed(app, client):
    row = _admin_id()
    db.update_admin_password(row, db.DEFAULT_ADMIN_PASS)  # reset to factory state
    r = client.post("/admin/login", data={"username": "admin", "password": db.DEFAULT_ADMIN_PASS})
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/change-password")
    # everything else is blocked until the password is changed
    assert client.get("/admin").headers["Location"].endswith("/admin/change-password")
    assert client.post("/admin/change-password", data={"new_password": "admin123"}).status_code == 200  # rejected
    r = client.post("/admin/change-password", data={"new_password": "Str0ng-Pass!"})
    assert r.status_code == 302
    assert client.get("/admin").status_code == 200
    assert db.admin_uses_default_password(row) is False
    db.update_admin_password(row, db.DEFAULT_ADMIN_PASS)  # leave DB as we found it


def _admin_id():
    with db.get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id FROM admins WHERE username = 'admin'")
            return c.fetchone()["id"]


def _simple_get_rules(app):
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and not rule.arguments and rule.endpoint != "static":
            yield rule


def test_every_admin_page_renders(app, admin_client):
    skipped = {"/admin/logout"}
    for rule in _simple_get_rules(app):
        if not rule.rule.startswith("/admin") or rule.rule in skipped:
            continue
        r = admin_client.get(rule.rule)
        assert r.status_code < 500, f"{rule.rule} -> {r.status_code}"


def test_student_flow(app, student, game_uploaded):
    c, email, password, uid = student
    for path in ["/dashboard", "/rankings", "/change-password", "/chapter-feedback-pdf/1", f"/api/my-scores/1"]:
        assert c.get(path).status_code in (200, 302), path
    r = c.post("/api/submit-score", json={"chapter_num": 1, "level_num": 1,
                                          "answers": [{"q_index": 1, "answer": "nyquist sampling"}]})
    assert r.status_code in (200, 403)
    assert c.get("/logout").status_code in (200, 302)
    assert c.get("/dashboard").status_code == 302


def test_mobile_token_api(app, student, game_uploaded):
    c, email, password, uid = student
    api = app.test_client()
    r = api.post("/api/auth/login", json={"email": email, "password": password})
    token = r.get_json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    for path in ["/api/me", "/api/dashboard", "/api/rankings", "/api/chapter/1/play-info", "/api/chapter/1/game-package"]:
        assert api.get(path, headers=h).status_code == 200, path
    assert api.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_game_file_injects_bridge_and_token(app, admin_client, student):
    import io
    from signalsleuth import db as _db

    c, email, password, uid = student
    html = b"<html><head></head><body>game</body></html>"
    r = admin_client.post("/admin/chapter/1/upload-game",
                          data={"game_file": (io.BytesIO(html), "t_game.html")},
                          content_type="multipart/form-data")
    assert r.status_code == 302
    page = c.get("/game-file/1")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "signalsleuth-game-bridge.js" in body and "SS_TOKEN" in body
    from signalsleuth.services import storage
    storage.delete_game_file((_db.get_chapter(1) or {}).get("game_filename"))
    _db.set_chapter_game_file(1, None)  # restore


def test_bundled_game_readable_without_writable_disk():
    from signalsleuth.services import storage
    assert storage.game_file_exists("chapter_1_SignalSleuth_Chapter1.html")
    assert len(storage.load_game_bytes("chapter_1_SignalSleuth_Chapter1.html")) > 1000


def test_secret_key_required_in_production(monkeypatch):
    from signalsleuth import create_app
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    monkeypatch.setattr(config, "SECRET_KEY", "")
    with pytest.raises(RuntimeError):
        create_app()


def test_ssl_options(monkeypatch):
    from signalsleuth.db import core
    monkeypatch.delenv("MYSQL_SSL", raising=False)
    assert core._ssl_kwargs() == {}
    monkeypatch.setenv("MYSQL_SSL", "1")
    kw = core._ssl_kwargs()
    assert kw["ssl_verify_cert"] and kw["ssl_verify_identity"] and kw.get("ssl_ca")


def test_login_is_throttled_after_repeated_failures(app, client):
    from signalsleuth.services import throttle

    throttle.reset_all()
    codes = [client.post("/login", data={"email": "nobody@example.com", "password": f"bad{i}"}).status_code
             for i in range(throttle.MAX_FAILURES + 2)]
    assert codes[0] == 200 and codes[-1] == 429
    # a different account is not affected
    assert client.post("/login", data={"email": "other@example.com", "password": "x"}).status_code == 200
    throttle.reset_all()


def test_mobile_login_does_not_leak_internal_errors(app, client, monkeypatch):
    from signalsleuth import db

    def boom(*a, **k):
        raise RuntimeError("secret-db-host.internal exploded")

    monkeypatch.setattr(db, "verify_user", boom)
    r = client.post("/api/auth/login", json={"email": "a@b.c", "password": "x"})
    assert r.status_code == 500
    assert "secret-db-host" not in r.get_data(as_text=True)


def test_session_cookie_secure_flag_follows_config(monkeypatch):
    import importlib
    from signalsleuth import config

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "0")
    importlib.reload(config)
    assert config.IS_PRODUCTION and config.SESSION_COOKIE_SECURE is False
    monkeypatch.delenv("SESSION_COOKIE_SECURE")
    importlib.reload(config)
    assert config.SESSION_COOKIE_SECURE is True
    monkeypatch.delenv("APP_ENV")
    importlib.reload(config)


def test_origin_guard_blocks_tunnel_traffic_without_secret(client, monkeypatch):
    from signalsleuth import config

    monkeypatch.setattr(config, "ORIGIN_SECRET", "s3cret-value")
    # direct LAN/local request: allowed
    assert client.get("/api/health").status_code == 200
    # looks like it came through a tunnel, no secret: blocked
    assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.7"}).status_code == 403
    assert client.get("/api/health", headers={"CF-Connecting-IP": "198.51.100.7"}).status_code == 403
    # wrong secret: blocked
    assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.7", "X-Origin-Secret": "nope"}).status_code == 403
    # correct secret (what the Vercel proxy project sends): allowed
    ok = client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.7", "X-Origin-Secret": "s3cret-value"})
    assert ok.status_code == 200


def test_origin_guard_off_when_no_secret(client, monkeypatch):
    from signalsleuth import config

    monkeypatch.setattr(config, "ORIGIN_SECRET", "")
    assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.7"}).status_code == 200


def test_throttle_is_per_client_ip_behind_the_front(app, client, monkeypatch):
    from signalsleuth import config
    from signalsleuth.services import throttle

    monkeypatch.setattr(config, "ORIGIN_SECRET", "s3cret-value")
    throttle.reset_all()

    def attempt(ip):
        return client.post("/login", data={"email": "who@example.com", "password": "bad"},
                           headers={"X-Origin-Secret": "s3cret-value", "X-Client-IP": ip}).status_code

    codes = [attempt("203.0.113.1") for _ in range(throttle.MAX_FAILURES + 1)]
    assert codes[-1] == 429
    assert attempt("203.0.113.2") == 200  # another visitor is not locked out
    throttle.reset_all()


def test_mobile_path_without_slash_does_not_redirect(client):
    # behind the Vercel proxy a missing trailing slash must not cause a redirect loop
    for path in ("/m", "/m/"):
        assert client.get(path).status_code in (200, 404)
