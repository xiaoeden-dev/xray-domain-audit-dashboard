# 2. Prerequisites and preparation

## Reference requirements

- Ubuntu Server 24.04 LTS, amd64, with root or sudo access.
- A working Xray Core deployment managed by 3x-ui or an equivalent panel.
- Access to the exact Xray Core source tag matching the installed binary.
- Git, Python 3.12, `python3-venv`, `acl`, and logrotate.
- Go toolchain compatible with the selected Xray Core tag (Go 1.27.4 was used for the reference build of `v26.10.21`).
- A Tailscale account and an administrator computer with Tailscale installed.
- A synchronized system clock. The reference collector interprets Xray access-log timestamps as UTC; use UTC on the VPS or adapt the parser before using a different server timezone.
- A backup/maintenance window before replacing the production Xray binary.

Do not assume paths, service names, architecture, or panel behaviour match this example. Confirm them first.

## Confirm system and paths

```bash
. /etc/os-release && printf '%s %s\\n' "$PRETTY_NAME" "$(dpkg --print-architecture)"
systemctl status x-ui --no-pager
command -v xray || true
ls -l /usr/local/x-ui/bin/xray-linux-amd64 /usr/local/x-ui/bin/config.json
ls -l /var/log/x-ui/
```

The example uses these common 3x-ui paths:

- Xray binary: `/usr/local/x-ui/bin/xray-linux-amd64`
- Xray config: `/usr/local/x-ui/bin/config.json`
- Logs: `/var/log/x-ui/access.log`, `/var/log/x-ui/error.log`

Adapt if your installation differs. Do not publish your config file; it can contain credentials and client identifiers.

## Back up before patching

Keep a copy of the current binary and relevant configuration in a root-only backup location. Do not overwrite the only working binary. Record the installed Xray version and architecture:

```bash
/usr/local/x-ui/bin/xray-linux-amd64 version
file /usr/local/x-ui/bin/xray-linux-amd64
```

Also record the current service status and check that clients work before any change. If a panel update replaces the Xray binary, re-check whether the custom patch is still present.

## Install base utilities

```bash
apt-get update
apt-get install -y git python3-venv acl logrotate
```

Install Go separately from the official Go distribution and verify its published checksum. Use a Go version supported by the Xray tag being built. Do not download prebuilt binaries from untrusted mirrors.

## Privacy before testing

Use synthetic example records in documentation and issues. Never paste unredacted access logs, config files, UUIDs, public IPs, real client names, passwords, tokens, or database files into public tickets.
