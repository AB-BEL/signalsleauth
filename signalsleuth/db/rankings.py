"""Rankings, projections and weekly/final rank snapshots."""
from datetime import datetime
from .core import utcnow
from datetime import timedelta
from .core import CHAPTER_WEIGHTS, chapter_percent, get_conn, weighted_final_from_progress
from .progress import get_user_all_progress
from .chapters import get_season, season_has_ended


def ranking_for_chapter(chapter_num):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT cp.*, u.student_id, u.full_name, u.email, u.generated_username
                   FROM chapter_progress cp
                   JOIN users u ON u.id = cp.user_id
                   WHERE cp.chapter_num = %s""",
                (chapter_num,),
            )
            players = c.fetchall()

    # Sort by effective_score descending (full scores; admin may filter re-reg manually)
    players_sorted = sorted(
        players,
        key=lambda p: (-float(p.get("effective_score") or 0), str(p.get("student_id") or "")),
    )
    for i, p in enumerate(players_sorted, 1):
        p["rank"] = i
    return players_sorted


def overall_ranking():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT id AS user_id, student_id, full_name, email, generated_username, status_chapter, overall_points FROM users"
            )
            users = c.fetchall()
    players = []
    for u in users:
        prog = get_user_all_progress(u["user_id"])
        final, detail = weighted_final_from_progress(prog)
        players.append({
            **u,
            "overall_score": final,
            "raw_total": sum(r.get("total_score") or 0 for r in prog),
            "chapters_passed": sum(1 for r in prog if r.get("passed")),
            "any_rereg": 1 if any(r.get("is_rereg") for r in prog) else 0,
            "weight_detail": detail,
        })

    players_sorted = sorted(
        players,
        key=lambda p: (-float(p.get("overall_score") or 0), str(p.get("student_id") or "")),
    )
    for i, p in enumerate(players_sorted, 1):
        p["rank"] = i
    return players_sorted


def get_user_current_rank(user_id):
    ranks = overall_ranking()
    for p in ranks:
        if p["user_id"] == user_id:
            return p["rank"], p["overall_score"], len(ranks)
    return None, 0.0, len(ranks)


def projected_rank_if_pace(user_id):
    """Heuristic: assume remaining incomplete chapters eventually score at current average %."""
    ranks = overall_ranking()
    me = next((p for p in ranks if p["user_id"] == user_id), None)
    if not me:
        return None, None
    prog = get_user_all_progress(user_id)
    done_pcts = []
    for r in prog:
        if r.get("max_possible"):
            done_pcts.append(chapter_percent(r["total_score"], r["max_possible"]))
    avg = sum(done_pcts) / len(done_pcts) if done_pcts else 0.0
    # Project final with avg% on missing chapters
    by_ch = {int(r["chapter_num"]): r for r in prog}
    projected = 0.0
    for ch, w in CHAPTER_WEIGHTS.items():
        row = by_ch.get(ch)
        if row and row.get("max_possible"):
            eff = float(row.get("effective_score") or 0)
            mx = float(row["max_possible"])
            pct = (eff / mx) * 100.0
        else:
            pct = avg
        projected += pct * w
    # Simulate rank with projected score
    better = sum(1 for p in ranks if p["user_id"] != user_id and p["overall_score"] > projected)
    return better + 1, projected


def _iso_week_label(dt=None):
    dt = dt or utcnow()
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def _week_start_iso(dt=None):
    dt = dt or utcnow()
    start = dt.date() - timedelta(days=dt.weekday())
    return start.isoformat()


def list_snapshots(snapshot_type=None):
    with get_conn() as conn:
        with conn.cursor() as c:
            if snapshot_type:
                c.execute(
                    "SELECT * FROM rank_snapshots WHERE snapshot_type = %s ORDER BY week_start DESC, id DESC",
                    (snapshot_type,),
                )
            else:
                c.execute("SELECT * FROM rank_snapshots ORDER BY week_start DESC, id DESC")
            return c.fetchall()


def get_snapshot(snapshot_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM rank_snapshots WHERE id = %s", (snapshot_id,))
            snap = c.fetchone()
            if not snap:
                return None
            c.execute(
                """SELECT r.*, u.student_id, u.full_name, u.email, u.generated_username
                   FROM rank_snapshot_rows r
                   JOIN users u ON u.id = r.user_id
                   WHERE r.snapshot_id = %s
                   ORDER BY r.rank_pos ASC""",
                (snapshot_id,),
            )
            rows = c.fetchall()
            for r in rows:
                r["rank"] = r["rank_pos"]
            return {"snapshot": snap, "rows": rows}


def take_rank_snapshot(snapshot_type="weekly", week_label=None):
    label = week_label or (_iso_week_label() if snapshot_type == "weekly" else "FINAL")
    week_start = _week_start_iso() if snapshot_type == "weekly" else str(get_season().get("end_date") or utcnow().date())[:10]
    now = utcnow()
    ranking = overall_ranking()
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute(
                    """INSERT INTO rank_snapshots (week_label, week_start, snapshot_type, created_at)
                       VALUES (%s, %s, %s, %s)""",
                    (label, week_start[:10], snapshot_type, now),
                )
                sid = c.lastrowid
                for p in ranking:
                    c.execute(
                        """INSERT INTO rank_snapshot_rows
                           (snapshot_id, user_id, rank_pos, overall_score, chapters_passed, any_rereg)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (sid, p["user_id"], p["rank"], p["overall_score"], p.get("chapters_passed") or 0, p.get("any_rereg") or 0),
                    )
        return sid
    except Exception:
        return None


def ensure_weekly_snapshot():
    label = _iso_week_label()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT id FROM rank_snapshots WHERE week_label = %s AND snapshot_type = 'weekly'",
                (label,),
            )
            row = c.fetchone()
    if row:
        return row["id"]
    return take_rank_snapshot("weekly", label)


def ensure_final_snapshot():
    if not season_has_ended():
        return None
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id FROM rank_snapshots WHERE snapshot_type = 'final'")
            row = c.fetchone()
    if row:
        return row["id"]
    return take_rank_snapshot("final", "FINAL")


def get_user_rank_history(user_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT s.week_label, s.week_start, s.snapshot_type, s.created_at,
                          r.rank_pos AS `rank`, r.overall_score, r.chapters_passed
                   FROM rank_snapshot_rows r
                   JOIN rank_snapshots s ON s.id = r.snapshot_id
                   WHERE r.user_id = %s
                   ORDER BY s.week_start ASC, s.id ASC""",
                (user_id,),
            )
            return c.fetchall()


def overall_ranking_with_levels():
    """Overall ranking plus per-level best scores for display."""
    ranks = overall_ranking()
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                """SELECT user_id, chapter_num, level_num, best_score, max_score, attempts, cleared
                   FROM level_scores ORDER BY user_id, chapter_num, level_num"""
            )
            rows = c.fetchall()
    by_user = {}
    for r in rows:
        by_user.setdefault(r["user_id"], []).append(r)
    for p in ranks:
        levels = by_user.get(p["user_id"], [])
        p["level_scores"] = levels
        # compact string e.g. C1L1:12/30(2a)
        parts = []
        for lv in levels:
            parts.append(
                f"C{lv['chapter_num']}L{lv['level_num']}:{lv['best_score']}/{lv['max_score']}({lv['attempts']}a)"
            )
        p["level_scores_text"] = "; ".join(parts)
    return ranks
