"""Key/value application settings."""
from datetime import datetime
from .core import utcnow
from .core import get_conn
from .schema import ensure_architecture_tables


def get_setting(key, default=None):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT setting_value FROM system_settings WHERE setting_key=%s", (key,))
            row = c.fetchone()
            return row["setting_value"] if row else default


def set_setting(key, value):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO system_settings (setting_key, setting_value, updated_at)
                   VALUES (%s,%s,%s)
                   ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value), updated_at=VALUES(updated_at)""",
                (key, str(value), utcnow()),
            )
