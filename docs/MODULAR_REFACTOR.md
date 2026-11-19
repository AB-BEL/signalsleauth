# Modular refactor: what changed and how it was verified

## Before and after

| Before | After |
|--------|-------|
| `app.py` (1,955 lines: config, helpers, 100+ routes) | `app.py` (10 lines) + package `signalsleuth/` |
| `db.py` (1,938 lines, 102 functions) | `signalsleuth/db/` (11 modules, same function names) |
| `storage.py`, `monetization.py` at the root | `signalsleuth/services/` |
| `schema.sql`, `data/` at the root | `database/schema.sql`, `database/seed/` |
| `static/`, `uploads/`, root HTML games | `public/static/`, `games/` (bundled), `uploads/` (runtime only) |

## Package map

```
signalsleuth/
  __init__.py        create_app() factory
  config.py          environment variables, paths, serverless detection
  constants.py
  db/                core (connection, TLS), schema, admins, progress, users, chapters,
                     access, scores, rankings, questions, settings
  services/          storage (local/S3), mailer, tokens, pdf, monetization
  web/               decorators (login/admin/api), hooks (filters, branding, cache headers)
  blueprints/        main, auth, student, game_api, mobile_api, system,
                     admin_auth, admin_students, admin_chapters, admin_content,
                     admin_rankings, admin_system
```

`from signalsleuth import db` still exposes every original function (`db.get_user(...)`), so business logic is unchanged.

## Deployment features added

1. **Serverless-safe files**: runtime writes go to `/tmp` on Vercel; built-in games are read from the read-only `games/` folder.
2. **TLS to managed MySQL**: `MYSQL_SSL=1` (certificate and host name verified).
3. **S3 storage chosen automatically** when `S3_BUCKET` is set; warning in `/admin/storage-status` when Vercel is used without it.
4. **Database setup separated from start-up**: `scripts/init_db.py`; on Vercel the app runs a single cheap probe instead of the whole schema (`DB_INIT=auto|always|never`).
5. **Real health check**: `/api/health` tests the database and returns 503 when it is down.
6. **Forced admin password change** while the factory password is in use; `ADMIN_INITIAL_PASSWORD` sets a custom first password.
7. **`SECRET_KEY` required** in production (Vercel) or when `APP_ENV=production`.
8. **Scheduled snapshots**: `/api/cron/weekly-snapshot` (protected by `CRON_SECRET`) called daily by Vercel Cron.
9. **Cross-origin games**: the game page injects a signed token so scores save when the mobile web app is hosted on a different domain.
10. **Static files in `public/`** (Vercel serves `public/` from its CDN; Flask serves the same folder locally).
11. **Upload limit** 4 MB on Vercel (platform body limit about 4.5 MB), 16 MB elsewhere.
12. **Secure session cookie** in production.
13. Backup/restore scripts accept TLS; `--routines/--triggers` removed (the schema has none).

Removed: the Alembic/Flask-Migrate placeholder (`migrations/`, one empty baseline revision) and its dependencies, plus the duplicate `/api/health_unused_placeholder` route.

## Endpoint names

URLs are identical to the original. Only Flask endpoint names gained a blueprint prefix; templates were updated accordingly. Use `url_for("auth.login")` instead of `url_for("login")`.

| Old endpoint | New endpoint |
|--------------|--------------|
| `admin_change_password` | `admin_auth.admin_change_password` |
| `admin_login` | `admin_auth.admin_login` |
| `admin_logout` | `admin_auth.admin_logout` |
| `admin_chapter_deadline` | `admin_chapters.admin_chapter_deadline` |
| `admin_module_chapters` | `admin_chapters.admin_module_chapters` |
| `admin_module_games` | `admin_chapters.admin_module_games` |
| `admin_module_levels` | `admin_chapters.admin_module_levels` |
| `admin_season` | `admin_chapters.admin_season` |
| `admin_set_chapter_title` | `admin_chapters.admin_set_chapter_title` |
| `admin_toggle_chapter` | `admin_chapters.admin_toggle_chapter` |
| `admin_upload_game` | `admin_chapters.admin_upload_game` |
| `admin_feedback_edit` | `admin_content.admin_feedback_edit` |
| `admin_feedback_list` | `admin_content.admin_feedback_list` |
| `admin_question_add` | `admin_content.admin_question_add` |
| `admin_question_edit` | `admin_content.admin_question_edit` |
| `admin_questions` | `admin_content.admin_questions` |
| `admin_questions_download` | `admin_content.admin_questions_download` |
| `admin_questions_download_pdf` | `admin_content.admin_questions_download_pdf` |
| `admin_questions_reseed` | `admin_content.admin_questions_reseed` |
| `admin_export_ranking` | `admin_rankings.admin_export_ranking` |
| `admin_force_snapshot` | `admin_rankings.admin_force_snapshot` |
| `admin_module_reports` | `admin_rankings.admin_module_reports` |
| `admin_module_scoring` | `admin_rankings.admin_module_scoring` |
| `admin_rankings` | `admin_rankings.admin_rankings` |
| `admin_add_pre_user` | `admin_students.admin_add_pre_user` |
| `admin_add_user` | `admin_students.admin_add_user` |
| `admin_approve_rereg` | `admin_students.admin_approve_rereg` |
| `admin_delete_pre_user` | `admin_students.admin_delete_pre_user` |
| `admin_delete_pre_user_sid` | `admin_students.admin_delete_pre_user_sid` |
| `admin_delete_user` | `admin_students.admin_delete_user` |
| `admin_module_students` | `admin_students.admin_module_students` |
| `admin_player_scores` | `admin_students.admin_player_scores` |
| `admin_resolve_reset` | `admin_students.admin_resolve_reset` |
| `admin_seed_default_ids` | `admin_students.admin_seed_default_ids` |
| `admin_upload_ids` | `admin_students.admin_upload_ids` |
| `admin_user_suspend` | `admin_students.admin_user_suspend` |
| `admin_dashboard` | `admin_system.admin_dashboard` |
| `admin_module_backup` | `admin_system.admin_module_backup` |
| `admin_module_security` | `admin_system.admin_module_security` |
| `admin_module_settings` | `admin_system.admin_module_settings` |
| `admin_save_branding` | `admin_system.admin_save_branding` |
| `admin_storage_status` | `admin_system.admin_storage_status` |
| `change_password` | `auth.change_password` |
| `forgot_password` | `auth.forgot_password` |
| `login` | `auth.login` |
| `logout` | `auth.logout` |
| `register` | `auth.register` |
| `api_level_status` | `game_api.api_level_status` |
| `api_my_scores` | `game_api.api_my_scores` |
| `api_submit_score` | `game_api.api_submit_score` |
| `index` | `main.index` |
| `legacy_game` | `main.legacy_game` |
| `api_auth_login` | `mobile_api.api_auth_login` |
| `api_auth_register` | `mobile_api.api_auth_register` |
| `api_dashboard` | `mobile_api.api_dashboard` |
| `api_game_package` | `mobile_api.api_game_package` |
| `api_me` | `mobile_api.api_me` |
| `api_play_info` | `mobile_api.api_play_info` |
| `api_rankings` | `mobile_api.api_rankings` |
| `serve_mobile_spa` | `mobile_api.serve_mobile_spa` |
| `chapter_feedback_pdf` | `student.chapter_feedback_pdf` |
| `dashboard` | `student.dashboard` |
| `level_feedback_pdf` | `student.level_feedback_pdf` |
| `play_chapter` | `student.play_chapter` |
| `rankings` | `student.rankings` |
| `request_rereg` | `student.request_rereg` |
| `serve_game_file` | `student.serve_game_file` |
| `api_health` | `system.api_health` |

## How it was verified

* The **original** app and the **new** app were run against two separate MariaDB 10.11 databases with the same scripted session of 102 requests (public pages, admin login and every admin page, admin actions, student registration/login/play/score/PDF, mobile token API, game file serving). Status codes, redirects, page titles and page structure matched on all 102 steps except the two intended differences (the forced admin password change).
* `pytest` suite in `tests/` (14 tests): health, cron, access control, forced password change, every admin page, student and mobile flows, game injection, bundled game, production secret check, TLS options.
* The app was started as an unprivileged user from a read-only copy of the project with `VERCEL=1` to simulate the Vercel runtime.
* Not tested here: a live TiDB Cloud instance, S3 storage, and an actual Vercel deployment. Step 7 of the deployment guide covers those checks.
