#!/usr/bin/env python3
"""Create / verify the Signal Sleuth database from your own computer.

Run this ONCE before the first deployment (and again after changing
database/schema.sql). It is idempotent: existing tables and data are kept.

    python scripts/init_db.py              # create schema + default admin/chapters/season
    python scripts/init_db.py --seed-ids   # ...and load database/seed/pre_users_seed.csv
    python scripts/init_db.py --check      # only test the connection and list tables

Connection settings come from .env or the environment (MYSQL_HOST, MYSQL_PORT,
MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_SSL=1 for managed databases).
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from signalsleuth import config, db  # noqa: E402


def list_tables():
    with db.get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SHOW TABLES")
            return sorted(next(iter(r.values())) for r in c.fetchall())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only test the connection")
    ap.add_argument("--seed-ids", action="store_true", help="load database/seed/pre_users_seed.csv")
    args = ap.parse_args()

    cfg = db._cfg()
    print(f"Database: {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}  TLS={'on' if 'ssl_ca' in cfg or cfg.get('ssl_verify_cert') else 'off'}")
    ok, err = db.ping()
    if not ok and args.check:
        print("FAILED:", err)
        return 1

    if not args.check:
        db.init_db()
        print("Schema and seed data ready.")
        if args.seed_ids:
            seed = config.SEED_DIR / "pre_users_seed.csv"
            entries = []
            with open(seed, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    sid = (row.get("Student_id") or row.get("student_id") or "").strip()
                    if sid:
                        entries.append((sid, (row.get("name") or "").strip(), (row.get("sex") or "").strip()))
            added, skipped = db.add_pre_users(entries)
            print(f"Student IDs: {added} added, {skipped} already present.")

    ok, err = db.ping()
    if not ok:
        print("FAILED:", err)
        return 1
    tables = list_tables()
    print(f"Connection OK. {len(tables)} tables: {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
