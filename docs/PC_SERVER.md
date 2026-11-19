# Running Signal Sleuth on your own PC (classroom server)

Use this when you want the platform on a computer in your lab or office instead of Vercel.
Students on the same Wi-Fi/LAN open `http://<your-PC-address>:8000`. Everything (database,
uploaded games, admin console, mobile API) stays on your machine.

Works on Windows 10/11 (scripts included), and on macOS/Linux with the same Python commands.

## What you need
1. **Python 3.10+**: https://www.python.org/downloads/ (tick "Add python.exe to PATH").
2. **MariaDB or MySQL** running on this PC (free). Any one of:
   - MariaDB: https://mariadb.org/download/ (remember the root password you set), or
   - XAMPP (start the "MySQL" module in its control panel): https://www.apachefriends.org/
3. This project folder, unzipped somewhere permanent (for example `C:\SignalSleuth`).
   Avoid running it from `Downloads` or from inside the zip.

## One-time setup (Windows)
1. Double-click **`setup_windows.bat`**. It creates a private Python environment, installs
   the packages, asks for your database user/password, writes `.env` (with a random
   `SECRET_KEY`), creates the database and tables, and optionally loads the sample student IDs.
2. Right-click **`open_firewall.bat`** -> *Run as administrator* (lets other computers connect).
   If your Wi-Fi is marked **Public**, switch it to **Private** in Windows network settings.
3. Double-click **`start_server.bat`**. The window prints the addresses to give your students, e.g.
   `Students (LAN): http://192.168.1.25:8000`. Keep the window open while class is running.
4. Sign in at `/admin/login` with user `admin`. Unless you set a first admin password during
   setup, the factory password is `admin123`, and you are forced to change it immediately.
5. In the admin console: upload the student list (Excel/CSV), set the season dates and
   chapter deadlines, and upload your chapter games.

### Other systems (macOS / Linux)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-pc.txt
python scripts/pc_setup.py --seed-ids
python pc_server.py
```

## Everyday use
| Task | How |
|---|---|
| Start | `start_server.bat` |
| Stop | Ctrl+C in the window, or close it |
| Back up | `backup_windows.bat` -> `backups\` (database `.sql` + uploaded games `.zip`) |
| Check DB connection | `python scripts\pc_setup.py --check` |
| Change settings | edit `.env`, then restart the server |

Back up before every exam week and copy the `backups` folder to a USB drive or cloud folder.
Restore the database with: `mysql -u USER -p signalsleuth < backups\signalsleuth_DATE.sql`

## Make the PC the permanent server
- Plug it into the network by cable if you can, and turn off sleep (Power & sleep -> Never).
- Give it a fixed address: set a DHCP reservation in your router, or a static IP, so
  `http://192.168.1.25:8000` never changes.
- Start automatically when Windows starts (run once in an *administrator* Command Prompt,
  adjusting the path):
  `schtasks /create /tn "SignalSleuth" /tr "C:\SignalSleuth\start_server.bat" /sc onstart /rl highest`
  (MariaDB/XAMPP must also start automatically; MariaDB does this by default as a Windows service.)

## Students outside your network (internet access)
Do not open your router to the internet. Use a tunnel plus the separate `signalsleuth-vercel-proxy` Vercel project, which gives
students a public `https://<name>.vercel.app` address and keeps your PC hidden. The complete,
step-by-step procedure is in **`docs/INTERNET_ACCESS.md`** (PDF: `docs/SignalSleuth_PC_Internet_Guide_v2.pdf`).
Short version: `setup_internet.bat`, then `start_all.bat`, then push the separate `signalsleuth-vercel-proxy` folder to its own GitHub repository and import it in Vercel.

## Security notes
- Keep `.env` private; it holds your database password and `SECRET_KEY`.
- Repeated wrong passwords lock that account/IP combination for 5 minutes.
- The server runs with Waitress, not Flask's debug server. Never set `FLASK_DEBUG=1` on a shared network.
- Only people on your network can reach the server unless you add a tunnel.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Cannot reach the database" | Start MariaDB/MySQL (Services -> MariaDB, or XAMPP -> Start MySQL); check `MYSQL_*` in `.env` |
| Students cannot open the address | Run `open_firewall.bat` as admin; same Wi-Fi?; Wi-Fi profile must be Private |
| Page loads but login does nothing | `.env` must contain `SESSION_COOKIE_SECURE=0` when using plain `http://` |
| "Port already in use" | Change `PORT` in `.env`, rerun `open_firewall.bat 8001` with the new port |
| Forgot admin password | `python -c "from signalsleuth import db; db.update_admin_password(1,'NewPass123')"` from the project folder, then sign in and change it |
