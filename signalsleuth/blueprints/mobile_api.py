"""Token-authenticated JSON API for the React/mobile client, plus the optional /m/ SPA host."""
import os
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from .. import db
from ..web.decorators import api_login_required
from ..services.tokens import issue_token
from ..services import throttle
from ..constants import CHAPTER1_LEVEL_MAX
from ..config import MOBILE_DIST_DIR

bp = Blueprint("mobile_api", __name__)


@bp.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    try:
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        wait = throttle.seconds_blocked("student", email)
        if wait:
            return jsonify({"ok": False, "error": f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s)."}), 429
        user = db.verify_user(email, password)
        if not user:
            throttle.record_failure("student", email)
            return jsonify({"ok": False, "error": "Invalid email or password"}), 401
        throttle.record_success("student", email)
        token = issue_token(user["id"])
        return jsonify({
            "ok": True,
            "token": token,
            "user": {
                "id": user["id"],
                "student_id": user["student_id"],
                "full_name": user.get("full_name"),
                "generated_username": user.get("generated_username"),
                "email": user["email"],
                "sex": user.get("sex"),
                "status_chapter": int(user.get("status_chapter") or 1),
                "overall_points": float(user.get("overall_points") or 0),
            },
        })
    except Exception as e:
        current_app.logger.exception("Mobile login failed")
        return jsonify({"ok": False, "error": "Login failed. Please try again."}), 500


@bp.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    try:
        data = request.get_json(force=True, silent=True) or {}
        sid = (data.get("student_id") or "").strip()
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        full_name = (data.get("full_name") or "").strip()
        campus_id = (data.get("campus_id") or "").strip() or sid
        if not sid or not email or not full_name or len(password) < 6:
            return jsonify({
                "ok": False,
                "error": "Student ID, name, email, and password (min 6) required",
            }), 400
        ok, msg = db.register_user(sid, email, password, full_name, campus_id)
        if not ok:
            return jsonify({"ok": False, "error": msg}), 400
        user = db.verify_user(email, password)
        if not user:
            # Account created but auto-login failed — still success for signup
            return jsonify({
                "ok": True,
                "message": msg + " Please sign in.",
                "token": None,
                "user": None,
            })
        token = issue_token(user["id"])
        return jsonify({
            "ok": True,
            "message": msg,
            "token": token,
            "user": {
                "id": user["id"],
                "student_id": user["student_id"],
                "full_name": user.get("full_name"),
                "generated_username": user.get("generated_username"),
                "email": user["email"],
                "status_chapter": int(user.get("status_chapter") or 1),
            },
        })
    except Exception as e:
        # Always JSON so the mobile app never sees HTML 500 pages
        current_app.logger.exception("Mobile registration failed")
        return jsonify({"ok": False, "error": "Registration failed. Please try again."}), 500


@bp.route("/api/me")
@api_login_required
def api_me():
    user = request.mobile_user
    final_score, weight_detail = db.user_weighted_final(user["id"])
    rank, rank_score, total_players = db.get_user_current_rank(user["id"])
    return jsonify({
        "ok": True,
        "user": {
            "id": user["id"],
            "student_id": user["student_id"],
            "campus_id": user.get("campus_id"),
            "full_name": user.get("full_name"),
            "generated_username": user.get("generated_username"),
            "email": user["email"],
            "sex": user.get("sex"),
            "status_chapter": user.get("status_chapter") or 1,
            "overall_points": float(user.get("overall_points") or 0),
        },
        "final_score": final_score,
        "rank": rank,
        "total_players": total_players,
        "season": db.get_season(),
        "season_active": db.season_is_active(),
    })


@bp.route("/api/dashboard")
@api_login_required
def api_dashboard():
    user = request.mobile_user
    uid = user["id"]
    chapters = db.list_chapters()
    items = []
    for ch in chapters:
        n = ch["chapter_num"]
        prog = db.get_chapter_progress(uid, n)
        ok, reason = db.user_can_access_chapter(uid, n)
        levels = db.get_user_level_scores(uid, n)
        locks = db.get_chapter_level_lock_map(uid, n)
        items.append({
            "chapter_num": n,
            "title": ch.get("title"),
            "is_active": bool(ch.get("is_active")),
            "start_date": str(ch.get("start_date") or ""),
            "end_date": str(ch.get("end_date") or ""),
            "has_game": bool(ch.get("game_filename")),
            "access_ok": ok,
            "access_reason": reason,
            "progress": prog,
            "levels": levels,
            "locks": locks,
        })
    final_score, weight_detail = db.user_weighted_final(uid)
    rank, _, total_players = db.get_user_current_rank(uid)
    league = db.overall_ranking()[:30]
    for p in league:
        p["overall_score"] = float(p.get("overall_score") or 0)
    return jsonify({
        "ok": True,
        "user": {
            "id": user["id"],
            "student_id": user["student_id"],
            "full_name": user.get("full_name"),
            "generated_username": user.get("generated_username"),
            "email": user["email"],
            "status_chapter": user.get("status_chapter") or 1,
        },
        "final_score": final_score,
        "weight_detail": weight_detail,
        "rank": rank,
        "total_players": total_players,
        "chapters": items,
        "league": league,
        "season_active": db.season_is_active(),
        "pass_rule": "Level clears at >= 50% overall. Attempts are counted; scores are never reduced (no ×4/5, no half credit).",
    })


@bp.route("/api/rankings")
@api_login_required
def api_rankings():
    chapter = request.args.get("chapter", type=int)
    if chapter:
        ranks = db.ranking_for_chapter(chapter)
    else:
        ranks = db.overall_ranking_with_levels()
    for r in ranks:
        if "overall_score" in r:
            r["overall_score"] = float(r.get("overall_score") or 0)
        if "effective_score" in r:
            r["effective_score"] = float(r.get("effective_score") or 0)
    return jsonify({"ok": True, "mode": "chapter" if chapter else "overall", "ranks": ranks})


@bp.route("/api/chapter/<int:chapter_num>/play-info")
@api_login_required
def api_play_info(chapter_num):
    user = request.mobile_user
    ok, reason = db.user_can_access_chapter(user["id"], chapter_num)
    if not ok:
        return jsonify({"ok": False, "error": reason}), 403
    scores = db.get_user_level_scores(user["id"], chapter_num)
    locks = db.get_chapter_level_lock_map(user["id"], chapter_num)
    ch = db.get_chapter(chapter_num)
    return jsonify({
        "ok": True,
        "chapter": ch,
        "scores": scores,
        "locks": locks,
        "is_rereg": db.user_chapter_is_rereg(user["id"], chapter_num),
        "level_max": CHAPTER1_LEVEL_MAX if chapter_num == 1 else {},
    })


@bp.route("/api/chapter/<int:chapter_num>/game-package")
@api_login_required
def api_game_package(chapter_num):
    """Dynamic game definition for mobile (and any SPA).

    Returns levels/questions from question_bank and/or HTML game URL.
    Scoring always goes through /api/submit-score with answers[].
    """
    user = request.mobile_user
    ok, reason = db.user_can_access_chapter(user["id"], chapter_num)
    if not ok:
        return jsonify({"ok": False, "error": reason}), 403
    pkg = db.get_mobile_game_package(chapter_num)
    if not pkg:
        return jsonify({"ok": False, "error": "Chapter not found"}), 404
    # Scores + locks for this user
    scores = db.get_user_level_scores(user["id"], chapter_num)
    locks = db.get_chapter_level_lock_map(user["id"], chapter_num)
    token = issue_token(user["id"])
    html_url = None
    if pkg.get("html_path"):
        # Absolute path relative to API host; mobile prepends API base
        html_url = f"{pkg['html_path']}?access_token={token}"
    return jsonify({
        "ok": True,
        "package": pkg,
        "scores": scores,
        "locks": locks,
        "html_play_url": html_url,
        "is_rereg": db.user_chapter_is_rereg(user["id"], chapter_num),
    })


@bp.route("/m")  # also served without the slash, so no redirect is needed behind the proxy
@bp.route("/m/")
@bp.route("/m/<path:path>")
def serve_mobile_spa(path="index.html"):
    root = str(MOBILE_DIST_DIR)
    if not os.path.isdir(root):
        return (
            "Mobile app not built. Run: cd mobile && npm install && npm run build "
            "then copy mobile/dist/* to public/static/mobile/",
            404,
        )
    target = os.path.join(root, path)
    if path == "index.html" or not os.path.isfile(target):
        return send_from_directory(root, "index.html")
    return send_from_directory(root, path)
