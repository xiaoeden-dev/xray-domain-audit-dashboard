# 5. 30-minute log rotation and read-only ACLs

The dashboard user needs to read only `access.log` and its rotated archives. It does not need access to `error.log`, `3xui.log`, or the rest of the server.

## 5.1 Create a dedicated account and directories

```bash
mkdir -p /opt/xray-dashboard /var/lib/xray-dashboard
id xraydash >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin xraydash
chown -R xraydash:xraydash /opt/xray-dashboard /var/lib/xray-dashboard
apt-get install -y acl logrotate
```

## 5.2 Grant read-only access to the active access log

```bash
setfacl -m u:xraydash:r-x /var/log/x-ui
setfacl -m u:xraydash:r-- /var/log/x-ui/access.log
```

For existing archives:

```bash
find /var/log/x-ui -maxdepth 1 -type f -name 'access.log*' \\
  -exec setfacl -m u:xraydash:r-- -- {} +
```

Verify the dedicated user can read the files:

```bash
runuser -u xraydash -- sh -c \\
  'for f in /var/log/x-ui/access.log*; do [ -r "$f" ] && echo "READ OK: ${f##*/}" || echo "READ FAIL: ${f##*/}"; done'
```

The directory ACL allows filename listing and traversal. File ACLs grant read-only access to `access.log*`; they do not grant read access to other root-owned log files.

## 5.3 Configure logrotate

Install `config/logrotate-x-ui.conf.example` as `/etc/logrotate-x-ui.conf` after adjusting paths. The example:

- retains up to 672 rotations;
- uses `maxage 14`;
- compresses older files and delays compression by one rotation;
- uses `copytruncate` so the long-running Xray process can continue writing to the same file;
- reapplies read-only ACLs to the active file and archives after rotation.

`copytruncate` has a small race window between copying and truncating in which a log write can be missed. It is used here because the panel-managed process may keep the access log open. Review the trade-off for your installation.

## 5.4 Schedule a forced rotation every 30 minutes

Install the supplied unit files:

```bash
install -m 644 systemd/x-ui-logrotate.service /etc/systemd/system/x-ui-logrotate.service
install -m 644 systemd/x-ui-logrotate.timer /etc/systemd/system/x-ui-logrotate.timer
systemctl daemon-reload
systemctl enable --now x-ui-logrotate.timer
```

The service invokes logrotate with `--force`; that is what makes this example rotate at each timer interval rather than waiting for the normal daily schedule/size threshold. The timer starts five minutes after boot and then every 30 minutes.

Verify:

```bash
systemctl list-timers --all x-ui-logrotate.timer --no-pager
systemctl start x-ui-logrotate.service
systemctl status x-ui-logrotate.service --no-pager
```

A oneshot service normally returns to `inactive (dead)` after a successful run. Check `status=0/SUCCESS` rather than expecting it to stay running.

## 5.5 Retention note

At two rotations per hour, 672 archives represent 14 days. The archive count and `maxage` are safeguards; actual disk usage depends on traffic volume. The dashboard SQLite database is independent and is not automatically purged by logrotate.
