"""Read-only progress aggregation per student and chapter."""
from .core import get_conn, weighted_final_from_progress


def get_chapter_progress(user_id, chapter_num):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM chapter_progress WHERE user_id = %s AND chapter_num = %s",
                (user_id, chapter_num),
            )
            return c.fetchone()


def get_user_all_progress(user_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM chapter_progress WHERE user_id = %s ORDER BY chapter_num",
                (user_id,),
            )
            return c.fetchall()


def user_weighted_final(user_id):
    return weighted_final_from_progress(get_user_all_progress(user_id))
