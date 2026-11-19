#!/usr/bin/env python3
"""Back up the PC server: database dump + uploaded chapter games, into backups/.

    python scripts/backup_pc.py

Needs the `mysqldump` program that comes with MariaDB / MySQL / XAMPP.
Old backups are deleted after BACKUP_KEEP_DAYS (default 14).
Restore the database with:
    mysql -u USER -p DATABASE < backups\\signalsleuth_YYYYMMDD-HHMMSS.sql
"""
import glob
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from signalsleuth import config  # noqa: E402  (loads .env)


def find_mysqldump():
    exe = shutil.which("mysqldump") or shutil.which("mariadb-dump")
    if exe:
        return exe
    patterns = [
        r"C:\xampp\mysql\bin\mysqldump.exe",
        r"C:\Program Files\MariaDB*\bin\mariadb-dump.exe",
        r"C:\Program Files\MariaDB*\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server*\bin\mysqldump.exe",
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def main():
    dump = find_mysqldump()
    if not dump:
        print("mysqldump not found. Add the MariaDB/MySQL 'bin' folder to PATH, or reinstall with the client tools.")
        return 1

    out_dir = Path(os.environ.get("BACKUP_DIR") or ROOT / "backups")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    db_name = os.environ.get("MYSQL_DATABASE", "signalsleuth")
    sql_file = out_dir / f"{db_name}_{stamp}.sql"

    env = dict(os.environ, MYSQL_PWD=os.environ.get("MYSQL_PASSWORD", ""))
    cmd = [
        dump, "-h", os.environ.get("MYSQL_HOST", "127.0.0.1"), "-P", os.environ.get("MYSQL_PORT", "3306"),
        "-u", os.environ.get("MYSQL_USER", "root"), "--single-transaction", "--routines",
        "--default-character-set=utf8mb4", "--result-file", str(sql_file), db_name,
    ]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print("Database dump FAILED:", res.stderr.strip())
        return 1
    print(f"Database  -> {sql_file} ({sql_file.stat().st_size:,} bytes)")

    games = config.UPLOAD_DIR
    files = [p for p in games.glob("*") if p.is_file() and p.name != ".gitkeep"] if games.exists() else []
    if files:
        zip_file = out_dir / f"chapter_games_{stamp}.zip"
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, p.name)
        print(f"Games     -> {zip_file} ({len(files)} files)")

    keep_days = int(os.environ.get("BACKUP_KEEP_DAYS", "14"))
    cutoff = time.time() - keep_days * 86400
    for p in out_dir.glob("*"):
        if p.suffix in (".sql", ".zip") and p.stat().st_mtime < cutoff:
            p.unlink()
            print("Removed old backup", p.name)
    print("Backup finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
