# Client HRMS — Deployment Guide

Tested on **Ubuntu 22.04**, Python 3.10, PostgreSQL 14, nginx + gunicorn.
Follow top to bottom. The **Gotchas** section at the end lists every issue we
actually hit — read it if something looks off.

---

## 0. Prerequisites (once per server)
```bash
sudo apt update
sudo apt install -y python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx
```

## 1. Clone + virtualenv
```bash
mkdir -p /home/ubuntu/hrms && cd /home/ubuntu/hrms
git clone https://github.com/vbs-0/hrms_skylinx2.0 -b 4.0
cd hrms_skylinx2.0
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt gunicorn
```

## 2. Database + migrations + static (one script)
```bash
bash setup_server.sh
```
It prompts for a Postgres password, creates the DB/user, writes `DATABASE_URL`
into `.env`, migrates, seeds themes, and runs collectstatic.

> You will see `could not change directory to ... Permission denied` a few
> times during the DB step. **This is harmless** — it's just `psql` running as
> the `postgres` user from a folder it can't `cd` into. The `CREATE DATABASE`
> etc. lines right after it confirm it worked.

## 3. Edit `.env`  ← the part that bites
```bash
nano .env
```
Set exactly these (the defaults are placeholders and WILL break things):
```ini
DEBUG=False
SECRET_KEY=<a long random string>
ALLOWED_HOSTS=<server-ip-or-domain>
CSRF_TRUSTED_ORIGINS=http://<server-ip-or-domain>     # MUST include http:// or https://
TIME_ZONE=Asia/Kolkata

# Licensing — point at the vendor server
LICENSE_ROLE=client
LICENSE_SERVER_URL=http://127.0.0.1:8001               # NO trailing path; client appends /api/license/verify
```
- Scroll to the **bottom** of the file and confirm there is a real
  `DATABASE_URL=postgresql://...` line (added by `setup_server.sh`). The
  `DB_NAME=dbname / user / password` block above it is placeholder text —
  `DATABASE_URL` overrides it.

## 4. Superuser
```bash
python3 manage.py createsuperuser
deactivate
```

## 5. Run as a service
```bash
sudo tee /etc/systemd/system/hrms-client.service >/dev/null <<'EOF'
[Unit]
Description=Skylinx HRMS Client
After=network.target postgresql.service
[Service]
User=root
WorkingDirectory=/home/ubuntu/hrms/hrms_skylinx2.0
ExecStart=/home/ubuntu/hrms/hrms_skylinx2.0/venv/bin/gunicorn skylinx.wsgi -b 127.0.0.1:8000 -w 3 --timeout 120
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now hrms-client
sudo systemctl status hrms-client --no-pager | grep Active
```

## 6. nginx
```bash
sudo tee /etc/nginx/sites-available/hrms >/dev/null <<'EOF'
server {
    listen 80;
    server_name <server-ip-or-domain>;
    client_max_body_size 50M;

    location = /api/license/verify { proxy_pass http://127.0.0.1:8001; proxy_set_header Host $host; }
    location /license/vendor       { proxy_pass http://127.0.0.1:8001; proxy_set_header Host $host; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /static/ { alias /home/ubuntu/hrms/hrms_skylinx2.0/staticfiles/; }
}
EOF
sudo ln -sf /etc/nginx/sites-available/hrms /etc/nginx/sites-enabled/hrms
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```
> If `nginx -t` warns `conflicting server name`, another config already claims
> this IP/domain. Find it and remove it:
> ```bash
> grep -rl "<server-ip-or-domain>" /etc/nginx/sites-enabled/
> ```

## 7. Verify
- `http://<server-ip>/` → login page, sign in as your superuser.
- Activate a license: log in → license activation page → paste the key from the
  vendor dashboard → paid features unlock.

---

## Gotchas (everything we actually hit)
| Symptom | Cause | Fix |
|---|---|---|
| 403 on login / CSRF verification failed | `CSRF_TRUSTED_ORIGINS` has no scheme | Use `http://<host>`, not bare `<host>` |
| License never activates / 404 on verify | `LICENSE_SERVER_URL` had an extra path like `/vendorapi` | Set it to the server **root** only; client appends `/api/license/verify` |
| Tracebacks shown on public site | `DEBUG=True` | Set `DEBUG=False` |
| `could not change directory ... Permission denied` during setup | cosmetic psql warning | Ignore — DB still created |
| `Using legacy setup.py install ... wheel is not installed` | no `wheel` in venv | Harmless; or `pip install wheel` first to silence |
| `nginx: conflicting server name` | leftover/default nginx config | Remove the other config claiming the host |
| Service won't boot | bad `.env` / wrong path | `journalctl -u hrms-client -n 40 --no-pager` |

## Updating later
```bash
cd /home/ubuntu/hrms/hrms_skylinx2.0 && source venv/bin/activate
git pull
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py collectstatic --noinput
deactivate
sudo systemctl restart hrms-client
```
