# Signal Sleuth (modular: your own PC server, reachable from anywhere, or fully on Vercel)

Multi-user educational game platform: Flask + MySQL, HTML chapter games, server-side scoring, league rankings, admin console, optional React mobile client.

**Three ways to run it** (same code):
1. **PC server on the internet (main route):** the app and database run on your PC; a tunnel plus the separate `signalsleuth-vercel-proxy` project (its own GitHub repo, shipped next to this folder) give students a public `https://<name>.vercel.app` address. Follow `docs/INTERNET_ACCESS.md` (PDF: `docs/SignalSleuth_PC_Internet_Guide_v2.pdf`).
2. **PC server on a classroom LAN only:** follow `docs/PC_SERVER.md` (Windows: `setup_windows.bat`, then `start_server.bat`).
3. **Everything on Vercel (cloud database):** follow `docs/DEPLOYMENT_VERCEL.md` (Vercel + TiDB Cloud + S3-compatible storage).

**Code layout:** `docs/MODULAR_REFACTOR.md`.

## Project layout

```
app.py                  entry point (Vercel / gunicorn / quick local test)
pc_server.py            PC / LAN server (Waitress)
setup_windows.bat, start_server.bat, open_firewall.bat, backup_windows.bat   Windows helpers for the PC server
setup_internet.bat, start_tunnel.bat, start_all.bat, check_internet.bat      internet mode (tunnel + the separate Vercel proxy project)
signalsleuth/           application package (config, db/, services/, web/, blueprints/)
templates/              Jinja templates
public/static/          static files (bridge script for games); served by Vercel CDN, and by Flask locally
games/                  bundled game files (read-only)
database/               schema.sql and seed/ (student ID list)
scripts/                init_db.py, pc_setup.py, pc_tunnel.py, backup_pc.py, backup_mysql.sh, restore_mysql.sh
tests/                  pytest suite
mobile/                 React (Vite) mobile client, deployed as a separate project
docs/                   guides and original manuals
vercel.json             Vercel function settings and daily cron
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # fill in MYSQL_* and SECRET_KEY
python scripts/init_db.py --seed-ids                   # create tables + load student IDs
python app.py                                          # quick test, this computer only: http://127.0.0.1:5000
# classroom / LAN server:  python pc_server.py  (see docs/PC_SERVER.md)
```

Admin: `/admin/login`. The built-in `admin` account starts with the factory password and **must change it at first login** (or set `ADMIN_INITIAL_PASSWORD`).

## Tests

Use a throw-away database:

```bash
pip install -r requirements-dev.txt
export MYSQL_HOST=127.0.0.1 MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=signalsleuth_test
pytest -q
```

## Admin flow

1. Sign in at `/admin/login`.
2. Upload students (Excel `.xlsx` with `Student_id`, `name`, `sex`, or CSV / paste).
3. Set season dates and chapter deadlines; upload chapter HTML games.
4. Handle password resets; view rankings, snapshots and reports.

## Student flow

Register only if the Student ID was uploaded; sign in with email and password; play active chapters within deadlines; scores feed the weighted final and the league table.

## Ranking rules

Weighted final: Ch1 x 1/22 ... Ch10 x 3/22. Re-registration: effective score x 4/5. Weekly snapshots plus an end-of-season final board.
