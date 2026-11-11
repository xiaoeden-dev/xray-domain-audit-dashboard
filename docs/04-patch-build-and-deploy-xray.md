# 4. Patch, build, test, and deploy Xray

> **Version-specific procedure.** The included patch helper expects the Xray Core source layout and two exact code locations from tag `v26.10.21`. If it finds anything other than two matches, it exits without editing. Do not weaken that check for a newer release.

## 4.1 Obtain the matching source

For the reference version:

```bash
git clone --depth 1 --branch v26.10.21 https://github.com/XTLS/Xray-core.git /opt/xray-src-26.10.21
cd /opt/xray-src-26.10.21
git rev-parse --short HEAD
```

The source tag must match the Xray release you intend to replace. If your installed version differs, stop and adapt the patch against that version's source.

## 4.2 Apply the patch

Assuming you extracted this repository to `/opt/xray-domain-audit-dashboard`, run the patch helper by its full path:

```bash
python3 /opt/xray-domain-audit-dashboard/scripts/patch-xray-dispatcher.py \\
  /opt/xray-src-26.10.21/app/dispatcher/default.go
cd /opt/xray-src-26.10.21
gofmt -w app/dispatcher/default.go
git diff --check
git diff -- app/dispatcher/default.go
```

The script inserts the following logic immediately after the sniffed destination is assigned in both dispatcher paths:

```go
if accessMessage := log.AccessMessageFromContext(ctx); accessMessage != nil {
    accessMessage.To = destination
}
```

Inspect the complete diff. Confirm the source backup created next to `default.go` exists. Do not continue if the patch count, imports, or diff are unexpected.

## 4.3 Build a separate binary

The reference build used Go 1.27.4 on Linux amd64. Adjust the Go path and target architecture to your environment. Build to a temporary path; do not overwrite the production binary during compilation.

```bash
cd /opt/xray-src-26.10.21
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOAMD64=v1 GOTOOLCHAIN=local \\
  /opt/go1.27.4/bin/go build -trimpath -gcflags=all=-l=4 -buildvcs=false \\
  -o /tmp/xray-linux-amd64-domainlog ./main

/tmp/xray-linux-amd64-domainlog version
```

The first build may download Go module dependencies. Verify module checksums and only use the official source repository and trusted Go module infrastructure.

## 4.4 Test the existing config before deployment

For the reference 3x-ui path:

```bash
XRAY_LOCATION_ASSET=/usr/local/x-ui/bin \\
  /tmp/xray-linux-amd64-domainlog run -test \\
  -c /usr/local/x-ui/bin/config.json
```

Setting `XRAY_LOCATION_ASSET` matters when `geoip.dat` and `geosite.dat` are in the panel's binary directory. A successful test should print `Configuration OK`.

## 4.5 Back up and stage the binary

Run these only after the config test succeeds. Confirm the destination and backup names first. This example uses a dated backup suffix:

```bash
cp -a /usr/local/x-ui/bin/xray-linux-amd64 \\
  /usr/local/x-ui/bin/xray-linux-amd64.original-YYYYMMDD

install -m 755 /tmp/xray-linux-amd64-domainlog \\
  /usr/local/x-ui/bin/xray-linux-amd64.new

chown --reference=/usr/local/x-ui/bin/xray-linux-amd64.original-YYYYMMDD \\
  /usr/local/x-ui/bin/xray-linux-amd64.new
chmod --reference=/usr/local/x-ui/bin/xray-linux-amd64.original-YYYYMMDD \\
  /usr/local/x-ui/bin/xray-linux-amd64.new
```

Replace `YYYYMMDD` with the actual date suffix you chose. Verify ownership and file sizes before switching:

```bash
ls -lh /usr/local/x-ui/bin/xray-linux-amd64*
```

Then switch atomically and restart the panel service:

```bash
mv -f /usr/local/x-ui/bin/xray-linux-amd64.new \\
  /usr/local/x-ui/bin/xray-linux-amd64
systemctl restart x-ui
systemctl status x-ui --no-pager -l
/usr/local/x-ui/bin/xray-linux-amd64 version
```

**Impact:** restarting Xray through the panel briefly disconnects active proxy clients. Perform this during a maintenance window and tell users beforehand.

## 4.6 Verify domain logging

Generate a small amount of normal test traffic from a test VLESS client, then inspect only the new access-log lines:

```bash
tail -n 50 /var/log/x-ui/access.log
```

A successful entry may resemble this synthetic example:

```text
2026/01/01 12:00:00.000 accepted tcp:example.com:443 [inbound >> direct] email: client-a
```

Some destinations will remain IPs or masked values. This is expected when Xray cannot sniff a hostname.

## 4.7 Rollback

If the custom binary fails or clients cannot connect, restore the backup you made and restart the panel service. Substitute the exact backup filename you created:

```bash
cp -a /usr/local/x-ui/bin/xray-linux-amd64.original-YYYYMMDD \\
  /usr/local/x-ui/bin/xray-linux-amd64.rollback
mv -f /usr/local/x-ui/bin/xray-linux-amd64.rollback \\
  /usr/local/x-ui/bin/xray-linux-amd64
systemctl restart x-ui
systemctl status x-ui --no-pager -l
```

Keep the source patch and build notes outside the active panel directory. Panel/Xray updates may overwrite the custom binary; reapply only after reviewing the new upstream source and repeating the tests.
