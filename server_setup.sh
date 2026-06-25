#!/usr/bin/env bash
#
# One-step server setup for the HRMS (PostgreSQL in production).
#
#   ./server_setup.sh            install deps, run migrations, collect static
#   ./server_setup.sh --reset    ALSO wipe ALL data and load fresh demo data
#
# Run from the project root with the virtualenv active (or set PYTHON=...).
# --reset is destructive: it flushes every table, then reloads demo fixtures
# and creates the known demo logins (admin/admin123, hrmanager|manager|emp1.. /123456).
#
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python}"

echo "==> Installing dependencies"
$PY -m pip install -r requirements.txt

echo "==> Applying database migrations"
$PY manage.py migrate --no-input

if [ "${1:-}" = "--reset" ]; then
  echo "==> Resetting database and loading demo data (DESTRUCTIVE)"
  $PY manage.py seed_demo_data --reset --no-input
fi

echo "==> Collecting static files"
$PY manage.py collectstatic --no-input

echo "==> Done."
