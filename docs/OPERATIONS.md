# Signal Sleuth — Hosting, Storage, Backups & Maintenance

## 1. The ephemeral disk problem

Many free PaaS plans (including **Render free**) give the web process a disk that is **wiped on redeploy or restart**.  
If chapter HTML games are stored only under `uploads/chapters/`, they **disappear** after restart even though MySQL still has the `game_filename` reference.

**Mitigations (pick one):**

| Approach | When to use |
|----------|-------------|
| **S3-compatible object storage** (`STORAGE_BACKEND=s3`) | Recommended for PaaS / multiple instances |
| **Persistent disk** attached to the service (`PERSISTENT_DISK=1`) | VPS, Render paid disk, Railway volume |
| **Re-upload after each deploy** | Emergency only — not a strategy |

### Object storage setup (Cloudflare R2, AWS S3, MinIO, B2)

```env
STORAGE_BACKEND=s3
S3_BUCKET=your-bucket
S3_ENDPOINT_URL=https://xxxx.r2.cloudflarestorage.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=auto
S3_PREFIX=signalsleuth/games/
```

Uploads go to the bucket; the app also keeps a **local cache** for fast HTML injection.  
Admin can check `/admin/storage-status` (JSON).

## 2. Managed MySQL

Do **not** run production MySQL only inside an ephemeral container without volumes.

Recommended:

- **Managed MySQL** (PlanetScale alternatives, Aiven, AWS RDS, Azure Database, Railway MySQL, etc.)
- Or a **VM with scheduled snapshots** and documented restore

Connection is always via `MYSQL_*` environment variables (never hard-code passwords in Git).

## 3. Automated daily backups

Script: `scripts/backup_mysql.sh`

```bash
chmod +x scripts/backup_mysql.sh scripts/restore_mysql.sh
# crontab — 03:15 UTC daily
15 3 * * * /opt/SignalSleuth/scripts/backup_mysql.sh >> /var/log/signalsleuth-backup.log 2>&1
```

Produces gzipped dumps under `backups/` (or `BACKUP_DIR`) and optionally uploads them to the same S3 bucket under `.../backups/`.  
Retention: `BACKUP_KEEP_DAYS` (default 14).

## 4. Periodic restoration tests

At least **monthly** on a **staging** database:

```bash
./scripts/restore_mysql.sh backups/signalsleuth_YYYYMMDDTHHMMSSZ.sql.gz
# Then smoke-test: admin login, student login, rankings, play level, PDF feedback
```

Document the date of the last successful restore in your ops log.

## 5. Version control (Git)

```bash
cd SignalSleuth
git init
git add .
git commit -m "Signal Sleuth production baseline"
# push to private GitHub/GitLab
```

`.gitignore` excludes `.env`, `backups/`, `node_modules/`, and local upload cache.  
**Never commit** secrets or live student data dumps to a public repo.

## 6. Database migrations (Flask-Migrate / Alembic)

- Baseline schema: `schema.sql` + runtime `db.ensure_*` helpers  
- Tooling: `migrations/` (Alembic) + dependencies in `requirements.txt`

```bash
export FLASK_APP=app.py
# After adding a new revision under migrations/versions/:
alembic -c migrations/alembic.ini upgrade head
```

**Release rule:** schema changes ship as a new Alembic revision; run `upgrade` before or during deploy.

## 7. Release & maintenance checklist

1. Tag release in Git (`v1.x.y`)  
2. Set env on host (SECRET_KEY, MYSQL_*, STORAGE_*)  
3. `pip install -r requirements.txt`  
4. Run migrations / confirm `schema.sql` applied on new envs  
5. Deploy app (Gunicorn)  
6. Confirm `/api/health` and `/admin/storage-status`  
7. Smoke-test register → play → score → rankings  
8. Verify cron backup ran within 24h  
9. Quarterly: dependency updates (`pip` / `npm audit`)

## 8. What the software now supports

- **Local or S3** game package storage (`storage.py`)  
- **mysqldump** backup + restore scripts  
- **Alembic** project layout for future schema revisions  
- **Render** blueprint defaults `STORAGE_BACKEND=s3` so free-disk loss is avoided when S3 is configured  
