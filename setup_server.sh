#!/bin/bash
set -e

echo "==========================================="
echo " Skylinx HRMS 2.0 - Server Setup Script    "
echo "==========================================="

DB_NAME="skylinx_db"
DB_USER="skylinx_user"

# Prompt for database password
read -s -p "Enter a new secure password for the PostgreSQL user '$DB_USER': " DB_PASS
echo ""

echo "[1/5] Installing PostgreSQL..."
sudo apt update
sudo apt install -y postgresql postgresql-contrib python3-dev libpq-dev

echo "[2/5] Configuring PostgreSQL database and user..."
# Ignore errors if DB or User already exist
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" || true
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" || sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"

echo "[3/5] Setting up environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.dist" ]; then
        cp .env.dist .env
        echo "Created .env from .env.dist"
    else
        touch .env
        echo "Created blank .env"
    fi
fi

# Update .env with DB credentials
DB_URL="DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}"

# Remove existing DATABASE_URL and add the new one
sed -i '/^DATABASE_URL=/d' .env
echo "$DB_URL" >> .env
echo "Updated DATABASE_URL in .env"

echo "[4/5] Running database migrations..."
# Assumes virtual environment is already activated or we are running system-wide
python3 manage.py makemigrations
python3 manage.py migrate

echo "[5/5] Collecting static files..."
python3 manage.py collectstatic --noinput

echo "==========================================="
echo " Setup complete! "
echo " Remember to create your superuser using:"
echo " python3 manage.py createsuperuser"
echo "==========================================="
