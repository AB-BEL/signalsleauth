#!/usr/bin/env bash
# Daily MySQL backup for Signal Sleuth.
# Cron example (03:15 daily):
#   15 3 * * * /path/to/SignalSleuth/scripts/backup_mysql.sh >> /var/log/signalsleuth-backup.log 2>&1
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi

HOST="${MYSQL_HOST:-127.0.0.1}"
PORT="${MYSQL_PORT:-3306}"
USER="${MYSQL_USER:-signalsleuth}"
PASS="${MYSQL_PASSWORD:-}"
DB="${MYSQL_DATABASE:-signalsleuth}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
OUT_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$OUT_DIR/${DB}_${STAMP}.sql.gz"

# Optional TLS for managed databases (set MYSQL_SSL=1 in .env). Works with MySQL and MariaDB clients.
SSL_ARGS=(); DUMP_EXTRA=()
if [[ "${MYSQL_SSL:-0}" =~ ^(1|true|yes|on)$ ]]; then
  if mysqldump --help 2>/dev/null | grep -q -- "--ssl-mode"; then SSL_ARGS+=(--ssl-mode=VERIFY_IDENTITY); else SSL_ARGS+=(--ssl --ssl-verify-server-cert); fi
  if [[ -n "${MYSQL_SSL_CA:-}" ]]; then SSL_ARGS+=(--ssl-ca="$MYSQL_SSL_CA"); fi
fi
if mysqldump --help 2>/dev/null | grep -q -- "--set-gtid-purged"; then DUMP_EXTRA+=(--set-gtid-purged=OFF); fi

echo "[$(date -Is)] Dumping $DB@$HOST:$PORT → $FILE"
export MYSQL_PWD="$PASS"
mysqldump -h "$HOST" -P "$PORT" -u "$USER" "${SSL_ARGS[@]}" --single-transaction "${DUMP_EXTRA[@]}" "$DB" | gzip -c > "$FILE"
unset MYSQL_PWD
echo "[$(date -Is)] OK ($(wc -c < "$FILE") bytes)"

# Optional: upload dump to S3 if configured
if [[ "${STORAGE_BACKEND:-}" == "s3" && -n "${S3_BUCKET:-}" ]]; then
  python3 - << PY
import os, boto3
from pathlib import Path
from botocore.client import Config
p = Path("$FILE")
kwargs = dict(
    service_name="s3",
    aws_access_key_id=os.environ.get("S3_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("S3_REGION") or "auto",
)
if os.environ.get("S3_ENDPOINT_URL"):
    kwargs["endpoint_url"] = os.environ["S3_ENDPOINT_URL"]
    kwargs["config"] = Config(signature_version="s3v4")
key = (os.environ.get("S3_PREFIX") or "signalsleuth/") + "backups/" + p.name
boto3.client(**kwargs).upload_file(str(p), os.environ["S3_BUCKET"], key)
print("Uploaded s3://%s/%s" % (os.environ["S3_BUCKET"], key))
PY
fi

find "$OUT_DIR" -name "${DB}_*.sql.gz" -mtime +"$KEEP_DAYS" -delete || true
echo "[$(date -Is)] Retention: deleted dumps older than ${KEEP_DAYS} days"
