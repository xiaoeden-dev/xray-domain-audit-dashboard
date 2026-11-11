# 6. Install the dashboard and collector

## 6.1 Create the Python virtual environment

The reference uses Python 3.12:

```bash
apt-get install -y python3-venv
runuser -u xraydash -- python3 -m venv /opt/xray-dashboard/venv
```

Copy `app.py` and `static/index.html` into `/opt/xray-dashboard/`, preserving ownership by `xraydash`. Install the pinned requirements:

```bash
runuser -u xraydash -- /opt/xray-dashboard/venv/bin/pip install -r requirements.txt
```

Validate:

```bash
runuser -u xraydash -- /opt/xray-dashboard/venv/bin/python -m py_compile /opt/xray-dashboard/app.py
runuser -u xraydash -- /opt/xray-dashboard/venv/bin/python -c 'import fastapi, uvicorn; print(fastapi.__version__, uvicorn.__version__)'
```

## 6.2 Create the environment file

Copy `env.example` to `/etc/xray-dashboard.env`, replace placeholders with a unique strong password and a random 64-character hex session secret, then restrict it:

```bash
install -o root -g root -m 600 env.example /etc/xray-dashboard.env
openssl rand -hex 32
chmod 600 /etc/xray-dashboard.env
chown root:root /etc/xray-dashboard.env
```

Edit the environment file with a root-owned editor, for example `nano /etc/xray-dashboard.env`. Do not paste the real file into chat or commit it. Keep the password value on one line; avoid newline characters. The application compares the configured password and uses the session secret to sign an HttpOnly session cookie.

The reference app uses a password in the root-only environment file. Treat that file as a secret. Use a long unique password and do not reuse a password from another service.

## 6.3 Prepare directories and permissions

```bash
install -d -o xraydash -g xraydash -m 755 /opt/xray-dashboard/static
install -d -o xraydash -g xraydash -m 750 /var/lib/xray-dashboard
chown -R xraydash:xraydash /opt/xray-dashboard
```

Ensure the log ACLs from the previous guide are in place. Test using the service account:

```bash
runuser -u xraydash -- sh -c '
  cd /opt/xray-dashboard &&
  ./venv/bin/python -c "import app; print(\"Application import: OK\")" &&
  test -r static/index.html &&
  test -r /var/log/x-ui/access.log &&
  test -w /var/lib/xray-dashboard &&
  echo "Application permissions: OK"
'
```

## 6.4 Install the systemd service

Copy `systemd/xray-dashboard.service.example` to `/etc/systemd/system/xray-dashboard.service`. Replace `__TAILSCALE_IPV4__` with the value returned by `tailscale ip -4`. Do not use `0.0.0.0` or the VPS's public IP.

Validate before starting:

```bash
systemd-analyze verify /etc/systemd/system/xray-dashboard.service
stat -c 'Owner: %U | Permissions: %a' /etc/xray-dashboard.env
```

The environment file should be owned by `root` with mode `600`.

## 6.5 Start and verify

```bash
systemctl daemon-reload
systemctl enable --now xray-dashboard.service
systemctl status xray-dashboard.service --no-pager -l
ss -ltnp | grep ':8080'
curl -fsS http://$(tailscale ip -4):8080/healthz
```

The listener should show the Tailscale IP specifically. If it shows `0.0.0.0`, a public IP, or another interface, stop the service and fix the bind address before using the dashboard.

## 6.6 Collector behaviour

The collector reads the active `access.log`, periodically scans rotated `access.log-*` archives (including gzip archives), and inserts selected fields into SQLite. A SHA-256 fingerprint based on each raw line is used for duplicate suppression; raw lines are not stored in the events table.

The database defaults to `/var/lib/xray-dashboard/history.sqlite3`. Protect this directory and its backups as sensitive monitoring data. The collector does not automatically delete old database rows; define and implement a database retention policy for your environment.
