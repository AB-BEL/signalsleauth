"""Connection handling, configuration, constants and small shared helpers."""
import os
import pymysql
from contextlib import contextmanager
from datetime import datetime, timezone
from pymysql.cursors import DictCursor

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# The built-in admin is created on first start. In production set
# ADMIN_INITIAL_PASSWORD; otherwise the default below is used and the admin
# is forced to change it at first login.
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin123"
INITIAL_ADMIN_PASS = os.environ.get("ADMIN_INITIAL_PASSWORD") or DEFAULT_ADMIN_PASS


CHAPTER_WEIGHTS = {
    1: 1 / 22, 2: 1 / 11, 3: 1 / 11, 4: 1 / 11, 5: 1 / 11,
    6: 1 / 11, 7: 2 / 22, 8: 1 / 11, 9: 1 / 11, 10: 3 / 22,
}


CHAPTER_TITLES = {
    1: "The Origins of the Discrete Domain",
    2: "Discrete-Time Signals and Systems",
    3: "The z-Transform",
    4: "Sampling of Continuous-Time Signals",
    5: "Transform Analysis of LTI Systems",
    6: "Structures for Discrete-Time Systems",
    7: "Filter Design Techniques",
    8: "The Discrete Fourier Transform",
    9: "Computation of the DFT",
    10: "Fourier Analysis of Signals Using the DFT",
}


def utcnow():
    """Naive UTC timestamp (same values as the deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_student_id(value):
    """Normalize IDs from Excel/forms: strip, drop trailing .0 from numeric cells."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() == "none":
        return ""
    # Excel often gives 12345.0 for integer IDs
    try:
        f = float(s)
        if f == int(f):
            s = str(int(f))
    except (ValueError, OverflowError):
        pass
    # collapse internal whitespace
    s = " ".join(s.split())
    return s


def _ssl_kwargs():
    """TLS options for managed MySQL (TiDB Cloud, Aiven, etc.).

    Enabled with MYSQL_SSL=1. Uses MYSQL_SSL_CA if given, otherwise the
    certifi bundle, and verifies both the certificate and the host name.
    """
    if os.environ.get("MYSQL_SSL", "").strip().lower() not in ("1", "true", "yes", "on"):
        return {}
    kw = {"ssl_verify_cert": True, "ssl_verify_identity": True}
    ca = os.environ.get("MYSQL_SSL_CA") or None
    if not ca:
        try:
            import certifi
            ca = certifi.where()
        except ImportError:
            pass
    if ca:
        kw["ssl_ca"] = ca
    return kw


def _cfg():
    return {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE", "signalsleuth"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
        "connect_timeout": int(os.environ.get("MYSQL_CONNECT_TIMEOUT", "10")),
        **_ssl_kwargs(),
    }


@contextmanager
def get_conn():
    conn = pymysql.connect(**_cfg())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping():
    """Return (ok, error_message). Used by the health endpoint."""
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT 1")
                c.fetchone()
        return True, ""
    except Exception as e:  # pragma: no cover - depends on DB state
        return False, str(e)[:200]


def as_date(val):
    """Normalize MySQL date/datetime/str/None -> datetime.date or None."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    # date type
    from datetime import date as date_cls
    if isinstance(val, date_cls):
        return val
    s = str(val).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def as_date_str(val):
    d = as_date(val)
    return d.isoformat() if d else ""


def chapter_weight(chapter_num):

    return CHAPTER_WEIGHTS.get(int(chapter_num), 0.0)


def chapter_percent(total_score, max_possible):
    if not max_possible:
        return 0.0
    return (float(total_score) / float(max_possible)) * 100.0


def weighted_final_from_progress(progress_rows):
    by_ch = {int(r["chapter_num"]): r for r in progress_rows}
    final = 0.0
    detail = []
    for ch, w in CHAPTER_WEIGHTS.items():
        row = by_ch.get(ch)
        if row and row.get("max_possible"):
            eff = float(row.get("effective_score") or 0)
            mx = float(row["max_possible"])
            pct = (eff / mx) * 100.0 if mx else 0.0
            raw_pct = chapter_percent(row.get("total_score") or 0, mx)
        else:
            pct = raw_pct = 0.0
        contrib = pct * w
        final += contrib
        detail.append({
            "chapter_num": ch, "weight": w, "raw_percent": raw_pct,
            "effective_percent": pct, "contribution": contrib,
            "has_score": bool(row and row.get("max_possible")),
        })
    return final, detail
