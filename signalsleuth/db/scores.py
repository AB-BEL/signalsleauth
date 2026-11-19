"""Level scores, level locks, attempts and per-student feedback."""
from datetime import datetime
from .core import utcnow
from .core import get_conn
from .schema import ensure_architecture_tables, ensure_level_scores_schema
from .users import refresh_user_status_and_points
from .access import user_chapter_is_rereg


def save_level_score(user_id, chapter_num, level_num, score, max_score, cleared, feedback=None):
    """Save a level attempt.

    Rules:
    - Level/chapter pass at >= 50%.
    - Attempts are counted and stored per player per level (no score halving).
    - Feedback JSON may be stored for PDF download after clear.
    """
    ensure_level_scores_schema()
    now = utcnow()
    is_rereg = 1 if user_chapter_is_rereg(user_id, chapter_num) else 0
    max_score = int(max_score or 0)
    score = int(score or 0)

    # Replay lock: cannot submit if level is locked
    if not can_play_level(user_id, chapter_num, level_num):
        return {"ok": False, "error": "This level is locked. You may download the feedback PDF but cannot replay."}

    # Attempt count after this submit
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM level_scores WHERE user_id = %s AND chapter_num = %s AND level_num = %s",
                (user_id, chapter_num, level_num),
            )
            existing = c.fetchone()
            attempts = (existing["attempts"] if existing else 0) + 1

    # Full marks always — never ×4/5 or half credit. Only store attempt count.
    raw_score = score
    pct_attempt = (score / max_score * 100.0) if max_score else 0.0
    if pct_attempt >= 50.0:
        cleared = True
    else:
        cleared = False

    import json
    fb_json = None
    if feedback is not None:
        try:
            fb_json = json.dumps(feedback) if not isinstance(feedback, str) else feedback
        except Exception:
            fb_json = None

    with get_conn() as conn:
        with conn.cursor() as c:
            if existing:
                # Keep best recorded score; still increment attempts
                best = max(int(existing["best_score"] or 0), score)
                best_pct = (best / max_score * 100.0) if max_score else 0.0
                # Unlock rule: cleared if THIS attempt OR cumulative best is >= 50%
                cleared_flag = 1 if (cleared or existing.get("cleared") or best_pct >= 50.0) else 0
                cleared = bool(cleared_flag)
                if fb_json:
                    c.execute(
                        """UPDATE level_scores SET best_score=%s, max_score=%s, attempts=%s, cleared=%s,
                           is_rereg=%s, feedback_json=%s, updated_at=%s
                           WHERE user_id=%s AND chapter_num=%s AND level_num=%s""",
                        (best, max_score, attempts, cleared_flag, is_rereg, fb_json, now,
                         user_id, chapter_num, level_num),
                    )
                else:
                    c.execute(
                        """UPDATE level_scores SET best_score=%s, max_score=%s, attempts=%s, cleared=%s,
                           is_rereg=%s, updated_at=%s
                           WHERE user_id=%s AND chapter_num=%s AND level_num=%s""",
                        (best, max_score, attempts, cleared_flag, is_rereg, now,
                         user_id, chapter_num, level_num),
                    )
            else:
                c.execute(
                    """INSERT INTO level_scores
                       (user_id, chapter_num, level_num, best_score, max_score, attempts, cleared, is_rereg, feedback_json, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user_id, chapter_num, level_num, score, max_score, attempts,
                     1 if cleared else 0, is_rereg, fb_json, now),
                )
            c.execute(
                """SELECT COALESCE(SUM(best_score),0) AS ts, COALESCE(SUM(max_score),0) AS ms,
                          COALESCE(SUM(cleared),0) AS lc
                   FROM level_scores WHERE user_id=%s AND chapter_num=%s""",
                (user_id, chapter_num),
            )
            rows = c.fetchone()
            total_score = int(rows["ts"] or 0)
            max_possible = int(rows["ms"] or 0)
            levels_cleared = int(rows["lc"] or 0)
            pct = (total_score / max_possible * 100.0) if max_possible else 0.0
            # Chapter complete only when all 7 levels are cleared (not after one level)
            passed = 1 if levels_cleared >= 7 else 0
            # Full points always — no ×4/5; admin decides ranking treatment for re-reg
            effective = float(total_score)
            c.execute(
                """INSERT INTO chapter_progress
                   (user_id, chapter_num, total_score, max_possible, levels_cleared, is_rereg, passed, effective_score, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                     total_score=VALUES(total_score), max_possible=VALUES(max_possible),
                     levels_cleared=VALUES(levels_cleared), is_rereg=VALUES(is_rereg),
                     passed=VALUES(passed), effective_score=VALUES(effective_score), updated_at=VALUES(updated_at)""",
                (user_id, chapter_num, total_score, max_possible, levels_cleared, is_rereg, passed, effective, now),
            )
    try:
        record_game_attempt(
            user_id, chapter_num, level_num, attempts, score, max_score, cleared,
            answers=None, feedback=feedback,
        )
    except Exception as e:
        print("record_game_attempt:", e)
    refresh_user_status_and_points(user_id)
    return {
        "ok": True,
        "total_score": total_score,
        "effective_score": effective,
        "passed": bool(passed),
        "is_rereg": bool(is_rereg),
        "level_score": score,
        "raw_score": raw_score,
        "attempts": attempts,
        "half_applied": False,  # legacy field; scores are never halved
        
        "level_cleared": bool(cleared),
        "cleared": bool(cleared),
        "level_pct": pct_attempt,
    }


def level_meets_pass(score, max_score):
    try:
        s, m = float(score or 0), float(max_score or 0)
        return m > 0 and (s / m) >= 0.5
    except Exception:
        return False


def can_play_level(user_id, chapter_num, level_num):
    """False if a higher level has already been started (attempts > 0)."""
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT level_num, attempts FROM level_scores
                   WHERE user_id=%s AND chapter_num=%s AND level_num > %s AND attempts > 0
                   LIMIT 1""",
                (user_id, chapter_num, level_num),
            )
            return c.fetchone() is None


def get_level_feedback(user_id, chapter_num, level_num):
    ensure_level_scores_schema()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT * FROM level_scores
                   WHERE user_id=%s AND chapter_num=%s AND level_num=%s""",
                (user_id, chapter_num, level_num),
            )
            return c.fetchone()


def get_chapter_level_lock_map(user_id, chapter_num):
    """Return {level_num: {playable, has_feedback, attempts, best_score, max_score, cleared}} for levels 1-7."""
    scores = get_user_level_scores(user_id, chapter_num)
    by_lv = {int(s["level_num"]): s for s in scores}
    highest_started = 0
    for lv, s in by_lv.items():
        if (s.get("attempts") or 0) > 0:
            highest_started = max(highest_started, lv)
    out = {}
    for lv in range(1, 8):
        s = by_lv.get(lv)
        playable = True
        if highest_started > lv:
            playable = False
        out[lv] = {
            "playable": playable,
            "has_feedback": bool(s and s.get("feedback_json")),
            "attempts": (s or {}).get("attempts") or 0,
            "best_score": (s or {}).get("best_score") or 0,
            "max_score": (s or {}).get("max_score") or 0,
            "cleared": bool(s and s.get("cleared")),
            "locked": not playable,
        }
    return out


def get_user_level_scores(user_id, chapter_num):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM level_scores WHERE user_id = %s AND chapter_num = %s ORDER BY level_num",
                (user_id, chapter_num),
            )
            return c.fetchall()


def list_all_student_feedback(chapter_num=None, level_num=None):
    """All level_scores rows that have feedback or scores, with user info."""
    ensure_level_scores_schema()
    with get_conn() as conn:
        with conn.cursor() as c:
            sql = """SELECT ls.*, u.student_id, u.full_name, u.generated_username, u.email
                     FROM level_scores ls
                     JOIN users u ON u.id = ls.user_id
                     WHERE 1=1"""
            params = []
            if chapter_num is not None:
                sql += " AND ls.chapter_num = %s"
                params.append(chapter_num)
            if level_num is not None:
                sql += " AND ls.level_num = %s"
                params.append(level_num)
            sql += " ORDER BY ls.chapter_num, ls.level_num, u.student_id"
            c.execute(sql, params)
            return c.fetchall()


def update_student_feedback(user_id, chapter_num, level_num, feedback_obj):
    """Replace feedback_json for a student level attempt."""
    import json
    ensure_level_scores_schema()
    if isinstance(feedback_obj, str):
        fb = feedback_obj
        # validate JSON
        json.loads(fb)
    else:
        fb = json.dumps(feedback_obj, ensure_ascii=False)
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """UPDATE level_scores SET feedback_json=%s, updated_at=%s
                   WHERE user_id=%s AND chapter_num=%s AND level_num=%s""",
                (fb, utcnow(), user_id, chapter_num, level_num),
            )
            if c.rowcount == 0:
                return False, "No score row for this student/level."
    return True, "Feedback updated."


def get_student_level_row(user_id, chapter_num, level_num):
    return get_level_feedback(user_id, chapter_num, level_num)


def get_chapter_all_feedback(user_id, chapter_num):
    """All level score rows for a chapter including feedback_json (ordered by level)."""
    ensure_level_scores_schema()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT * FROM level_scores
                   WHERE user_id=%s AND chapter_num=%s
                   ORDER BY level_num""",
                (user_id, chapter_num),
            )
            return c.fetchall()


def record_game_attempt(user_id, chapter_num, level_num, attempt_no, score, max_score, cleared, answers=None, feedback=None):
    ensure_architecture_tables()
    import json
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO game_attempts
                   (user_id, chapter_num, level_num, attempt_no, score, max_score, cleared,
                    answers_json, feedback_json, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    user_id, chapter_num, level_num, attempt_no, score, max_score,
                    1 if cleared else 0,
                    json.dumps(answers) if answers is not None else None,
                    json.dumps(feedback) if feedback is not None else None,
                    utcnow(),
                ),
            )
