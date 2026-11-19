# Signal Sleuth — React Mobile App

Mobile-first React (Vite) client for the Signal Sleuth Flask backend.

## Features
- Student login / register (unique account token)
- Personal dashboard (username, rank, chapter progress)
- Rankings
- Chapter 1 play (contextual scoring, ≥50% pass, server sync)
- Bottom navigation for phone use

## Run (development)

1. Start Flask (MySQL configured) on port 5000:
   ```bash
   cd SignalSleuth
   python app.py
   ```

2. Start the mobile app:
   ```bash
   cd SignalSleuth/mobile
   npm install
   npm run dev
   ```
   Open the shown URL on your phone (same Wi‑Fi) or browser.

3. Phone on LAN — set API base to your PC IP:
   ```bash
   # mobile/.env
   VITE_API_BASE=http://192.168.x.x:5000
   ```
   Restart `npm run dev`.

## Production build
```bash
cd mobile
npm install
npm run build
```
Serve `mobile/dist` with any static host, or copy into `public/static/mobile` (served by Flask at /m/ on non-Vercel hosts).

## API used
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET  /api/me`
- `GET  /api/dashboard`
- `GET  /api/rankings`
- `GET  /api/chapter/:n/play-info`
- `POST /api/submit-score`

Auth: `Authorization: Bearer <token>` (issued at login; 14-day lifetime).
