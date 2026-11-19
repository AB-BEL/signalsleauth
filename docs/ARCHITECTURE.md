# Signal Sleuth — Architecture (v2)

## 1. User interfaces
- **Web application** — administrator and students (Flask/Jinja)
- **Mobile application** — Android/iOS browser or installed SPA (React); dynamic game packages from API
- **Secure HTTPS API** — JSON under `/api/*` (session or Bearer token)

## 2. Flask backend services
| Service | Responsibility |
|---------|----------------|
| Authentication | Login, register, tokens, password reset |
| User management | Pre-IDs, profiles, suspend, delete |
| Game management | HTML packages, versions, storage |
| Scoring engine | Server-side answer evaluation only |
| Progression engine | Levels, chapter unlock, status_chapter |
| Ranking engine | Weighted overall, chapter boards, exports |
| Feedback service | Per-level and full-chapter PDF |
| Reporting service | Rankings Excel, admin reports |

## 3. MySQL
Users, questions (`question_bank` / `game_questions`), scores (`level_scores`), progress, feedback, rankings, **logs** (`admin_activity_logs`, `audit_logs`), attempts (`game_attempts`), settings.

> Code layout: see `docs/MODULAR_REFACTOR.md`. The services above map to `signalsleuth/blueprints/` (routes) and `signalsleuth/db/` (data layer).

## 4. Game storage
HTML packages via `signalsleuth/services/storage.py` (local or S3), **versions** in `game_versions`, backups via scripts.

## 5. Monitoring and maintenance
Automated backups, admin activity + audit logs, storage status, security password policy, deployment via Vercel (see `docs/DEPLOYMENT_VERCEL.md`) or Gunicorn/Render.

## Administrator modules
Dashboard · Students · Chapters · Games · Levels · Questions · Scoring · Feedback · Leaderboard · Reports · Settings · Security · Backup

## New tables
courses, game_versions, levels, game_questions, game_attempts, student_achievements, notifications, admin_activity_logs, audit_logs, system_settings, users_extra
