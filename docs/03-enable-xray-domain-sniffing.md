# 3. Enable Xray domain sniffing and access logs

The Xray inbound must have sniffing enabled for the protocol types you want to identify. In a JSON-style Xray inbound, the relevant shape is:

```json
{
  "sniffing": {
    "enabled": true,
    "destOverride": ["http", "tls", "quic", "fakedns"]
  }
}
```

Apply this through your panel's inbound settings when the panel owns the generated config. Do not blindly replace a panel-generated config with a partial JSON example.

The Xray log configuration should direct access logs to a file. A typical example is:

```json
{
  "log": {
    "access": "/var/log/x-ui/access.log",
    "error": "/var/log/x-ui/error.log",
    "loglevel": "warning",
    "maskAddress": "full"
  }
}
```

Verify the actual config path and log path for your installation. Keep a normal production log level; debug logging can create unnecessary volume.

## Client identity

The access record can include `email: CLIENT_NAME` when the VLESS client is assigned an email/label in Xray's client configuration. The dashboard uses that field as the client selector. Use neutral placeholders in public examples, such as `client-a`.

## Address masking

`maskAddress: full` masks IP-address destinations in the access log. It does not prevent a sniffed hostname from being written by the patch. When Xray cannot identify a hostname, the destination can remain masked; no later parser can infer it from a masked value.

## Verify baseline behaviour

Before the custom patch, confirm that:

- the access log is being written;
- VLESS records contain the expected client `email:` field;
- sniffing is enabled on the relevant inbound;
- domains appear in Xray's diagnostics where sniffing succeeds.

The exact messages and file paths may vary by Xray version and panel.
