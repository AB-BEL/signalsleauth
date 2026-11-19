"""Question bank, trusted server-side scoring and the mobile game package."""
import json as _json
import re as _re
from datetime import datetime
from .core import utcnow
from .core import get_conn
from .schema import ensure_question_bank_seeded
from .chapters import get_chapter


def _normalize_answer_text(s):
    s = (s or "").lower()
    s = _re.sub(r"[^\w\s]", " ", s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s


def evaluate_answer_server(text, keys, points):
    """Keyword/phrase weighted scoring matching the game engine."""
    points = int(points or 0)
    norm = _normalize_answer_text(text)
    if not norm or len(norm) < 3:
        labels = []
        if isinstance(keys, list):
            labels = [k.get("label") or "" for k in keys if isinstance(k, dict)]
        return {
            "score": 0,
            "max": points,
            "matched": [],
            "missing": labels,
            "ratio": 0.0,
        }
    if isinstance(keys, str):
        try:
            keys = _json.loads(keys)
        except Exception:
            keys = []
    if not isinstance(keys, list):
        keys = []
    ew = tw = 0
    matched, missing = [], []
    for k in keys:
        if not isinstance(k, dict):
            continue
        w = int(k.get("weight") or 1)
        tw += w
        phrases = k.get("phrases") or []
        label = k.get("label") or (phrases[0] if phrases else "item")
        hit = False
        for ph in phrases:
            if _normalize_answer_text(ph) and _normalize_answer_text(ph) in norm:
                hit = True
                break
        if hit:
            ew += w
            matched.append(label)
        else:
            missing.append(label)
    ratio = (ew / tw) if tw else 0.0
    score = int(round(ratio * points))
    # Small partial credit for long non-matching attempts (same as client soft floor)
    if score == 0 and len(norm) > 40:
        score = min(2, points)
    return {
        "score": score,
        "max": points,
        "matched": matched,
        "missing": missing,
        "ratio": ratio,
    }


def score_level_answers(chapter_num, level_num, answers):
    """
    Score a level using question_bank only.
    answers: list of {q_index|index|question, answer|text} or plain strings in order.
    Returns dict with score, max_score, cleared, feedback, detail — or error.
    """
    ensure_question_bank_seeded()
    questions = [
        q for q in list_question_bank(chapter_num)
        if int(q.get("level_num") or 0) == int(level_num)
    ]
    questions.sort(key=lambda q: int(q.get("q_index") or 0))
    if not questions:
        return {
            "ok": False,
            "error": f"No authorized questions for chapter {chapter_num} level {level_num}. "
                     "Admin must load the question bank before scoring.",
        }

    # Normalize answers list to map by q_index or sequential order
    ans_list = answers if isinstance(answers, list) else []
    by_index = {}
    sequential = []
    for i, a in enumerate(ans_list):
        if isinstance(a, str):
            sequential.append(a)
            by_index[i + 1] = a
        elif isinstance(a, dict):
            text = a.get("answer") if a.get("answer") is not None else a.get("text") or a.get("a") or ""
            sequential.append(text)
            qi = a.get("q_index") or a.get("index") or a.get("i")
            if qi is not None:
                try:
                    by_index[int(qi)] = text
                except Exception:
                    by_index[i + 1] = text
            else:
                by_index[i + 1] = text

    total = 0
    total_max = 0
    feedback = []
    detail = []
    for qi, q in enumerate(questions, 1):
        q_index = int(q.get("q_index") or qi)
        pts = int(q.get("points") or 0)
        total_max += pts
        text = by_index.get(q_index)
        if text is None and qi - 1 < len(sequential):
            text = sequential[qi - 1]
        text = text or ""
        keys = q.get("keys_json") or "[]"
        ev = evaluate_answer_server(text, keys, pts)
        total += ev["score"]
        detail.append(ev)
        feedback.append({
            "question": q.get("question_text") or "",
            "answer": text,
            "score": ev["score"],
            "max": ev["max"],
            "feedback": (
                ("Matched: " + ", ".join(ev["matched"])) if ev["matched"]
                else "Weak coverage"
            ) + (
                (" | Missing: " + ", ".join(ev["missing"])) if ev["missing"] else ""
            ),
            "model_answer": q.get("model_answer") or "",
        })

    cleared = total_max > 0 and (total / total_max) >= 0.5
    return {
        "ok": True,
        "score": total,
        "max_score": total_max,
        "cleared": cleared,
        "feedback": feedback,
        "detail": detail,
        "question_count": len(questions),
    }


def validate_client_score_caps(score, max_score, level_max_hint=None):
    """Reject absurd client-only submissions when answers are absent (legacy path disabled)."""
    try:
        score = int(score)
        max_score = int(max_score)
    except Exception:
        return False, "Invalid score types"
    if max_score <= 0 or max_score > 500:
        return False, "Invalid max_score"
    if score < 0 or score > max_score:
        return False, "score must be between 0 and max_score"
    if level_max_hint is not None and max_score > int(level_max_hint) + 5:
        return False, "max_score exceeds authorized level total"
    return True, "ok"


def list_question_bank(chapter_num=None):
    ensure_question_bank_seeded()
    with get_conn() as conn:
        with conn.cursor() as c:
            if chapter_num is not None:
                c.execute(
                    """SELECT * FROM question_bank WHERE chapter_num = %s
                       ORDER BY level_num, q_index""",
                    (chapter_num,),
                )
            else:
                c.execute("SELECT * FROM question_bank ORDER BY chapter_num, level_num, q_index")
            return c.fetchall()


def get_question(qid):
    ensure_question_bank_seeded()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM question_bank WHERE id = %s", (qid,))
            return c.fetchone()


def update_question(qid, question_text, points, model_answer, feedback_note, keys_json=None, level_title=None):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """UPDATE question_bank SET
                   question_text=%s, points=%s, model_answer=%s, feedback_note=%s,
                   keys_json=COALESCE(%s, keys_json),
                   level_title=COALESCE(%s, level_title),
                   updated_at=%s
                   WHERE id=%s""",
                (question_text, int(points or 0), model_answer, feedback_note,
                 keys_json, level_title, utcnow(), qid),
            )
    return get_question(qid)


def add_question(chapter_num, level_num, q_index, question_text, points, model_answer,
                 feedback_note="", keys_json="[]", level_title=""):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO question_bank
                   (chapter_num, level_num, q_index, level_title, question_text, points,
                    model_answer, keys_json, feedback_note, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     question_text=VALUES(question_text), points=VALUES(points),
                     model_answer=VALUES(model_answer), feedback_note=VALUES(feedback_note),
                     keys_json=VALUES(keys_json), level_title=VALUES(level_title),
                     updated_at=VALUES(updated_at)""",
                (chapter_num, level_num, q_index, level_title or None, question_text,
                 int(points or 0), model_answer, keys_json or "[]", feedback_note, utcnow()),
            )
            return c.lastrowid


def get_mobile_game_package(chapter_num):
    """JSON game definition for mobile/web clients (from question_bank + chapter row).

    Does not expose scoring keys to clients (server scores answers).
    """
    ensure_question_bank_seeded()
    ch = get_chapter(chapter_num)
    if not ch:
        return None
    questions = list_question_bank(chapter_num)
    levels_map = {}
    for q in questions:
        ln = int(q.get("level_num") or 0)
        if ln < 1:
            continue
        levels_map.setdefault(ln, {
            "id": ln,
            "title": q.get("level_title") or f"Level {ln}",
            "maxScore": 0,
            "questions": [],
        })
        levels_map[ln]["questions"].append({
            "q_index": int(q.get("q_index") or 0),
            "text": q.get("question_text") or "",
            "points": int(q.get("points") or 0),
            # keys intentionally omitted — server-side scoring only
        })
        levels_map[ln]["maxScore"] += int(q.get("points") or 0)
    levels = [levels_map[k] for k in sorted(levels_map.keys())]
    for lv in levels:
        lv["questions"].sort(key=lambda x: x["q_index"])
    has_html = bool(ch.get("game_filename"))
    has_bank = len(levels) > 0
    # Preferred mobile mode: native bank renderer; HTML available as alternate
    if has_bank:
        mode = "bank"
    elif has_html:
        mode = "html"
    else:
        mode = "empty"
    return {
        "chapter_num": int(chapter_num),
        "title": ch.get("title") or f"Chapter {chapter_num}",
        "active": bool(ch.get("active")),
        "mode": mode,
        "has_html_game": has_html,
        "has_question_bank": has_bank,
        "levels": levels,
        "html_path": f"/game-file/{int(chapter_num)}" if has_html else None,
    }
