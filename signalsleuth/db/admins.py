"""Admin accounts, activity log, audit log and dashboard statistics."""
from datetime import datetime
from .core import utcnow
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from .core import DEFAULT_ADMIN_PASS, get_conn
from .schema import ensure_architecture_tables


def verify_admin(username, password):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM admins WHERE username = %s", (username,))
            row = c.fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return row
    return None


def admin_uses_default_password(admin_id):
    """True while the admin still has the well-known factory password."""
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT password_hash FROM admins WHERE id = %s", (admin_id,))
            row = c.fetchone()
    return bool(row and check_password_hash(row["password_hash"], DEFAULT_ADMIN_PASS))


def update_admin_password(admin_id, new_password):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE admins SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new_password), admin_id),
            )


def log_admin_activity(admin_id, action, detail="", ip=None):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO admin_activity_logs (admin_id, action, detail, ip, created_at)
                   VALUES (%s,%s,%s,%s,%s)""",
                (admin_id, action, detail, ip, utcnow()),
            )


def log_audit(actor_type, actor_id, event_type, entity_type=None, entity_id=None, detail=""):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO audit_logs
                   (actor_type, actor_id, event_type, entity_type, entity_id, detail, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (actor_type, actor_id, event_type, entity_type,
                 str(entity_id) if entity_id is not None else None, detail, utcnow()),
            )


def admin_dashboard_stats():
    """Aggregate stats for admin Dashboard module."""
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) AS n FROM users")
            total = int((c.fetchone() or {}).get("n") or 0)
            c.execute(
                """SELECT COUNT(DISTINCT user_id) AS n FROM level_scores
                   WHERE updated_at >= (UTC_TIMESTAMP() - INTERVAL 7 DAY)"""
            )
            active = int((c.fetchone() or {}).get("n") or 0)
            c.execute("SELECT COUNT(*) AS n FROM chapter_progress WHERE passed=1")
            completions = int((c.fetchone() or {}).get("n") or 0)
            c.execute("SELECT AVG(overall_points) AS a FROM users")
            avg = float((c.fetchone() or {}).get("a") or 0)
            c.execute("SELECT COUNT(*) AS n FROM chapters WHERE is_active=1")
            active_ch = int((c.fetchone() or {}).get("n") or 0)
    return {
        "total_students": total,
        "active_students_7d": active,
        "chapter_completions": completions,
        "average_overall_score": round(avg, 2),
        "active_chapters": active_ch,
    }


def list_admin_activity(limit=100):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM admin_activity_logs ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return c.fetchall()
