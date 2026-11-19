"""Chapter access rules and re-registration requests."""
from datetime import datetime
from .core import utcnow
from .core import get_conn
from .progress import get_chapter_progress
from .users import refresh_user_status_and_points
from .chapters import chapter_within_deadline, get_chapter, is_chapter_active


def user_can_access_chapter(user_id, chapter_num):
    if not is_chapter_active(chapter_num):
        return False, "This chapter is not activated yet."
    if not chapter_within_deadline(chapter_num):
        ch = get_chapter(chapter_num) or {}
        return False, f"Chapter {chapter_num} is outside its deadline."
    ch = get_chapter(chapter_num)
    if not ch or not ch.get("game_filename"):
        return False, "No game file has been uploaded for this chapter yet. Contact admin."
    if chapter_num == 1:
        return True, "ok"
    prev = get_chapter_progress(user_id, chapter_num - 1)
    if not prev or not prev["passed"]:
        return False, f"You must pass Chapter {chapter_num - 1} (score > 50%) before unlocking this chapter."
    return True, "ok"


def request_rereg(user_id, chapter_num):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT id FROM rereg_requests WHERE user_id = %s AND chapter_num = %s AND status = 'pending'",
                (user_id, chapter_num),
            )
            if c.fetchone():
                return False, "A re-registration request is already pending for this chapter."
            c.execute(
                "INSERT INTO rereg_requests (user_id, chapter_num, status, created_at) VALUES (%s, %s, 'pending', %s)",
                (user_id, chapter_num, utcnow()),
            )
    return True, "Re-registration request submitted. Wait for admin approval."


def list_pending_reregs():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT r.*, u.email, u.student_id, u.full_name, u.generated_username
                   FROM rereg_requests r
                   JOIN users u ON u.id = r.user_id
                   WHERE r.status = 'pending'
                   ORDER BY r.created_at"""
            )
            return c.fetchall()


def approve_rereg(request_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rereg_requests WHERE id = %s", (request_id,))
            row = c.fetchone()
            if not row or row["status"] != "pending":
                return False
            uid, ch = row["user_id"], row["chapter_num"]
            now = utcnow()
            c.execute(
                "UPDATE rereg_requests SET status = 'approved', resolved_at = %s WHERE id = %s",
                (now, request_id),
            )
            c.execute("DELETE FROM level_scores WHERE user_id = %s AND chapter_num = %s", (uid, ch))
            c.execute(
                """INSERT INTO chapter_progress
                   (user_id, chapter_num, total_score, max_possible, levels_cleared, is_rereg, passed, effective_score, updated_at)
                   VALUES (%s, %s, 0, 0, 0, 1, 0, 0, %s)
                   ON DUPLICATE KEY UPDATE
                     total_score=0, max_possible=0, levels_cleared=0, is_rereg=1, passed=0, effective_score=0, updated_at=%s""",
                (uid, ch, now, now),
            )
    refresh_user_status_and_points(uid)
    return True


def user_chapter_is_rereg(user_id, chapter_num):
    p = get_chapter_progress(user_id, chapter_num)
    return bool(p and p.get("is_rereg"))
