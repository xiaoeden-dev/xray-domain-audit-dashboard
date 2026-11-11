# 7. Private dashboard access with Tailscale

Tailscale creates an encrypted private network between authorized devices. It is separate from the Xray/VLESS proxy service. The dashboard is not made private simply by knowing the VPS address; the application must bind to the server's Tailscale interface and tailnet access must be restricted.

## 7.1 Install and authenticate

Install Tailscale on the Ubuntu VPS using the official instructions for your Ubuntu release. Install the Windows client on the administrator PC. Sign both into the same tailnet and approve the server device.

On the VPS:

```bash
tailscale status
tailscale ip -4
ip -4 addr show tailscale0
```

From Windows PowerShell:

```powershell
tailscale ping <TAILSCALE_IPV4_OF_VPS>
```

Use the address reported on your own VPS; never copy an example address from a guide.

## 7.2 Bind Uvicorn only to the Tailscale IP

In the systemd service, set:

```text
--host <TAILSCALE_IPV4_OF_VPS> --port 8080
```

Do not use `--host 0.0.0.0`. Do not bind the dashboard to the VPS public address. After editing the unit:

```bash
systemctl daemon-reload
systemctl restart xray-dashboard.service
ss -ltnp | grep ':8080'
```

The output must show the Tailscale IPv4 address on port 8080.

## 7.3 Access the dashboard

With Tailscale connected on the administrator's Windows PC, open:

```text
http://<TAILSCALE_IPV4_OF_VPS>:8080
```

Sign in with the dashboard password configured in `/etc/xray-dashboard.env`.

The reference deployment uses HTTP inside the encrypted Tailscale network. Do not expose this HTTP service to the public internet. If you need access outside the tailnet, design a separate TLS-protected public access layer and review the security model first.

## 7.4 Tailnet controls

Authorize only trusted devices/users in the Tailscale admin console. Consider a tailnet ACL or grants policy that allows only the administrator device/user to reach TCP port 8080 on the server. Do not invite untrusted users to the tailnet just to access the dashboard.
