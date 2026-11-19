"""Pre-registered IDs, student accounts, password resets, suspension, email log."""
import pymysql
import random
import re
import string
from datetime import datetime
from .core import utcnow
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from .core import get_conn, normalize_student_id, weighted_final_from_progress
from .schema import ensure_architecture_tables
from .progress import get_user_all_progress


def add_pre_users(entries):
    """entries: list of (student_id, full_name, sex)"""
    added, skipped = 0, 0
    now = utcnow()
    with get_conn() as conn:
        with conn.cursor() as c:
            for item in entries:
                if len(item) >= 3:
                    sid, name, sex = item[0], item[1], item[2]
                else:
                    sid, name, sex = item[0], item[1] if len(item) > 1 else "", ""
                sid = normalize_student_id(sid)
                if not sid:
                    continue
                name = normalize_student_id(name) if name else ""
                # name should not use ID normalizer for floats only - keep simple strip
                name = str(name or "").strip() if name is not None else ""
                sex = str(sex or "").strip() if sex is not None else ""
                try:
                    c.execute(
                        "INSERT INTO pre_users (student_id, full_name, sex, created_at) VALUES (%s, %s, %s, %s)",
                        (sid, name or None, sex or None, now),
                    )
                    added += 1
                except pymysql.err.IntegrityError:
                    skipped += 1
    return added, skipped


def list_pre_users():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT p.*, (u.id IS NOT NULL) AS registered, u.email, u.generated_username
                   FROM pre_users p
                   LEFT JOIN users u ON u.student_id = p.student_id
                   ORDER BY p.student_id"""
            )
            return c.fetchall()


def pre_user_exists(student_id):
    sid = normalize_student_id(student_id)
    if not sid:
        return None
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM pre_users WHERE student_id = %s", (sid,))
            row = c.fetchone()
            if row:
                return row
            # Case-insensitive fallback (Excel/admin vs student typing)
            c.execute("SELECT * FROM pre_users WHERE LOWER(student_id) = LOWER(%s)", (sid,))
            return c.fetchone()


def add_pre_user_one(student_id, full_name=None, sex=None):
    """Add a single pre-registered student. Returns (ok, message)."""
    sid = normalize_student_id(student_id)
    if not sid:
        return False, "Student ID is required."
    now = utcnow()
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute(
                    "INSERT INTO pre_users (student_id, full_name, sex, created_at) VALUES (%s, %s, %s, %s)",
                    (sid, (full_name or "").strip() or None, (sex or "").strip() or None, now),
                )
        return True, f"Added {sid}."
    except Exception as e:
        if "Duplicate" in str(e) or "duplicate" in str(e).lower():
            return False, f"{sid} already exists."
        return False, str(e)


def delete_pre_user(student_id):
    """Delete pre-user by ID. Fails if already registered as a user."""
    sid = normalize_student_id(student_id)
    if not sid:
        return False, "Invalid ID."
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id FROM users WHERE student_id = %s OR LOWER(student_id)=LOWER(%s)", (sid, sid))
            if c.fetchone():
                return False, f"{sid} is already registered; cannot delete from pre-list."
            c.execute("DELETE FROM pre_users WHERE student_id = %s OR LOWER(student_id)=LOWER(%s)", (sid, sid))
            if c.rowcount:
                return True, f"Deleted {sid}."
            return False, f"{sid} not found in pre-list."


def delete_pre_user_by_id(row_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT student_id FROM pre_users WHERE id = %s", (row_id,))
            row = c.fetchone()
            if not row:
                return False, "Not found."
            return delete_pre_user(row["student_id"])


def _generate_username(full_name, student_id):
    base = re.sub(r"[^a-z0-9]", "", (full_name or "").lower())
    if len(base) < 3:
        base = "player" + re.sub(r"[^a-z0-9]", "", str(student_id).lower())[:6]
    base = base[:12] or "player"
    suffix = "".join(random.choices(string.digits, k=3))
    candidate = f"{base}{suffix}"
    with get_conn() as conn:
        with conn.cursor() as c:
            for _ in range(20):
                c.execute("SELECT id FROM users WHERE generated_username = %s", (candidate,))
                if not c.fetchone():
                    return candidate
                candidate = f"{base}{''.join(random.choices(string.digits, k=4))}"
    return f"player{random.randint(10000, 99999)}"


def register_user(student_id, email, password, full_name=None, campus_id=None):
    sid = normalize_student_id(student_id)
    pre = pre_user_exists(sid)
    if not pre:
        return False, (
            f"Student ID '{sid}' is not in the pre-registration list. "
            "Use the exact ID the admin uploaded (check Admin → pre-registered list). "
            "Contact admin if it still fails."
        )
    # Prefer the canonical ID stored in pre_users
    sid = pre["student_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id FROM users WHERE student_id = %s", (sid,))
            if c.fetchone():
                return False, "This Student ID is already registered."
            c.execute("SELECT id FROM users WHERE email = %s", (email.strip().lower(),))
            if c.fetchone():
                return False, "Email already in use."
            name = (full_name or pre.get("full_name") or "").strip() or None
            sex = pre.get("sex")
            uname = _generate_username(name, sid)
            c.execute(
                """INSERT INTO users
                   (student_id, campus_id, full_name, generated_username, sex, email, password_hash,
                    status_chapter, overall_points, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 0, %s)""",
                (
                    sid,
                    normalize_student_id(campus_id) or sid,
                    name,
                    uname,
                    sex,
                    email.strip().lower(),
                    generate_password_hash(password),
                    utcnow(),
                ),
            )
    return True, f"Registration successful. Your username is {uname}."


def verify_user(email, password):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
            row = c.fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return row
    return None


def get_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return c.fetchone()


def get_user_by_email(email):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
            return c.fetchone()


def update_user_password(user_id, new_password):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new_password), user_id),
            )


def delete_user(user_id):
    """Permanently remove a registered player and their scores."""
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id, student_id, email FROM users WHERE id = %s", (user_id,))
            row = c.fetchone()
            if not row:
                return False, "User not found."
            uid = row["id"]
            c.execute("DELETE FROM rank_snapshot_rows WHERE user_id = %s", (uid,))
            c.execute("DELETE FROM level_scores WHERE user_id = %s", (uid,))
            c.execute("DELETE FROM chapter_progress WHERE user_id = %s", (uid,))
            c.execute("DELETE FROM rereg_requests WHERE user_id = %s", (uid,))
            c.execute("DELETE FROM password_reset_requests WHERE user_id = %s", (uid,))
            c.execute("DELETE FROM users WHERE id = %s", (uid,))
    return True, f"Deleted player {row.get('student_id')} ({row.get('email')})."


def admin_create_player(student_id, full_name, email, password, sex=None, campus_id=None):
    """Admin creates a player account (ID must be pre-listed)."""
    return register_user(student_id, email, password, full_name, campus_id or student_id)


def list_all_users():

    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT id, student_id, campus_id, full_name, generated_username, sex,
                          email, status_chapter, overall_points, created_at
                   FROM users ORDER BY student_id"""
            )
            return c.fetchall()


def refresh_user_status_and_points(user_id):
    """Update status_chapter (chapter student is working on) and overall_points.

    Working chapter = lowest chapter that is not fully complete (7 levels cleared),
    or 10 if all complete. Does NOT jump to next chapter after a single level.
    Also repairs chapter_progress.passed / effective_score (full points, no ×4/5).
    """
    with get_conn() as conn:
        with conn.cursor() as c:
            # Repair progress rows from level_scores
            for ch in range(1, 11):
                c.execute(
                    """SELECT COALESCE(SUM(best_score),0) AS ts, COALESCE(SUM(max_score),0) AS ms,
                              COALESCE(SUM(cleared),0) AS lc
                       FROM level_scores WHERE user_id=%s AND chapter_num=%s""",
                    (user_id, ch),
                )
                rows = c.fetchone()
                if not rows:
                    continue
                total_score = int(rows["ts"] or 0)
                max_possible = int(rows["ms"] or 0)
                levels_cleared = int(rows["lc"] or 0)
                if total_score == 0 and levels_cleared == 0 and max_possible == 0:
                    continue
                passed = 1 if levels_cleared >= 7 else 0
                effective = float(total_score)  # full marks; admin ranks re-reg separately
                c.execute(
                    """INSERT INTO chapter_progress
                       (user_id, chapter_num, total_score, max_possible, levels_cleared, is_rereg, passed, effective_score, updated_at)
                       VALUES (%s,%s,%s,%s,%s,
                         COALESCE((SELECT is_rereg FROM chapter_progress cp WHERE cp.user_id=%s AND cp.chapter_num=%s), 0),
                         %s,%s,%s)
                       ON DUPLICATE KEY UPDATE
                         total_score=VALUES(total_score), max_possible=VALUES(max_possible),
                         levels_cleared=VALUES(levels_cleared), passed=VALUES(passed),
                         effective_score=VALUES(effective_score), updated_at=VALUES(updated_at)""",
                    (user_id, ch, total_score, max_possible, levels_cleared,
                     user_id, ch, passed, effective, utcnow()),
                )

    prog = get_user_all_progress(user_id)
    final, _ = weighted_final_from_progress(prog)
    by_ch = {int(r["chapter_num"]): r for r in prog}
    status = 1
    for ch in range(1, 11):
        row = by_ch.get(ch)
        levels_cleared = int(row.get("levels_cleared") or 0) if row else 0
        if levels_cleared >= 7:
            status = min(ch + 1, 10)
            continue
        status = ch
        break
    status = min(max(status, 1), 10)
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE users SET status_chapter = %s, overall_points = %s WHERE id = %s",
                (status, final, user_id),
            )
    return status, final


def request_password_reset(email):
    user = get_user_by_email(email)
    if not user:
        return False, "No account with that email."
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT id FROM password_reset_requests WHERE user_id = %s AND status = 'pending'",
                (user["id"],),
            )
            if c.fetchone():
                return True, "A reset request is already pending. Admin will process it."
            c.execute(
                "INSERT INTO password_reset_requests (user_id, status, created_at) VALUES (%s, 'pending', %s)",
                (user["id"], utcnow()),
            )
    return True, "Reset request sent to admin. You will receive a new password by email once processed."


def list_pending_resets():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT r.*, u.email, u.student_id, u.full_name, u.generated_username
                   FROM password_reset_requests r
                   JOIN users u ON u.id = r.user_id
                   WHERE r.status = 'pending'
                   ORDER BY r.created_at"""
            )
            return c.fetchall()


def resolve_password_reset(request_id, temp_password):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM password_reset_requests WHERE id = %s", (request_id,))
            row = c.fetchone()
            if not row or row["status"] != "pending":
                return None
            c.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(temp_password), row["user_id"]),
            )
            c.execute(
                "UPDATE password_reset_requests SET status = 'resolved', temp_password = %s, resolved_at = %s WHERE id = %s",
                (temp_password, utcnow(), request_id),
            )
            c.execute("SELECT * FROM users WHERE id = %s", (row["user_id"],))
            return c.fetchone()


def log_email(user_id, email_to, subject, body, status):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO email_log (user_id, email_to, subject, body, status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, email_to, subject, body, status, utcnow()),
            )


def set_user_suspended(user_id, suspended=True):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO users_extra (user_id, is_suspended)
                   VALUES (%s,%s)
                   ON DUPLICATE KEY UPDATE is_suspended=VALUES(is_suspended)""",
                (user_id, 1 if suspended else 0),
            )


def is_user_suspended(user_id):
    ensure_architecture_tables()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT is_suspended FROM users_extra WHERE user_id=%s", (user_id,))
            row = c.fetchone()
            return bool(row and row.get("is_suspended"))
