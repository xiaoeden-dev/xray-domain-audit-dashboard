# 8. Operations, security, and troubleshooting

## Service status

```bash
systemctl status x-ui --no-pager
systemctl status xray-dashboard --no-pager
systemctl status x-ui-logrotate.timer --no-pager
systemctl list-timers --all x-ui-logrotate.timer --no-pager
```

## Dashboard logs

```bash
journalctl -u xray-dashboard -n 100 --no-pager
journalctl -u xray-dashboard -f
```

Do not publish journal output without reviewing it for usernames, paths, and sensitive values.

## Common issues

### Dashboard does not start

```bash
systemctl status xray-dashboard --no-pager -l
journalctl -u xray-dashboard -n 100 --no-pager
systemd-analyze verify /etc/systemd/system/xray-dashboard.service
```

Check that the Tailscale address exists, that the environment file is present and root-only, and that the `xraydash` user can import the app and read the static file.

### `Permission denied` reading access logs

```bash
getfacl -p /var/log/x-ui /var/log/x-ui/access.log
runuser -u xraydash -- test -r /var/log/x-ui/access.log && echo OK
```

Check ACLs on the active log and archives. Confirm the logrotate `lastaction` hook reapplies the ACL after rotation.

### Domains are missing or masked

The dashboard cannot recover a domain if Xray's access log has only a masked destination or IP. Check inbound sniffing settings and the custom Xray build. Encrypted DNS, ECH, direct IP connections, and application-specific protocols can prevent hostname identification. Do not treat every logged connection as a human page visit.

### Old entries appear more than once

The collector uses a unique SHA-256 fingerprint to ignore duplicate records when an uncompressed archive later becomes compressed under a new filename. If you modify parser logic or manually reset the database, review the import state first. Do not delete the database as a routine troubleshooting step; it contains your collected history.

### Dashboard port is not reachable

- Confirm Tailscale is connected on both devices.
- Check `tailscale status` and `tailscale ping`.
- Check `ss -ltnp | grep ':8080'` on the VPS.
- Confirm the listener binds to the VPS's Tailscale IP.
- Review Tailscale ACLs/grants. Do not open port 8080 publicly as a shortcut.

## Backups and database retention

The SQLite database is separate from logrotate. Back it up using SQLite's online backup mechanism or stop the dashboard briefly before making a filesystem copy. Protect backups because they contain client/domain/timestamp metadata.

The reference application does not prune database records. Decide how long to retain history and implement a reviewed cleanup job if required. Log archive retention does not delete rows already imported into SQLite.

## Updating Xray or 3x-ui

A panel/Xray update may replace the custom binary or change the source structure. After updates:

1. Check the running Xray version and binary checksum.
2. Confirm the custom patch remains present or rebuild from a matching upstream source tag.
3. Do not reapply the old patch blindly to a new Xray release.
4. Build to a separate path and test the existing config with `XRAY_LOCATION_ASSET` set correctly.
5. Back up the current binary before deployment.
6. Restart only during a maintenance window and verify existing client connectivity.

## Browser favicon privacy

The dashboard loads favicons directly from each identified domain using the administrator's browser. The request uses `referrerpolicy="no-referrer"`, but the destination may still see the browser's public IP address and request time. Disable the favicon loader in `static/index.html` if these outbound requests are not appropriate.

## Operational safety

- Keep Xray and dashboard secrets out of Git.
- Never commit logs, SQLite databases, private config, or compiled production binaries.
- Do not expose port 8080 publicly.
- Keep the dashboard process unprivileged.
- Review monitoring authorization and retention requirements.
