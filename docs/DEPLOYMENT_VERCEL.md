# Deploying Signal Sleuth on Vercel with a free MySQL database

This project is already prepared for Vercel. **You do not need to change any code.** Follow the steps in order. Total time: about 45 minutes the first time.

**What you will end up with**

| Part | Service | Cost |
|------|---------|------|
| Web app + API (Flask) | Vercel (Hobby plan) | Free |
| MySQL database | TiDB Cloud Starter (MySQL-compatible) | Free tier |
| Uploaded chapter games | Cloudflare R2 or Backblaze B2 (S3-compatible) | Free allowance |
| Mobile web app (optional) | Second Vercel project | Free |

> Free-tier terms change. Check each provider's pricing page when you sign up. Vercel's Hobby plan is for non-commercial use.

---

## Step 0. What you need before you start

1. A **GitHub** account.
2. A **Vercel** account (sign in with GitHub).
3. A **TiDB Cloud** account (tidbcloud.com).
4. An S3-compatible storage account (Cloudflare R2 or Backblaze B2). Some providers ask for a payment method even for the free allowance.
5. On your computer: **Python 3.10+** and **Git**. (Node.js 18+ only if you deploy the mobile app.)

---

## Step 1. Create the free MySQL database (TiDB Cloud Starter)

1. Sign in at tidbcloud.com and click **Create**. Choose **Starter** (MySQL-compatible). Name it `signalsleuth`.
2. Choose the **AWS region closest to your Vercel region**. Vercel functions run in Washington D.C. (`iad1`) by default, so choose **US East (N. Virginia)** if offered. Keeping them close makes every page faster.
3. Open the instance and click **Connect**. Generate the password and copy these four values into a safe place:
   - **Host** (like `gateway01.xx-xxxx-x.prod.aws.tidbcloud.com`)
   - **Port**: `4000` (not 3306)
   - **User**, including the prefix (like `abc123.root`)
   - **Password**
4. Open the **SQL Editor** and run:

```sql
CREATE DATABASE IF NOT EXISTS signalsleuth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

> TiDB requires encrypted connections. The project supports this with `MYSQL_SSL=1`.

## Step 2. Create the object storage bucket (for uploaded chapter games)

Vercel's disk is temporary, so games uploaded in the admin panel must live in object storage. (The built-in Chapter 1 game ships with the code and always works.)

1. Create a bucket, for example `signalsleuth-games`, at Cloudflare R2 or Backblaze B2.
2. Create an **access key** with read/write permission on that bucket.
3. Note: **bucket name**, **endpoint URL** (for R2 like `https://<account-id>.r2.cloudflarestorage.com`), **access key**, **secret key**.

## Step 3. Prepare the project on your computer

```bash
unzip SignalSleuth_modular_vercel.zip
cd SignalSleuth
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Edit `.env` and fill in:

```
SECRET_KEY=<a long random string>
MYSQL_HOST=<TiDB host>
MYSQL_PORT=4000
MYSQL_USER=<prefix>.root
MYSQL_PASSWORD=<TiDB password>
MYSQL_DATABASE=signalsleuth
MYSQL_SSL=1
```

To generate a good `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

## Step 4. Create the tables from your computer (one time)

Doing this once locally shows any problem immediately, instead of during a web request.

```bash
python scripts/init_db.py --check        # tests the connection
python scripts/init_db.py --seed-ids     # creates tables, default admin, chapters, season, and loads the student ID list
```

You should see `Connection OK. 24 tables: ...`. (Omit `--seed-ids` if you prefer to upload your own student list later from the admin panel.)

**Optional local test:** `python app.py`, then open http://127.0.0.1:5000. Press Ctrl+C to stop.

## Step 5. Put the project on GitHub

1. Create a **private** repository on GitHub (for example `signalsleuth`).
2. Check that `.env` is **not** committed (it is listed in `.gitignore`).

```bash
git init
git add .
git status          # make sure .env is NOT listed
git commit -m "Signal Sleuth"
git branch -M main
git remote add origin https://github.com/<you>/signalsleuth.git
git push -u origin main
```

## Step 6. Deploy on Vercel

1. Go to vercel.com → **Add New → Project** and import the GitHub repository.
2. Vercel detects **Flask** automatically. Leave *Build Command* and *Output Directory* empty and *Root Directory* as the repository root.
3. Open **Environment Variables** and add the following (for Production, Preview and Development):

| Name | Value |
|------|-------|
| `SECRET_KEY` | the same long random string as in `.env` (required: the app refuses to start without it) |
| `MYSQL_HOST` | TiDB host |
| `MYSQL_PORT` | `4000` |
| `MYSQL_USER` | `<prefix>.root` |
| `MYSQL_PASSWORD` | TiDB password |
| `MYSQL_DATABASE` | `signalsleuth` |
| `MYSQL_SSL` | `1` |
| `STORAGE_BACKEND` | `s3` |
| `S3_BUCKET` | bucket name |
| `S3_ENDPOINT_URL` | storage endpoint URL |
| `S3_ACCESS_KEY` | storage access key |
| `S3_SECRET_KEY` | storage secret key |
| `S3_REGION` | `auto` (R2) or your provider's region |
| `ADMIN_INITIAL_PASSWORD` | *(optional)* a strong first admin password; leave empty to use the default and be forced to change it |
| `CRON_SECRET` | a second random string (enables the daily ranking-snapshot job) |
| `APP_NAME` / `COURSE_NAME` | your branding |
| `SMTP_*` | *(optional)* only if you want registration / reset e-mails |

4. Click **Deploy**. When it finishes you get an address like `https://signalsleuth.vercel.app`.

Optional: in **Settings → Functions**, set the region to the one closest to your TiDB region.

## Step 7. Verify the deployment

1. Open `https://<your-app>.vercel.app/api/health`. Expect `"ok": true` and `"database": "up"`. (If it says `down`, see Troubleshooting.)
2. Open `/admin/login`. Sign in as **admin** with `ADMIN_INITIAL_PASSWORD`, or with `admin123` if you did not set one. In the second case the app **forces you to choose a new password immediately**.
3. Open `/admin/storage-status`. It should show `"backend": "s3"` and `"persistent": true`.
4. In the admin panel: set the season dates, upload your student list (Excel with columns `Student_id`, `name`, `sex`), and upload a test chapter HTML file. Wait a few minutes and confirm the chapter file is still there (this proves object storage works).
5. Register a test student with an ID from the list, play Chapter 1, and confirm the score appears on the dashboard and in the rankings.

## Step 8. (Optional) Deploy the mobile web app

The React mobile app must be its own Vercel project, because Vercel serves only one Flask app per project.

1. In Vercel click **Add New → Project** and import the **same** repository.
2. Set **Root Directory** to `mobile`. Framework: **Vite** (auto-detected). Build command `npm run build`, output `dist`.
3. Add environment variable `VITE_API_BASE` = `https://<your-flask-app>.vercel.app` (no trailing slash).
4. Deploy and test login and play on a phone.

The API already allows cross-origin requests, and embedded games authenticate with a signed token, so score saving works across the two domains.

## Step 9. Keep it healthy

- **Updates:** every `git push` to `main` redeploys automatically.
- **Backups:** run from your computer, for example monthly and before exams:

```bash
./scripts/backup_mysql.sh      # reads .env; uses TLS when MYSQL_SSL=1; needs the mysql client tools installed
```

  Also check which backup and restore features TiDB Cloud offers on your Starter instance.
- **Free-tier limits:** TiDB throttles when the monthly free allowance is used up. Watch usage in the TiDB console during exam weeks.
- **Schema changes:** edit `database/schema.sql` (or the `ensure_*` helpers in `signalsleuth/db/schema.py`), then run `python scripts/init_db.py` from your computer.
- **Scheduled snapshots:** `vercel.json` calls `/api/cron/weekly-snapshot` once a day. The job is safe to repeat and only works when `CRON_SECRET` is set.
- **Request size:** Vercel limits request bodies to about 4.5 MB, so the app limits uploads to 4 MB there. Chapter HTML files and Excel lists are far smaller.

## Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| Every page shows 500 and the logs say `SECRET_KEY is not set` | Add `SECRET_KEY` in Vercel and redeploy |
| `/api/health` says `database: down` | Wrong host/user/password, `MYSQL_PORT` not `4000`, or `MYSQL_SSL` not `1`. Re-run `python scripts/init_db.py --check` locally with the same values |
| `Access denied for user` | The TiDB user is missing its prefix, or the password was regenerated |
| `Unknown database` | Run the `CREATE DATABASE` statement from Step 1 |
| Tables missing | Run `python scripts/init_db.py` from your computer |
| Uploaded game disappears | `STORAGE_BACKEND=s3` and the `S3_*` variables are missing or wrong; check `/admin/storage-status` |
| Upload fails with 413 | File larger than about 4 MB |
| Game opens but score is not saved | Check the browser console. The game must be uploaded through the admin panel (it injects the score bridge automatically) |
| Mobile app: "Failed to fetch" | `VITE_API_BASE` wrong, ends with `/`, or uses `http://` |
| Everyone is logged out after a redeploy | `SECRET_KEY` changed. Keep one fixed value |
| Cron job returns 401 | `CRON_SECRET` not set in Vercel |

Logs: Vercel → your project → **Logs**.

## Appendix: running on other hosts

The same project runs on Render, Railway or a VPS: `pip install -r requirements-render.txt`, then `gunicorn app:app`. See `render.yaml` and `Procfile`.
