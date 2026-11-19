#!/usr/bin/env bash
# Restore a gzipped mysqldump. TEST THIS PERIODICALLY on a staging database.
# Usage: ./scripts/restore_mysql.sh backups/signalsleuth_YYYYMMDD.sql.gz
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi
FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Usage: $0 path/to/dump.sql.gz" >&2
  exit 1
fi
HOST="${MYSQL_HOST:-127.0.0.1}"
PORT="${MYSQL_PORT:-3306}"
USER="${MYSQL_USER:-signalsleuth}"
PASS="${MYSQL_PASSWORD:-}"
DB="${MYSQL_DATABASE:-signalsleuth}"
SSL_ARGS=()
if [[ "${MYSQL_SSL:-0}" =~ ^(1|true|yes|on)$ ]]; then
  if mysql --help 2>/dev/null | grep -q -- "--ssl-mode"; then SSL_ARGS+=(--ssl-mode=VERIFY_IDENTITY); else SSL_ARGS+=(--ssl --ssl-verify-server-cert); fi
  if [[ -n "${MYSQL_SSL_CA:-}" ]]; then SSL_ARGS+=(--ssl-ca="$MYSQL_SSL_CA"); fi
fi
echo "WARNING: This overwrites database '$DB' on $HOST. Ctrl+C within 5s to abort."
sleep 5
export MYSQL_PWD="$PASS"
gunzip -c "$FILE" | mysql -h "$HOST" -P "$PORT" -u "$USER" "${SSL_ARGS[@]}" "$DB"
unset MYSQL_PWD
echo "Restore complete. Run application smoke tests (login, rankings, play)."
