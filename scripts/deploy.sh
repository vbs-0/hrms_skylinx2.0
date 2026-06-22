#!/usr/bin/env bash
# One-command deploy (gap #12). Pull, migrate, collectstatic, restart.
# Backs up the DB first so a bad migration is recoverable (gap #8).
#
# Usage on server:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PY="${PY:-$PROJECT_DIR/venv/bin/python}"
SERVICES="${SERVICES:-hrms-client hrms-vendor hrms-scheduler}"

echo "==> safety backup before deploy"
"$PROJECT_DIR/scripts/backup_db.sh" || echo "WARN: backup failed — continuing (check backup.log)"

echo "==> git pull"
git pull --ff-only

echo "==> install deps (if changed)"
"$PY" -m pip install -q -r requirements.txt

echo "==> migrate"
"$PY" manage.py migrate --noinput

echo "==> collectstatic"
"$PY" manage.py collectstatic --noinput

echo "==> restart services"
# shellcheck disable=SC2086
sudo systemctl restart $SERVICES

echo "==> done. status:"
# shellcheck disable=SC2086
sudo systemctl --no-pager --lines=0 status $SERVICES || true
