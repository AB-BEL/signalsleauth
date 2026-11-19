"""Central configuration: environment variables and filesystem locations.

Nothing here touches the network or the database, so it is safe to import
anywhere. Runtime flags are plain module attributes read once at start-up.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional in production
    pass


def _flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ── Paths ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent          # project root
TEMPLATES_DIR = BASE_DIR / "templates"
PUBLIC_DIR = BASE_DIR / "public"                            # served by the Vercel CDN
STATIC_DIR = PUBLIC_DIR / "static"                          # also served by Flask locally
MOBILE_DIST_DIR = STATIC_DIR / "mobile"                     # optional built React app at /m/
GAMES_DIR = BASE_DIR / "games"                              # bundled, read-only game files
SEED_DIR = BASE_DIR / "database" / "seed"

# ── Runtime environment ─────────────────────────────────────
IS_VERCEL = bool(os.environ.get("VERCEL"))
IS_PRODUCTION = IS_VERCEL or os.environ.get("APP_ENV", "").strip().lower() == "production"

# Browsers drop "Secure" cookies on plain http, so a PC server on the school LAN
# (http://192.168.x.x) must run with SESSION_COOKIE_SECURE=0. Defaults to on for
# Vercel / production and off for local use; set it explicitly to override.
SESSION_COOKIE_SECURE = _flag("SESSION_COOKIE_SECURE", default=IS_PRODUCTION)

# Internet mode (PC server behind a tunnel + the Vercel proxy project).
# When set, any request that arrives through the tunnel must carry this secret in the
# X-Origin-Secret header (the Vercel front adds it). Direct LAN requests are unaffected.
ORIGIN_SECRET = os.environ.get("ORIGIN_SECRET", "").strip()

# Vercel's filesystem is read-only except /tmp (and /tmp is not shared
# between instances), so runtime writes go there.
WRITABLE_DIR = Path("/tmp") if IS_VERCEL else BASE_DIR
UPLOAD_DIR = WRITABLE_DIR / "uploads" / "chapters"

# ── Security ────────────────────────────────────────────────
DEV_SECRET_KEY = "signal-sleuth-dev-key-change-me"
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
CRON_SECRET = os.environ.get("CRON_SECRET", "").strip()

# ── Database start-up behaviour ─────────────────────────────
# auto   : serverless -> create schema only if the DB is empty (one cheap probe)
#          other hosts -> run the idempotent schema on every start (original behaviour)
# always : always run the full idempotent schema on start
# never  : never touch the schema at start-up (use scripts/init_db.py instead)
DB_INIT = os.environ.get("DB_INIT", "auto").strip().lower()
if _flag("SKIP_DB_INIT"):
    DB_INIT = "never"

# ── Uploads ─────────────────────────────────────────────────
# Vercel Functions reject request bodies above roughly 4.5 MB.
MAX_CONTENT_LENGTH = (4 if IS_VERCEL else 16) * 1024 * 1024


def validate():
    """Fail fast on unsafe production settings."""
    if IS_PRODUCTION and (not SECRET_KEY or SECRET_KEY == DEV_SECRET_KEY):
        raise RuntimeError(
            "SECRET_KEY is not set. Set a long random SECRET_KEY environment variable "
            "(it signs login sessions and mobile tokens)."
        )
