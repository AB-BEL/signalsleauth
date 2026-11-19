"""Cookie-session JSON endpoints used by embedded games (score submission, level status)."""
from flask import Blueprint, jsonify, request, session
from .. import db
from ..web.decorators import login_required
from ..services.tokens import user_from_token

bp = Blueprint("game_api", __name__)


@bp.route("/api/submit-score", methods=["POST"])
def api_submit_score():
    """Trusted scoring endpoint.

    Preferred body:
      { chapter_num, level_num, answers: [{q_index, answer}, ...] }

    Client-provided score / max_score / cleared are IGNORED when answers are present.
    Server loads question_bank, scores answers, then persists the verified result.
    """
    user = user_from_token()
    if not user:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    data = request.get_json(force=True) or {}
    try:
        chapter = int(data.get("chapter_num", 1))
        level = int(data.get("level_num", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid chapter or level"}), 400
    if chapter < 1 or chapter > 10 or level < 1 or level > 7:
        return jsonify({"ok": False, "error": "chapter_num must be 1–10 and level_num 1–7"}), 400

    ok, reason = db.user_can_access_chapter(user["id"], chapter)
    if not ok:
        return jsonify({"ok": False, "error": reason}), 403
    if not db.can_play_level(user["id"], chapter, level):
        return jsonify({
            "ok": False,
            "error": "Level locked — you already started a later level. Download the feedback PDF instead.",
            "locked": True,
        }), 403

    # Collect answers from several client shapes
    answers = data.get("answers")
    if answers is None and isinstance(data.get("feedback"), list):
        # feedback items often include student answers — use only as answer text source
        answers = [
            {
                "q_index": i + 1,
                "answer": (item.get("answer") or item.get("text") or item.get("a") or "")
                if isinstance(item, dict) else "",
            }
            for i, item in enumerate(data.get("feedback") or [])
        ]

    if not answers or not isinstance(answers, list) or len(answers) == 0:
        return jsonify({
            "ok": False,
            "error": "Answers required. Submit answers[] so the server can score the level. "
                     "Client-reported score is not accepted.",
            "code": "ANSWERS_REQUIRED",
        }), 400

    verified = db.score_level_answers(chapter, level, answers)
    if not verified.get("ok"):
        return jsonify(verified), 400

    score = int(verified["score"])
    max_score = int(verified["max_score"])
    cleared = bool(verified["cleared"])
    feedback = verified.get("feedback")

    # Hard safety caps (cannot exceed bank total)
    if score < 0 or score > max_score or max_score <= 0:
        return jsonify({"ok": False, "error": "Internal scoring bounds error"}), 500

    result = db.save_level_score(
        user["id"], chapter, level, score, max_score, cleared, feedback=feedback
    )
    if result.get("ok") is False:
        return jsonify(result), 403

    result["level_cleared"] = bool(result.get("level_cleared") or cleared)
    result["cleared"] = bool(result.get("cleared") or result.get("level_cleared"))
    result["score"] = score
    result["max_score"] = max_score
    result["level_score"] = result.get("level_score", score)
    result["server_scored"] = True
    result["question_count"] = verified.get("question_count")
    result["feedback"] = feedback
    return jsonify(result)


@bp.route("/api/level-status/<int:chapter_num>")
@login_required
def api_level_status(chapter_num):
    locks = db.get_chapter_level_lock_map(session["user_id"], chapter_num)
    return jsonify({"levels": locks})


@bp.route("/api/my-scores/<int:chapter_num>")
def api_my_scores(chapter_num):
    user = user_from_token()
    if not user:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    scores = db.get_user_level_scores(user["id"], chapter_num)
    prog = db.get_chapter_progress(user["id"], chapter_num)
    locks = db.get_chapter_level_lock_map(user["id"], chapter_num)
    return jsonify({
        "ok": True,
        "levels": scores,
        "progress": prog,
        "locks": locks,
        "is_rereg": db.user_chapter_is_rereg(user["id"], chapter_num),
        "pass_rule": "Level clears at >= 50% overall. Attempts are counted; scores are never reduced (no ×4/5, no half credit).",
    })
