#!/usr/bin/env bash
# Nightly database backup (gap #8). Postgres only — SQLite is dev-local.
# Reads DB creds from the project .env (DATABASE_URL, or DB_NAME/USER/...).
# Keeps 14 days, gzipped. Also backs up the media/ uploads dir (gap #32, files).
#
# Install (run once on the server):
#   chmod +x scripts/backup_db.sh
#   crontab -e   # add:
#   30 2 * * *  /home/ubuntu/hrms/hrms_skylinx2.0/scripts/backup_db.sh >> /home/ubuntu/backups/backup.log 2>&1
#
# Restore:  gunzip -c <file>.sql.gz | psql "$DATABASE_URL"
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

# load .env if present (export every assignment)
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a; . "$PROJECT_DIR/.env"; set +a
fi

mkdir -p "$BACKUP_DIR"

# ponytail: prefer DATABASE_URL; fall back to discrete DB_* vars.
if [ -n "${DATABASE_URL:-}" ]; then
  DUMP_TARGET="$DATABASE_URL"
else
  export PGPASSWORD="${DB_PASSWORD:-}"
  DUMP_TARGET="--host=${DB_HOST:-localhost} --port=${DB_PORT:-5432} --username=${DB_USER:-postgres} ${DB_NAME:?DB_NAME not set}"
fi

OUT="$BACKUP_DIR/db-$STAMP.sql.gz"
# shellcheck disable=SC2086
pg_dump $DUMP_TARGET | gzip > "$OUT"
echo "$(date -Is) wrote $OUT ($(du -h "$OUT" | cut -f1))"

# files: media uploads (employee docs, ID proofs). Skip if dir missing.
if [ -d "$PROJECT_DIR/media" ]; then
  tar -czf "$BACKUP_DIR/media-$STAMP.tar.gz" -C "$PROJECT_DIR" media
  echo "$(date -Is) wrote media-$STAMP.tar.gz"
fi

# rotate
find "$BACKUP_DIR" -name 'db-*.sql.gz'   -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'media-*.tar.gz' -mtime +"$KEEP_DAYS" -delete
echo "$(date -Is) rotated backups older than ${KEEP_DAYS}d"
