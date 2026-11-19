# Free hosting & withdrawing the service yourself

You remain the owner of the deployment. Nothing is locked to a vendor beyond your account.

## Recommended free path (you can stop anytime)

### Option A — Render (free web service)
1. Push this project to **your** GitHub repo (private recommended).
2. Render → New Web Service → connect that repo.
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn -b 0.0.0.0:$PORT app:app --workers 2 --timeout 120`
5. Set env: `SECRET_KEY`, `MYSQL_*`, prefer `STORAGE_BACKEND=s3` for game files.
6. Use a free/low-cost **managed MySQL** (or campus MySQL reachable from Render).

**Withdraw:** Render Dashboard → your service → **Suspend** or **Delete**.  
That stops the public URL. Delete the GitHub repo or MySQL instance separately if you also want data gone.

### Option B — Railway / PythonAnywhere
Same idea: your account, your env vars, **Delete project** when finished.

### Option C — Campus/VPS free tier
Run `python app.py` or Gunicorn behind HTTPS; stop the process or remove the DNS record to withdraw.

## Data when you withdraw
- App offline ≠ automatic DB wipe. Delete the MySQL database and S3 bucket if you need full erasure.
- Run `./scripts/backup_mysql.sh` before shutdown if you want an archive.

## Updating later
- Code: git push → host auto-deploy (if connected).
- Courses/games: admin UI only (HTML + questions).

## Future ads / business links
Defaults: `ADS_ENABLED=0`. When ready, set env and use `monetization.py` hooks — not required for teaching mode.
