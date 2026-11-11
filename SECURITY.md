# Security and responsible-use policy

## Intended use

This project is provided for educational purposes. Any practical deployment is intended for lawful domain-level connection logging and private administration of infrastructure that the operator owns or is explicitly authorized to manage.

Do not use it to secretly monitor people, steal or obtain another person's browsing or connection history without authority, access accounts or devices without permission, or unlawfully collect, retain, use, or disclose personal data. Taking or viewing someone else's activity history without authorization may be unlawful and may violate privacy, computer-misuse, data-protection, telecommunications, employment, or other laws depending on the jurisdiction and circumstances.

The operator is responsible for checking applicable law and contracts, providing required notice, obtaining consent or another lawful basis where required, limiting access, and setting a proportionate retention policy. This project is not legal advice. A statement that software is “for education” does not make an otherwise unlawful deployment lawful.

## Browser favicon behaviour

The dashboard browser requests each identified domain's `/favicon.ico` directly to display its icon. The request originates from the administrator's browser, not from the VPS, and can disclose the browser's public IP address and request time to the domain operator. Disable the favicon loader in `static/index.html` if this is not acceptable for your environment.

## Reporting a vulnerability

Do not publish working credentials, access tokens, raw logs, client identifiers, IP addresses, screenshots containing private data, or database contents in an issue. For a suspected vulnerability, use GitHub's private vulnerability reporting feature if enabled. If private reporting is unavailable, ask the maintainer for a private contact route without posting exploit details publicly.

## Deployment security checklist

- Bind Uvicorn only to the server's Tailscale IPv4 address for the private deployment.
- Do not open the dashboard port on the public firewall or bind it to `0.0.0.0`.
- Keep `/etc/xray-dashboard.env` owned by root with mode `0600`.
- Use a strong, unique administrator password and protect the session secret.
- Run the application as a dedicated unprivileged user.
- Grant that user read-only ACL access only to the Xray access log and its archives.
- Keep SQLite data outside the web root with restrictive permissions.
- Restrict tailnet membership and device access to trusted administrators.
- Keep raw logs, database files, server configs, credentials, and production binaries out of the public repository.
- Back up the original Xray binary and validate a custom build before replacing a production binary.
- Review retention and deletion for both raw log archives and the SQLite database; the example does not automatically prune SQLite history.
