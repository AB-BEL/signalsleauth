# Signal Sleuth: PC server on the internet

_Run Signal Sleuth on your own PC and reach it from anywhere through ngrok and a separate Vercel proxy project_

## 1. What changed, and why the 404 happened

In the first version I put the Vercel proxy as a **`web-proxy` subfolder inside the big project** and told you to push the whole project to GitHub. That layout is the most likely reason Vercel answered **404**. I cannot see your Vercel project, so I cannot prove which cause hit you, but two things in my layout could each produce it, and both are removed in this version:

- The root `.vercelignore` that I added listed `web-proxy/`. When the project is deployed from that repository, Vercel can end up with **no function at all**, and then every address answers `404: NOT_FOUND`.
- The function assumed Vercel passes the original path to it after a rewrite. If it receives the rewrite's destination instead, the proxy would ask your PC for `/api/proxy`, and Flask answers **Not Found**.

Your ChatGPT package already contained the two good ideas that fix this: a **separate repository that contains only the proxy**, and passing the original path in a query parameter (`__proxy_path`). I kept both and strengthened the rest:

| Area | This version |
|---|---|
| Separate repository | The proxy lives alone in `signalsleuth-vercel-proxy/`. **Only this small folder goes to GitHub and Vercel.** The full PC application never leaves your PC. |
| Path handling | The original path comes from `__proxy_path`; the query string is forwarded byte-for-byte; trailing slashes are kept; a visitor cannot change the target by adding their own `__proxy_path`. |
| Built-in diagnostics | `/__front/debug` works with no PC and no tunnel, and shows what the function sees (never the secret). The same page works directly at `/api/proxy?__proxy_path=/__front/debug`, which separates 'function missing' from 'rewrite missing'. |
| PC application | `/m` no longer depends on a trailing slash; `check_internet.bat` also tests your Vercel address; nothing in the PC folder is named `web-proxy` any more. |
| Tests | 22 proxy checks (including a simulated Vercel rewrite) plus 21 application tests, and a run of the real application behind the proxy. |
| This guide | A 404 decision tree (section 10) tells you which of the causes you have. |

## 2. What you are building

```
student (anywhere)
      |  https
      v
https://your-name.vercel.app          Vercel project (tiny proxy, holds no data)
      |  https + secret key
      v
https://your-name.ngrok-free.app      ngrok tunnel (outbound from your PC)
      |
      v
Your Windows PC: Signal Sleuth (port 8000) + MariaDB/MySQL
```

| Folder | Where it lives | On GitHub? |
|---|---|---|
| **SignalSleuth/** (the application) | Your PC, for example `C:\SignalSleuth` | **No.** It contains your database password and secret in `.env` |
| **signalsleuth-vercel-proxy/** (the proxy) | Extracted anywhere, then pushed as its own repository | **Yes**, alone, as the repository root |

> **Honest limits.** **The PC must be on and online** whenever students use the site; otherwise they see an 'offline' page. Speed depends on your upload bandwidth. A single request through Vercel is limited to about 4.4 MB (scores, Excel lists and normal games are fine; for larger uploads use `http://localhost:8000/admin` on the PC). Vercel's Hobby plan is for non-commercial use, and free-tier limits of ngrok and Vercel change, so check their pricing pages.

## 3. Accounts and software

| You need | Where | Used for |
|---|---|---|
| Python 3.10+ | python.org/downloads (tick 'Add python.exe to PATH') | Running the server |
| MariaDB (or MySQL / XAMPP) | mariadb.org/download (write down the root password) | Database |
| Node.js 22 LTS (optional) | nodejs.org | Only to run the proxy's self-test on your PC |
| Git for Windows | git-scm.com | Uploading the proxy to GitHub |
| GitHub account | github.com | Vercel imports the proxy from here |
| Vercel account | vercel.com (sign in with GitHub) | Public address |
| ngrok account | ngrok.com | Free tunnel with a permanent address |

No domain purchase is needed with ngrok. If you own a domain you may use a Cloudflare named tunnel instead (Part B, option 2).

## 4. Part A: set up the PC server

1. Install **Python** (tick **Add python.exe to PATH**) and **MariaDB** (set and remember the root password; keep 'Install as service'). Check: `python --version`; `services.msc` shows MariaDB **Running**.
2. Create `C:\SignalSleuth` and extract the **SignalSleuth** folder from the zip so that **app.py is directly inside it**.
3. Double-click **setup_windows.bat**. Answer the prompts (MySQL user `root`, your password, press Enter for the rest). It ends with `Setup complete`.
4. Double-click **start_server.bat**. Open **http://localhost:8000/api/health**: expect `"ok": true` and `"database": "up"`.
5. Open **http://localhost:8000/admin/login**, sign in as `admin` (default `admin123`; you must change it), set the season dates and upload your student list.

> **Checkpoint.** Continue only when the health page shows ok and database up.

## 5. Part B: prepare the tunnel

### Option 1: ngrok (recommended)

1. Sign in at **ngrok.com**. Download **ngrok for Windows** from its setup page and put `ngrok.exe` in `C:\SignalSleuth\tools\` (create the folder), or install it from the Microsoft Store.
2. On the ngrok dashboard copy your **authtoken**. In Command Prompt run once: `ngrok config add-authtoken YOUR_TOKEN`
3. On the dashboard open the **Domains** page and create your free static domain, for example `friendly-name-1234.ngrok-free.app`. **Write it down.** This permanent address is your `ORIGIN_URL`.

> **Older ngrok versions.** Current ngrok starts a fixed domain with `--url`. If it says 'unknown flag --url', add `NGROK_URL_FLAG=domain` to `.env`.

### Option 2: Cloudflare named tunnel (needs a domain you own)

1. Add your domain to a free Cloudflare account and install **cloudflared**.
2. In the dashboard open **Zero Trust**, **Networks**, **Tunnels**, create a **Cloudflared** tunnel and copy its **token** (do not run their service-install command).
3. On the tunnel's **Public Hostname** tab add `sleuth.yourdomain.com` with service **HTTP** and URL **localhost:8000**.

Menu names change from time to time; the idea stays the same. A Cloudflare quick tunnel (random address on every start) is for tests only, because you would have to update Vercel and redeploy every time.

## 6. Part C: connect the PC to the tunnel

1. Double-click **setup_internet.bat**. Choose **1** (ngrok) and enter your ngrok domain.
2. When asked whether LAN students may also sign in over plain http, answer **n** (safer).
3. When asked for your Vercel address, press Enter now (you will add it after Part E).
4. The script prints two values. **Copy them to Notepad; you need them in Part E:**

```
ORIGIN_URL    = https://friendly-name-1234.ngrok-free.app
ORIGIN_SECRET = (a long random string)
```

`ORIGIN_SECRET` is the key that makes the PC accept tunnel traffic only from **your** Vercel project. Anyone who finds the ngrok address by itself gets **403 Forbidden**.

5. Close the earlier server window, then double-click **start_all.bat**. Two windows open: the server and the tunnel. Keep both open.
6. Double-click **check_internet.bat**. Expect:

```
Local server       : 200 (expect 200)
Tunnel + secret    : 200 (expect 200)
Tunnel, no secret  : 403 (expect 403 - proves strangers cannot use the tunnel directly)
Vercel address     : not tested (add FRONT_URL=... to .env after you deploy it)
```

> **If a line is wrong.** Local not 200: start the server and MariaDB. Tunnel + secret not 200: read the tunnel window (wrong authtoken, wrong domain). No 403: `ORIGIN_SECRET` is empty in `.env`; run setup_internet.bat again.

## 7. Part D: put the proxy on GitHub (its own repository)

1. Extract **signalsleuth-vercel-proxy** anywhere, for example `C:\Users\YOU\Documents\signalsleuth-vercel-proxy`. Open it: you must see **api**, **public**, **test**, **package.json** and **vercel.json** immediately inside.
2. (Optional) With Node.js installed, open PowerShell in that folder and run `npm test`. Expect `All 22 checks passed.` This tests the proxy against a simulated PC and a simulated Vercel rewrite.
3. On github.com create a **Private** repository named `signalsleuth-vercel-proxy`. **Do not** add a README, .gitignore or license: it must be empty.
4. Open Command Prompt **inside the proxy folder** (File Explorer: click the address bar, type `cmd`, Enter) and run:

```
git init
git add .
git status
git commit -m "Signal Sleuth Vercel proxy"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/signalsleuth-vercel-proxy.git
git push -u origin main
```

5. Open the repository in your browser. Its **front page must show `api/`, `public/`, `test/`, `package.json` and `vercel.json` directly**. If you see a single folder instead, you pushed the parent folder; delete the repository contents and push again from inside the proxy folder.

| Message | Fix |
|---|---|
| `non-fast-forward` (push rejected) | The repository was not empty. Create a fresh empty one, or `git pull --rebase origin main` then push |
| `Repository not found` | Wrong URL or account. `git remote -v`; fix with `git remote set-url origin URL`; clear old logins in Windows Credential Manager (git:https://github.com) |
| `cannot rename the current branch while not on any` | Detached HEAD: `git rebase --abort` if needed, then `git checkout -b main` |
| `nothing to commit, working tree clean` | Not an error. If GitHub lacks the files, run `git push` |

> **Never upload secrets.** The proxy repository contains no secrets. Never put `.env`, `ORIGIN_SECRET`, the ngrok authtoken or a Cloudflare token on GitHub.

## 8. Part E: create the Vercel project

> **Start clean.** If you created a Vercel project from the old layout, **delete it** (Project, Settings, General, Delete Project) so no old settings carry over. Do not touch your separate mobile project.

1. On vercel.com choose **Add New**, then **Project**, and **Import** the `signalsleuth-vercel-proxy` repository.
2. On the Configure Project screen set exactly:

| Setting | Value |
|---|---|
| Project Name | `signalsleuth-web` (any free name; it becomes `signalsleuth-web.vercel.app`) |
| Framework Preset | **Other** |
| Root Directory | **`./`** (the repository root; do not pick a subfolder) |
| Build Command | empty (override off) |
| Output Directory | empty (override off) |
| Install Command | default |

3. Open **Environment Variables** and add both, for **Production** (add Preview too only if you will use preview deployments). No quotes, no trailing slash:

| Name | Value |
|---|---|
| `ORIGIN_URL` | `https://friendly-name-1234.ngrok-free.app` (your ngrok domain, https) |
| `ORIGIN_SECRET` | The long string from Part C, identical to `ORIGIN_SECRET` in the PC's `.env` |

5. Click **Deploy** and wait for **Ready**.
6. Open the deployment, then its **Source** tab and confirm it lists `api/proxy.js` and `vercel.json`. Open **Functions** (or **Resources**) and confirm `api/proxy.js` appears.

> **Use the production address.** Students must use the project's main domain (Settings, Domains, for example `signalsleuth-web.vercel.app`). Long deployment-specific addresses can be protected by Vercel login and show an 'Authentication Required' page.

## 9. Test in this order

Replace `NAME` with your Vercel domain. Run **start_all.bat** on the PC first.

| Test | Open | Expected |
|---|---|---|
| **1. Function exists** | `https://NAME.vercel.app/__front/debug` | JSON with `"pathSource": "query"`, `"hasOriginUrl": true`, `"hasOriginSecret": true`. Works even if the PC is off |
| **2. Chain is up** | `https://NAME.vercel.app/__front/health` | `"origin": "up"` |
| **3. Home page** | `https://NAME.vercel.app/` | The Signal Sleuth home page |
| **4. API** | `https://NAME.vercel.app/api/health` | The PC's health JSON |
| **5. Real use** | A phone on **mobile data** (Wi-Fi off) | Register a test student, play Chapter 1, see the score |
| **6. Admin** | `https://NAME.vercel.app/admin/login` | Dashboard opens |

Finally add `FRONT_URL=https://NAME.vercel.app` as a new line in `C:\SignalSleuth\.env` and run **check_internet.bat**; the last line should now read `Vercel address: 200`.

> **Success.** When tests 1 to 6 pass, students anywhere can use your PC through the Vercel address. Share it (and a QR code made from it).

> **After changing an environment variable.** Vercel applies new values only to new deployments: Project, **Deployments**, the latest one's menu, **Redeploy**.

## 10. If you see a 404 (decision tree)

| What you see | What it means | What to do |
|---|---|---|
| Vercel's own page **404: NOT_FOUND** with a Code/ID line | Vercel found no function or route: the project has no `api/proxy.js` or no `vercel.json` | Deployment, **Source** tab must list `api/proxy.js` and `vercel.json`. Root Directory must be `./`, Framework **Other**. Check the GitHub front page (section 7, step 5). Make sure there is **no `.vercelignore`** listing `api`. Fix, then Redeploy. If settings were wrong from an earlier attempt, delete the project and import again |
| `/api/proxy?__proxy_path=/__front/debug` works, but `/__front/debug` gives 404 | The function is deployed but the **rewrite** is not active | `vercel.json` must be at the repository root and valid JSON. Redeploy |
| `/__front/debug` works but pages show plain **Not Found** (a short white page) | The request reached your PC but for a path that does not exist | Compare `resolvedPath` in the debug output with `http://localhost:8000/` + the same path. A bad link, or a feature not built (for example `/m/` needs the mobile app built) |
| Our page **Routing problem** | The function was opened without its original path | Open normal pages through the rewrite; check `vercel.json` is at the root; Redeploy |
| Page **The server is offline right now** (503) | PC off, server or tunnel window closed, or ngrok domain mismatch | Run `start_all.bat`; `check_internet.bat`; make sure `ORIGIN_URL` equals your ngrok domain exactly |
| Plain **Forbidden** (403) | `ORIGIN_SECRET` differs between Vercel and `.env` | Make them identical, restart the PC server, Redeploy Vercel |
| Vercel login / **Authentication Required** | You opened a protected deployment address | Use the main domain from Settings, Domains |

## 11. Daily operation

### Start, stop, start automatically

- Start: **start_all.bat** (server + tunnel windows). Keep both open during class. Stop: close them.
- The tunnel program restarts itself if the connection drops.

```
schtasks /create /tn "SignalSleuth" ^
  /tr "C:\SignalSleuth\start_all.bat" ^
  /sc onlogon /rl highest
```

Run that once in an **administrator** Command Prompt. For an unattended PC also enable automatic sign-in (Win+R, `netplwiz`) and set Sleep to **Never**. MariaDB already starts with Windows.

### Backups and updates

- **backup_windows.bat** writes the database and uploaded games to `backups\`. Copy it to a USB drive or cloud folder before every exam week.
- Application update: replace files in `C:\SignalSleuth` and restart `start_all.bat`.
- Proxy update: edit the proxy folder, then `git add .`, `git commit -m "..."`, `git push`; Vercel redeploys by itself.

### Change the tunnel address or the secret

- New tunnel address: update **ORIGIN_URL** in Vercel and **Redeploy**.
- New secret: delete the `ORIGIN_SECRET=` line in `.env`, run setup_internet.bat, restart the PC server, update **ORIGIN_SECRET** in Vercel and Redeploy.

## 12. More troubleshooting

| Symptom | Cause and fix |
|---|---|
| ngrok: authentication failed | `ngrok config add-authtoken YOUR_TOKEN` again |
| ngrok: unknown flag `--url` | Add `NGROK_URL_FLAG=domain` to `.env`, restart the tunnel |
| ngrok: domain not found or not owned | `NGROK_DOMAIN` in `.env` must equal the domain on your ngrok dashboard exactly |
| `/__front/health` says **Not configured** (500) | Add `ORIGIN_URL` and `ORIGIN_SECRET` in Vercel (https, no trailing slash), then Redeploy |
| Login works on the Vercel address but not on `http://192.168...` | Internet mode uses Secure cookies. Use the Vercel address everywhere, or run setup_internet.bat again and answer **y** to LAN sign-in |
| Upload fails (too large) | About 4.4 MB limit through Vercel. Do big uploads at `http://localhost:8000/admin` on the PC |
| Pages are slow | Home upload speed, Wi-Fi, or many students at once: use a cable; raise `THREADS` in `.env` (for example 16) |
| Everyone logged out | `SECRET_KEY` in `.env` changed. Keep one fixed value |
| Database errors | MariaDB service stopped: start it in `services.msc`; `python scripts\pc_setup.py --check` |
| Forgot the admin password | From the project folder: `python -c "from signalsleuth import db; db.update_admin_password(1,'NewPass123')"`, then sign in and change it |

## 13. Security notes

- `.env` stays on the PC. The tunnel address alone is useless: without the secret the PC answers **403** (checked by check_internet.bat).
- Change the default admin password at first sign-in (forced). Eight wrong passwords lock that account and visitor for 5 minutes.
- Keep Windows updated and its firewall on. The tunnel only makes outbound connections: **do not open router ports**.
- Never share `ORIGIN_SECRET`, the ngrok authtoken or a Cloudflare token in screenshots or chats.
- Back up regularly: the PC holds the only copy of the data.

## 14. Final checklist

| Done | Item |
|---|---|
| [ ] | Python, MariaDB installed; `C:\SignalSleuth` set up; http://localhost:8000/api/health ok |
| [ ] | ngrok authtoken added; static domain created and written down |
| [ ] | setup_internet.bat run; ORIGIN_URL and ORIGIN_SECRET copied; check_internet.bat shows 200, 200, 403 |
| [ ] | Proxy repository pushed alone; GitHub front page shows `api/` and `vercel.json` |
| [ ] | Old Vercel project deleted; new project: Framework Other, Root Directory `./`, both variables set, Ready |
| [ ] | Source tab lists `api/proxy.js`; tests 1 to 6 in section 9 pass; phone on mobile data works |
| [ ] | FRONT_URL added to `.env`; check_internet.bat shows `Vercel address: 200` |
| [ ] | Admin password changed; student list, season and deadlines set; first backup taken; PC set to never sleep |

> **How this was tested.** The proxy passed 22 checks against a simulated PC and a simulated Vercel rewrite, and the real application ran behind it (home, login, admin session with a Secure cookie, static files, /m and /m/, secret check, health). The Windows batch files, ngrok, Cloudflare and Vercel's own platform could not be run in the test environment, so on your first run send me the exact message or the `/__front/debug` output of any step that differs.
