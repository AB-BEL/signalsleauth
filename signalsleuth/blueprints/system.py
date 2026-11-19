"""Operational endpoints: health check and scheduled jobs (no user session)."""
import hmac

from flask import Blueprint, jsonify, request

from .. import config, db
from ..services import storage

bp = Blueprint("system", __name__)


@bp.route("/api/health")
def api_health():
    """Liveness + database check. Returns 503 when the database is unreachable."""
    ok, err = db.ping()
    if not ok:
        print("Health check: database unreachable:", err)
    body = {
        "ok": ok,
        "service": "SignalSleuth",
        "mobile": True,
        "database": "up" if ok else "down",
        "storage": storage.backend_name(),
    }
    return jsonify(body), (200 if ok else 503)


@bp.route("/api/cron/weekly-snapshot")
def cron_weekly_snapshot():
    """Idempotent ranking snapshots. Called by Vercel Cron (or any scheduler).

    Protected by CRON_SECRET: the caller must send ``Authorization: Bearer <secret>``.
    Vercel Cron adds this header automatically when CRON_SECRET is set.
    """
    expected = f"Bearer {config.CRON_SECRET}"
    given = request.headers.get("Authorization", "")
    if not config.CRON_SECRET or not hmac.compare_digest(given, expected):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    db.ensure_weekly_snapshot()
    db.ensure_final_snapshot()
    return jsonify({"ok": True})
