"""Student dashboard, game play, rankings, re-registration and feedback PDFs."""
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from .. import db
from ..services import storage
from ..web.decorators import login_required
from ..services.tokens import issue_token, user_from_token, serializer as _serializer
from ..services.pdf import text_to_simple_pdf, build_feedback_pdf
from ..constants import CHAPTER1_LEVEL_MAX

bp = Blueprint("student", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    uid = session.get("user_id")
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        session.clear()
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))
    user = db.get_user(uid)
    if not user or int(user["id"]) != uid:
        session.clear()
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))
    # Keep session identity in sync with THIS account only
    session["user_id"] = int(user["id"])
    session["username"] = user.get("generated_username") or user["student_id"]
    session["student_id"] = user["student_id"]
    session["email"] = user["email"]
    session["role"] = "student"
    # Refresh status so "Working on chapter" is not stale
    try:
        db.refresh_user_status_and_points(uid)
        user = db.get_user(uid)
    except Exception:
        pass
    chapters = db.list_chapters()
    progress = {}
    access = {}
    level_scores = {}
    level_locks = {}
    for ch in chapters:
        n = ch["chapter_num"]
        progress[n] = db.get_chapter_progress(user["id"], n)
        ok, reason = db.user_can_access_chapter(user["id"], n)
        access[n] = {"ok": ok, "reason": reason}
        level_scores[n] = db.get_user_level_scores(user["id"], n)
        level_locks[n] = db.get_chapter_level_lock_map(user["id"], n)

    final_score, weight_detail = db.user_weighted_final(user["id"])
    # Auto weekly snapshot (once per ISO week) + final if season ended
    db.ensure_weekly_snapshot()
    final_snap_id = db.ensure_final_snapshot()
    rank, rank_score, total_players = db.get_user_current_rank(user["id"])
    rank_history = db.get_user_rank_history(user["id"])
    season_ended = db.season_has_ended()
    final_board = None
    if season_ended:
        snaps = db.list_snapshots("final")
        if snaps:
            final_board = db.get_snapshot(snaps[0]["id"])
    league = db.overall_ranking_with_levels()
    proj_rank, proj_score = db.projected_rank_if_pace(user["id"])
    # points needed to pass current status chapter (>50%)
    status_ch = user.get("status_chapter") or 1
    cp = progress.get(status_ch)
    need_to_pass = None
    if cp and cp.get("max_possible"):
        need = int(cp["max_possible"] * 0.5) + 1
        need_to_pass = max(0, need - int(cp.get("total_score") or 0))
    elif status_ch <= 10:
        need_to_pass = None  # unknown until they start
    return render_template(
        "dashboard.html",
        user=user,
        chapters=chapters,
        progress=progress,
        access=access,
        level_scores=level_scores,
        level_locks=level_locks,
        season=db.get_season(),
        season_active=db.season_is_active(),
        final_score=final_score,
        weight_detail=weight_detail,
        chapter_weights=db.CHAPTER_WEIGHTS,
        current_rank=rank,
        rank_score=rank_score,
        total_players=total_players,
        rank_history=rank_history,
        season_ended=season_ended,
        final_board=final_board,
        league=league,
        proj_rank=proj_rank,
        proj_score=proj_score,
        need_to_pass=need_to_pass,
        status_ch=status_ch,
    )


@bp.route("/play/<int:chapter_num>")
@login_required
def play_chapter(chapter_num):
    ok, reason = db.user_can_access_chapter(session["user_id"], chapter_num)
    if not ok:
        flash(reason, "danger")
        return redirect(url_for("student.dashboard"))
    if not db.season_is_active():
        flash("The season is closed. You can view rankings but not play.", "warning")
        return redirect(url_for("student.dashboard"))
    ch = db.get_chapter(chapter_num)
    # Prefer admin-uploaded HTML; fall back to built-in Ch.1 template only if no file
    if ch and ch.get("game_filename"):
        return render_template(
            "play_uploaded.html",
            chapter=ch,
            chapter_num=chapter_num,
            is_rereg=db.user_chapter_is_rereg(session["user_id"], chapter_num),
        )
    if chapter_num == 1:
        scores = db.get_user_level_scores(session["user_id"], chapter_num)
        is_rereg = db.user_chapter_is_rereg(session["user_id"], chapter_num)
        player = db.get_user(session["user_id"])
        return render_template(
            "play_chapter1.html",
            chapter_num=chapter_num,
            scores=scores,
            is_rereg=is_rereg,
            level_max=CHAPTER1_LEVEL_MAX,
            player=player,
        )
    flash("No game HTML has been uploaded for this chapter yet.", "warning")
    return redirect(url_for("student.dashboard"))


@bp.route("/game-file/<int:chapter_num>")
def serve_game_file(chapter_num):
    """Serve admin-uploaded HTML with SignalSleuth game bridge injected.

    Auth: student session OR Bearer / ?access_token= (mobile WebView).
    """
    user = user_from_token()
    if not user:
        token = request.args.get("access_token") or request.args.get("token")
        if token:
            try:
                data = _serializer().loads(token, max_age=60 * 60 * 24 * 14)
                user = db.get_user(data["uid"])
            except Exception:
                user = None
    if not user:
        abort(401)
    # Establish session so bridge fetch('/api/submit-score') works same-origin
    session["user_id"] = int(user["id"])
    session["role"] = "student"
    session["username"] = user.get("generated_username") or user["student_id"]
    ok, reason = db.user_can_access_chapter(user["id"], chapter_num)
    if not ok:
        abort(403)
    ch = db.get_chapter(chapter_num)
    if not ch or not ch.get("game_filename"):
        abort(404)
    raw = storage.load_game_bytes(ch["game_filename"])
    if not raw:
        abort(404)
    try:
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        abort(404)

    bridge_src = url_for("static", filename="js/signalsleuth-game-bridge.js")
    inject = (
        f"\n<!-- Signal Sleuth integration (auto-injected) -->\n"
        f"<script>window.SS_CHAPTER_NUM={int(chapter_num)};window.SS_USER_ID={int(user['id'])};window.SS_USERNAME='';window.SS_API_BASE=\"\";window.SS_TOKEN=\"{issue_token(user['id'])}\";</script>\n"
        f'<script src="{bridge_src}"></script>\n'
    )
    lower = html.lower()
    if "</head>" in lower:
        idx = lower.rfind("</head>")
        html = html[:idx] + inject + html[idx:]
    elif "<body" in lower:
        idx = lower.find("<body")
        # after body tag
        gt = html.find(">", idx)
        html = html[: gt + 1] + inject + html[gt + 1 :]
    else:
        html = inject + html

    from flask import Response
    resp = Response(html, mimetype="text/html; charset=utf-8")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@bp.route("/level-feedback-pdf/<int:chapter_num>/<int:level_num>")
@login_required
def level_feedback_pdf(chapter_num, level_num):
    """Download feedback PDF after clearing a level (includes model answers)."""
    row = db.get_level_feedback(session["user_id"], chapter_num, level_num)
    if not row:
        flash("No score recorded for this level yet. Clear the level first.", "warning")
        return redirect(url_for("student.dashboard"))
    if not row.get("cleared"):
        flash("PDF with correct answers is available after you clear the level (≥50%).", "warning")
        return redirect(url_for("student.play_chapter", chapter_num=chapter_num))
    user = db.get_user(session["user_id"])
    import json
    feedback = []
    if row.get("feedback_json"):
        try:
            feedback = json.loads(row["feedback_json"])
        except Exception:
            feedback = [{"text": str(row["feedback_json"])}]
    pdf_bytes = build_feedback_pdf(user, chapter_num, level_num, row, feedback)
    from flask import Response
    fname = f"SignalSleuth_Ch{chapter_num}_L{level_num}_feedback.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@bp.route("/chapter-feedback-pdf/<int:chapter_num>")
@login_required
def chapter_feedback_pdf(chapter_num):
    """PDF with feedback for ALL levels the student has attempted in this chapter."""
    import json
    user = db.get_user(session["user_id"])
    if not user:
        flash("Session expired.", "warning")
        return redirect(url_for("auth.login"))
    rows = db.get_chapter_all_feedback(user["id"], chapter_num)
    if not rows:
        flash("No level attempts for this chapter yet.", "warning")
        return redirect(url_for("student.dashboard"))
    lines = [
        "Signal Sleuth — Full chapter feedback",
        f"Student: {user.get('full_name') or ''} ({user.get('generated_username') or ''})",
        f"ID: {user.get('student_id')}  Email: {user.get('email')}",
        f"Chapter {chapter_num}",
        "",
    ]
    try:
        bank = db.list_question_bank(chapter_num)
    except Exception:
        bank = []
    for row in rows:
        ln = row.get("level_num")
        lines.append("=" * 60)
        lines.append(
            f"LEVEL {ln}  Score: {row.get('best_score')}/{row.get('max_score')}  "
            f"Attempts: {row.get('attempts')}  Cleared: {'Yes' if row.get('cleared') else 'No'}"
        )
        level_bank = [q for q in bank if int(q.get("level_num") or 0) == int(ln)]
        if level_bank:
            lines.append("Model answers:")
            for q in level_bank:
                lines.append(f"  Q{q['q_index']}. {q['question_text']}")
                lines.append(f"     Answer: {q.get('model_answer') or '—'}")
        feedback = []
        if row.get("feedback_json"):
            try:
                feedback = json.loads(row["feedback_json"])
            except Exception:
                feedback = []
        if isinstance(feedback, list) and feedback:
            lines.append("Your submission:")
            for i, item in enumerate(feedback, 1):
                if isinstance(item, dict):
                    lines.append(f"  Q{i}. {item.get('question') or ''}")
                    lines.append(f"     Your answer: {item.get('answer') or item.get('text') or ''}")
                    lines.append(f"     Score: {item.get('score', '')}/{item.get('max', '')}")
                    lines.append(f"     Feedback: {item.get('feedback') or item.get('note') or ''}")
                else:
                    lines.append(f"  {i}. {item}")
        lines.append("")
    pdf_bytes = text_to_simple_pdf(lines)
    from flask import Response
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=SignalSleuth_Ch{chapter_num}_all_levels_feedback.pdf"
        },
    )


@bp.route("/request-rereg/<int:chapter_num>", methods=["POST"])
@login_required
def request_rereg(chapter_num):
    ok, msg = db.request_rereg(session["user_id"], chapter_num)
    flash(msg, "success" if ok else "warning")
    return redirect(url_for("student.dashboard"))


@bp.route("/rankings")
@login_required
def rankings():
    db.ensure_weekly_snapshot()
    db.ensure_final_snapshot()
    chapter = request.args.get("chapter", type=int)
    snap_id = request.args.get("snapshot", type=int)
    chapters = db.list_chapters()
    weekly = db.list_snapshots("weekly")
    finals = db.list_snapshots("final")
    season_ended = db.season_has_ended()
    if snap_id:
        board = db.get_snapshot(snap_id)
        return render_template(
            "rankings.html", mode="snapshot", board=board, chapters=chapters,
            weekly=weekly, finals=finals, season_ended=season_ended,
            my_id=session["user_id"],
        )
    if chapter:
        ranks = db.ranking_for_chapter(chapter)
        return render_template(
            "rankings.html", mode="chapter", chapter=chapter, ranks=ranks, chapters=chapters,
            weekly=weekly, finals=finals, season_ended=season_ended,
            my_id=session["user_id"],
        )
    ranks = db.overall_ranking_with_levels()
    return render_template(
        "rankings.html", mode="overall", ranks=ranks, chapters=chapters,
        weekly=weekly, finals=finals, season_ended=season_ended,
        my_id=session["user_id"],
    )
