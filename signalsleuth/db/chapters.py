"""Season, chapters, deadlines and game version history."""
from datetime import datetime
from .core import utcnow
from .core import as_date, get_conn
from .schema import ensure_architecture_tables


def get_season():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM season WHERE id = 1")
            return c.fetchone() or {}


def set_season(name, start_date, end_date):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE season SET name = %s, start_date = %s, end_date = %s, updated_at = %s WHERE id = 1",
                (name, start_date or None, end_date or None, utcnow()),
            )


def season_is_active():
    s = get_season()
    if not s or not s.get("start_date") or not s.get("end_date"):
        return True
    today = utcnow().date()
    start = as_date(s.get("start_date"))
    end = as_date(s.get("end_date"))
    if not start or not end:
        return True
    return start <= today <= end


def season_has_ended():
    s = get_season()
    if not s or not s.get("end_date"):
        return False
    end = as_date(s.get("end_date"))
    if not end:
        return False
    return utcnow().date() > end


def list_chapters():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM chapters ORDER BY chapter_num")
            return c.fetchall()


def get_chapter(chapter_num):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM chapters WHERE chapter_num = %s", (chapter_num,))
            return c.fetchone()


def set_chapter_active(chapter_num, active):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE chapters SET is_active = %s, activated_at = %s WHERE chapter_num = %s",
                (1 if active else 0, utcnow() if active else None, chapter_num),
            )


def set_chapter_deadline(chapter_num, start_date, end_date):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE chapters SET start_date = %s, end_date = %s WHERE chapter_num = %s",
                (start_date or None, end_date or None, chapter_num),
            )


def set_chapter_game_file(chapter_num, filename):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE chapters SET game_filename = %s, game_uploaded_at = %s WHERE chapter_num = %s",
                (filename, utcnow(), chapter_num),
            )


def is_chapter_active(chapter_num):
    ch = get_chapter(chapter_num)
    return bool(ch and ch["is_active"])


def chapter_within_deadline(chapter_num):
    ch = get_chapter(chapter_num)
    if not ch:
        return False
    today = utcnow().date()
    start = as_date(ch.get("start_date"))
    end = as_date(ch.get("end_date"))
    if start and today < start:
        return False
    if end and today > end:
        return False
    return True


def set_chapter_title(chapter_num, title):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE chapters SET title = %s WHERE chapter_num = %s",
                ((title or "").strip() or f"Chapter {chapter_num}", chapter_num),
            )
    return get_chapter(chapter_num)


def record_game_version(chapter_num, filename, admin_id=None, notes="", status="published"):
    ensure_architecture_tables()
    label = utcnow().strftime("%Y%m%dT%H%M%S")
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO game_versions
                   (chapter_num, version_label, filename, storage_key, status, notes, uploaded_by_admin_id, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (chapter_num, label, filename, filename, status, notes, admin_id, utcnow()),
            )
            return c.lastrowid


def list_game_versions(chapter_num=None, limit=50):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            if chapter_num is not None:
                c.execute(
                    """SELECT * FROM game_versions WHERE chapter_num=%s
                       ORDER BY created_at DESC LIMIT %s""",
                    (chapter_num, limit),
                )
            else:
                c.execute(
                    "SELECT * FROM game_versions ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            return c.fetchall()
