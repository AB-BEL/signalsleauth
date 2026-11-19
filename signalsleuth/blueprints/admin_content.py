"""Admin: question bank, student feedback editing and downloads."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from .. import db
from ..web.decorators import admin_required
from ..services.pdf import text_to_simple_pdf

bp = Blueprint("admin_content", __name__)


@bp.route("/admin/questions")
@admin_required
def admin_questions():
    """View/edit question bank: all levels, questions, model answers, feedback notes."""
    try:
        db.ensure_question_bank_seeded()
    except Exception as e:
        flash(f"Question bank init: {e}", "warning")
    chapter = request.args.get("chapter", type=int)
    questions = db.list_question_bank(chapter)
    # group by chapter, level
    grouped = {}
    for q in questions:
        key = (q["chapter_num"], q["level_num"])
        grouped.setdefault(key, {"title": q.get("level_title") or f"Level {q['level_num']}", "questions": []})
        grouped[key]["questions"].append(q)
    return render_template(
        "admin_questions.html",
        module="questions",
        questions=questions,
        grouped=grouped,
        filter_chapter=chapter,
        chapters=db.list_chapters(),
    )


@bp.route("/admin/questions/<int:qid>/edit", methods=["GET", "POST"])
@admin_required
def admin_question_edit(qid):
    q = db.get_question(qid)
    if not q:
        flash("Question not found.", "danger")
        return redirect(url_for("admin_content.admin_questions"))
    if request.method == "POST":
        db.update_question(
            qid,
            request.form.get("question_text", ""),
            request.form.get("points", 0),
            request.form.get("model_answer", ""),
            request.form.get("feedback_note", ""),
            keys_json=request.form.get("keys_json") or None,
            level_title=request.form.get("level_title") or None,
        )
        flash("Question and feedback notes saved.", "success")
        return redirect(url_for("admin_content.admin_questions", chapter=q["chapter_num"]))
    return render_template("admin_question_edit.html", q=q)


@bp.route("/admin/questions/add", methods=["POST"])
@admin_required
def admin_question_add():
    try:
        db.add_question(
            int(request.form.get("chapter_num", 1)),
            int(request.form.get("level_num", 1)),
            int(request.form.get("q_index", 1)),
            request.form.get("question_text", "").strip(),
            request.form.get("points", 10),
            request.form.get("model_answer", ""),
            request.form.get("feedback_note", ""),
            request.form.get("keys_json") or "[]",
            request.form.get("level_title", ""),
        )
        flash("Question added to bank.", "success")
    except Exception as e:
        flash(f"Could not add question: {e}", "danger")
    return redirect(url_for("admin_content.admin_questions"))


@bp.route("/admin/feedback")
@admin_required
def admin_feedback_list():
    """All student level submissions with answers/feedback."""
    chapter = request.args.get("chapter", type=int)
    level = request.args.get("level", type=int)
    rows = db.list_all_student_feedback(chapter, level)
    import json
    parsed = []
    for r in rows:
        r = dict(r)
        fb = []
        if r.get("feedback_json"):
            try:
                fb = json.loads(r["feedback_json"])
            except Exception:
                fb = [{"text": r["feedback_json"]}]
        r["feedback_parsed"] = fb
        parsed.append(r)
    return render_template(
        "admin_feedback.html",
        module="feedback",
        rows=parsed,
        filter_chapter=chapter,
        filter_level=level,
        chapters=db.list_chapters(),
    )


@bp.route("/admin/feedback/<int:user_id>/<int:chapter_num>/<int:level_num>", methods=["GET", "POST"])
@admin_required
def admin_feedback_edit(user_id, chapter_num, level_num):
    import json
    row = db.get_student_level_row(user_id, chapter_num, level_num)
    player = db.get_user(user_id)
    if not row or not player:
        flash("Submission not found.", "danger")
        return redirect(url_for("admin_content.admin_feedback_list"))
    bank = [q for q in db.list_question_bank(chapter_num) if int(q["level_num"]) == level_num]
    if request.method == "POST":
        raw = request.form.get("feedback_json", "").strip()
        try:
            # Prefer structured fields if present
            n = int(request.form.get("item_count", 0) or 0)
            if n > 0:
                items = []
                for i in range(n):
                    items.append({
                        "question": request.form.get(f"q_{i}", ""),
                        "answer": request.form.get(f"a_{i}", ""),
                        "score": request.form.get(f"s_{i}", ""),
                        "max": request.form.get(f"m_{i}", ""),
                        "feedback": request.form.get(f"f_{i}", ""),
                    })
                ok, msg = db.update_student_feedback(user_id, chapter_num, level_num, items)
            else:
                ok, msg = db.update_student_feedback(user_id, chapter_num, level_num, raw)
            flash(msg, "success" if ok else "danger")
            return redirect(url_for("admin_content.admin_feedback_edit", user_id=user_id, chapter_num=chapter_num, level_num=level_num))
        except Exception as e:
            flash(f"Invalid feedback data: {e}", "danger")
    fb = []
    if row.get("feedback_json"):
        try:
            fb = json.loads(row["feedback_json"])
        except Exception:
            fb = []
    return render_template(
        "admin_feedback_edit.html",
        row=row,
        player=player,
        feedback=fb if isinstance(fb, list) else [],
        bank=bank,
        chapter_num=chapter_num,
        level_num=level_num,
    )


@bp.route("/admin/questions/download")
@admin_required
def admin_questions_download():
    """Download question bank as CSV (questions + model answers)."""
    import csv
    from io import StringIO
    from flask import Response
    chapter = request.args.get("chapter", type=int)
    rows = db.list_question_bank(chapter)
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["chapter", "level", "level_title", "q_index", "question", "points", "model_answer", "feedback_note"])
    for q in rows:
        w.writerow([
            q["chapter_num"], q["level_num"], q.get("level_title") or "",
            q["q_index"], q["question_text"], q["points"],
            q.get("model_answer") or "", q.get("feedback_note") or "",
        ])
    fname = f"questions_ch{chapter}.csv" if chapter else "questions_all.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@bp.route("/admin/questions/download-pdf")
@admin_required
def admin_questions_download_pdf():
    """Download questions + answers as simple PDF."""
    chapter = request.args.get("chapter", type=int)
    rows = db.list_question_bank(chapter)
    lines = ["Signal Sleuth — Question bank", f"Chapter filter: {chapter or 'ALL'}", ""]
    cur = None
    for q in rows:
        key = (q["chapter_num"], q["level_num"])
        if key != cur:
            cur = key
            lines.append(f"--- Chapter {q['chapter_num']} Level {q['level_num']}: {q.get('level_title') or ''} ---")
        lines.append(f"Q{q['q_index']} ({q['points']} pts): {q['question_text']}")
        lines.append(f"  Answer: {q.get('model_answer') or '—'}")
        if q.get("feedback_note"):
            lines.append(f"  Feedback note: {q['feedback_note']}")
        lines.append("")
    pdf_bytes = text_to_simple_pdf(lines)
    from flask import Response
    fname = f"questions_ch{chapter}.pdf" if chapter else "questions_all.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@bp.route("/admin/questions/reseed", methods=["POST"])
@admin_required
def admin_questions_reseed():
    """Force upsert of all Chapter 1 questions (7 levels) into the bank."""
    try:
        db.ensure_question_bank_seeded()
        n = len(db.list_question_bank(1))
        flash(f"Chapter 1 question bank refreshed ({n} questions across levels 1–7).", "success")
    except Exception as e:
        flash(f"Reseed failed: {e}", "danger")
    return redirect(url_for("admin_content.admin_questions", chapter=1))
