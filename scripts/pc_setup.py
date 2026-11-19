#!/usr/bin/env python3
"""One-time setup for running Signal Sleuth as a PC server.

    python scripts/pc_setup.py            interactive: writes .env, creates the database
    python scripts/pc_setup.py --check    only test the database connection
    python scripts/pc_setup.py --seed-ids also load database/seed/pre_users_seed.csv
    python scripts/pc_setup.py --internet configure the tunnel + Vercel proxy project settings in .env

It never overwrites an existing .env; edit that file by hand to change values.
"""
import argparse
import getpass
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENV = ROOT / ".env"


def ask(prompt, default="", secret=False):
    suffix = f" [{default}]" if default and not secret else ""
    fn = getpass.getpass if secret else input
    val = fn(f"{prompt}{suffix}: ").strip()
    return val or default


def write_env():
    if ENV.exists():
        print(f".env already exists, keeping it ({ENV}).")
        return
    print("\nDatabase connection (MariaDB / MySQL installed on this PC)")
    host = ask("  MySQL host", "127.0.0.1")
    port = ask("  MySQL port", "3306")
    user = ask("  MySQL user", "root")
    pw = ask("  MySQL password (hidden)", "", secret=True)
    name = ask("  Database name (created for you)", "signalsleuth")
    print("\nWebsite")
    app_name = ask("  Site name", "Signal Sleuth")
    course = ask("  Course name", "Your course")
    admin_pw = ask("  First admin password (blank = use admin123 and be forced to change it)", "", secret=True)
    web_port = ask("  Port students will use", "8000")

    ENV.write_text(
        "# Created by scripts/pc_setup.py. Edit freely; keep this file private.\n"
        f"SECRET_KEY={secrets.token_urlsafe(48)}\n"
        f"ADMIN_INITIAL_PASSWORD={admin_pw}\n"
        f"APP_NAME={app_name}\nCOURSE_NAME={course}\n"
        "\n# PC server\nAPP_ENV=production\nSESSION_COOKIE_SECURE=0\nHOST=0.0.0.0\n"
        f"PORT={web_port}\nTHREADS=8\nTRUST_PROXY=0\n"
        "\n# Database\n"
        f"MYSQL_HOST={host}\nMYSQL_PORT={port}\nMYSQL_USER={user}\nMYSQL_PASSWORD={pw}\nMYSQL_DATABASE={name}\nMYSQL_SSL=0\n"
        "\n# Files stay on this PC's disk\nSTORAGE_BACKEND=local\nPERSISTENT_DISK=1\n"
        "\nBACKUP_KEEP_DAYS=14\nADS_ENABLED=0\n",
        encoding="utf-8",
    )
    print(f"\nSaved {ENV}")


def read_env():
    values = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    return values


def update_env(updates):
    """Set KEY=value lines in .env (replace if present, append otherwise). Comments are kept."""
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    done = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}"
                done.add(key)
    missing = [k for k in updates if k not in done]
    if missing:
        lines += ["", "# Internet mode (added by setup_internet.bat)"] + [f"{k}={updates[k]}" for k in missing]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def configure_internet():
    """Prepare .env for: students -> Vercel proxy project -> tunnel -> this PC."""
    if not ENV.exists():
        print("Run setup_windows.bat first (no .env yet).")
        return 1
    cur = read_env()
    print("\nInternet access: how will the PC be reachable?")
    print("  1) ngrok            free permanent address (xxxx.ngrok-free.app); no domain purchase  [recommended]")
    print("  2) Cloudflare tunnel permanent address on a domain you own")
    print("  3) Cloudflare quick  TEST ONLY: random address that changes at every start")
    choice = ask("Choose 1, 2 or 3", "1")
    updates = {"TRUST_PROXY": "1"}
    origin_url = ""
    if choice == "2":
        updates["TUNNEL_PROVIDER"] = "cloudflared"
        host = ask("  Public hostname you created in Cloudflare (for example sleuth.example.com)").replace("https://", "").strip("/ ")
        updates["CLOUDFLARE_TUNNEL_TOKEN"] = ask("  Tunnel token (hidden; from the Cloudflare dashboard)", cur.get("CLOUDFLARE_TUNNEL_TOKEN", ""), secret=True)
        origin_url = f"https://{host}" if host else ""
    elif choice == "3":
        updates["TUNNEL_PROVIDER"] = "cloudflared-quick"
    else:
        updates["TUNNEL_PROVIDER"] = "ngrok"
        domain = ask("  Your ngrok static domain (for example my-name.ngrok-free.app)", cur.get("NGROK_DOMAIN", "")).replace("https://", "").strip("/ ")
        updates["NGROK_DOMAIN"] = domain
        origin_url = f"https://{domain}" if domain else ""
    if origin_url:
        updates["TUNNEL_PUBLIC_URL"] = origin_url

    lan = ask("Also let students on the LAN sign in directly over plain http? (y/N)", "n").lower().startswith("y")
    updates["SESSION_COOKIE_SECURE"] = "0" if lan else "1"
    front = ask("Your Vercel address if it already exists, e.g. https://signalsleuth-web.vercel.app (blank = later)", cur.get("FRONT_URL", "")).strip().rstrip("/")
    if front:
        updates["FRONT_URL"] = front
    secret = cur.get("ORIGIN_SECRET") or secrets.token_urlsafe(32)
    updates["ORIGIN_SECRET"] = secret
    update_env(updates)

    print("\n" + "=" * 64)
    print(" Internet mode is configured in .env")
    print("=" * 64)
    print(" Put these two values in Vercel (signalsleuth-vercel-proxy project, Settings, Environment Variables):\n")
    print(f"   ORIGIN_URL    = {origin_url or '(the tunnel address; the quick tunnel prints it when it starts)'}")
    print(f"   ORIGIN_SECRET = {secret}\n")
    print(" Keep ORIGIN_SECRET private. Next: start_all.bat, then deploy the separate signalsleuth-vercel-proxy project on Vercel.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only test the database connection")
    ap.add_argument("--seed-ids", action="store_true", help="load database/seed/pre_users_seed.csv")
    ap.add_argument("--internet", action="store_true", help="configure internet mode (tunnel + Vercel proxy project)")
    args = ap.parse_args()

    if args.internet:
        return configure_internet()

    if not args.check:
        write_env()

    from signalsleuth import config, db  # imported after .env exists

    cfg = db._cfg()
    print(f"\nDatabase: {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}")
    if args.check:
        ok, err = db.ping()
        print("Connection OK" if ok else f"FAILED: {err}")
        return 0 if ok else 1

    db.init_db()  # creates the database if needed, then tables and defaults
    ok, err = db.ping()
    if not ok:
        print("FAILED:", err)
        print("Check that MariaDB/MySQL is running and the user/password in .env are right.")
        return 1
    print("Database ready (tables, admin account, chapters).")

    if args.seed_ids:
        import csv
        seed = config.SEED_DIR / "pre_users_seed.csv"
        entries = []
        with open(seed, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sid = (row.get("Student_id") or row.get("student_id") or "").strip()
                if sid:
                    entries.append((sid, (row.get("name") or "").strip(), (row.get("sex") or "").strip()))
        added, skipped = db.add_pre_users(entries)
        print(f"Student IDs: {added} added, {skipped} already present.")

    print("\nSetup complete. Start the server with start_server.bat (or: python pc_server.py).")
    print(f"Admin sign-in: /admin/login   user: {db.DEFAULT_ADMIN_USER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
