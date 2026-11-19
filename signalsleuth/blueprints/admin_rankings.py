"""Admin: rankings, snapshots, exports, reports and scoring overview."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from .. import db
from ..web.decorators import admin_required

bp = Blueprint("admin_rankings", __name__)


@bp.route("/admin/rankings")
@admin_required
def admin_rankings():
    db.ensure_weekly_snapshot()
    db.ensure_final_snapshot()
    chapter = request.args.get("chapter", type=int)
    snap_id = request.args.get("snapshot", type=int)
    chapters = db.list_chapters()
    weekly = db.list_snapshots("weekly")
    finals = db.list_snapshots("final")
    if snap_id:
        board = db.get_snapshot(snap_id)
        return render_template(
            "admin_rankings.html", module="leaderboard", mode="snapshot", board=board, chapters=chapters,
            weekly=weekly, finals=finals, season_ended=db.season_has_ended(),
        )
    if chapter:
        ranks = db.ranking_for_chapter(chapter)
        return render_template(
            "admin_rankings.html", module="leaderboard", mode="chapter", chapter=chapter, ranks=ranks, chapters=chapters,
            weekly=weekly, finals=finals, season_ended=db.season_has_ended(),
        )
    ranks = db.overall_ranking_with_levels()
    return render_template(
        "admin_rankings.html", module="leaderboard", mode="overall", ranks=ranks, chapters=chapters,
        weekly=weekly, finals=finals, season_ended=db.season_has_ended(),
    )


@bp.route("/admin/snapshot", methods=["POST"])
@admin_required
def admin_force_snapshot():
    kind = request.form.get("type", "weekly")
    if kind == "final":
        sid = db.take_rank_snapshot("final", "FINAL")
        flash("Final season ranking snapshot saved." if sid else "Final snapshot already exists (or failed).", "success" if sid else "warning")
    else:
        # Allow force new weekly with unique label
        label = db._iso_week_label() + "-manual-" + db.core.utcnow().strftime("%H%M%S")
        sid = db.take_rank_snapshot("weekly", label)
        flash("Weekly ranking snapshot saved." if sid else "Snapshot failed.", "success" if sid else "danger")
    return redirect(url_for("admin_rankings.admin_rankings"))


@bp.route("/admin/export-ranking")
@admin_required
def admin_export_ranking():
    """Export live overall ranking (or final snapshot if season ended) to Excel."""
    from openpyxl import Workbook
    from io import BytesIO
    from flask import send_file

    db.ensure_weekly_snapshot()
    db.ensure_final_snapshot()
    use_final = request.args.get("final") == "1" or db.season_has_ended()
    rows = []
    title = "Live overall ranking"
    if use_final:
        snaps = db.list_snapshots("final")
        if snaps:
            board = db.get_snapshot(snaps[0]["id"])
            title = f"Final ranking ({board['snapshot']['week_label']})"
            for r in board["rows"]:
                rows.append({
                    "rank": r.get("rank") or r.get("rank_pos"),
                    "username": r.get("generated_username") or "",
                    "student_id": r.get("student_id"),
                    "full_name": r.get("full_name") or "",
                    "email": r.get("email") or "",
                    "score": r.get("overall_score"),
                    "chapters_passed": r.get("chapters_passed"),
                    "any_rereg": r.get("any_rereg"),
                })
    if not rows:
        title = "Live overall ranking"
        for r in db.overall_ranking():
            rows.append({
                "rank": r["rank"],
                "username": r.get("generated_username") or "",
                "student_id": r.get("student_id"),
                "full_name": r.get("full_name") or "",
                "email": r.get("email") or "",
                "score": r.get("overall_score"),
                "chapters_passed": r.get("chapters_passed"),
                "any_rereg": r.get("any_rereg"),
            })

    wb = Workbook()
    ws = wb.active
    ws.title = "Ranking"
    headers = ["Rank", "Username", "Student_id", "Full name", "Email", "Weighted score", "Chapters passed", "Re-registered"]
    ws.append(headers)
    for r in rows:
        ws.append([
            r["rank"], r["username"], r["student_id"], r["full_name"], r["email"],
            r["score"], r["chapters_passed"], "Yes" if r["any_rereg"] else "No",
        ])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = "signalsleuth_final_ranking.xlsx" if use_final else "signalsleuth_live_ranking.xlsx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.route("/admin/reports")
@admin_required
def admin_module_reports():
    return render_template("admin_module_reports.html", module="reports")


@bp.route("/admin/scoring")
@admin_required
def admin_module_scoring():
    return render_template(
        "admin_module_scoring.html",
        module="scoring",
        pass_percent=db.get_setting("pass_percent", "50"),
    )
