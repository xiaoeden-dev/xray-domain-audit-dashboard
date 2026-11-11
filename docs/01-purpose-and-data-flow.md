# 1. Purpose, limits, and data flow

## What the setup does

Xray writes access-log entries for accepted connections. For VLESS users, the access log can include a client email/identity. With sniffing enabled, Xray can identify a domain from supported protocols. A small, version-specific Xray Core patch copies the sniffed destination into the access-log message so the access log can show the hostname as well as the client identity.

A local collector parses those entries and stores selected metadata in SQLite. A private web dashboard lets an authorized administrator filter records by client, destination, and date.

## Educational and authorized use only

This guide is provided for educational purposes. Any practical deployment must be limited to administration of systems you own or are explicitly authorized to manage. Do not use it to secretly monitor people, steal or obtain another person's browsing/connection history without authority, access accounts or devices without permission, or unlawfully collect or disclose personal data. Taking or viewing someone else's activity history without authorization may be unlawful and may violate privacy, computer-misuse, data-protection, telecommunications, employment, or other laws depending on the jurisdiction and circumstances.

Check applicable law and contracts, provide required notice, obtain consent or another lawful basis where required, limit access to the records, and define retention before enabling monitoring. This repository is not legal advice. See [SECURITY.md](../SECURITY.md).

## What it is useful for

- checking which configured client identity generated a recorded connection;
- troubleshooting destination and routing behaviour;
- reviewing domain-level connection metadata during an authorized support or security investigation;
- searching records without manually scanning raw log files.

## What it does not do

- It is not a packet capture system or deep packet inspection engine.
- It does not decrypt HTTPS or bypass browser/application encryption.
- It does not record full URLs, page paths, browser search terms, forms, chat messages, passwords, or page content.
- It does not prove that a user intentionally visited or viewed a website. Applications create background connections.
- It cannot reconstruct a hostname when Xray never receives one.

## Data path

1. A client connects to an Xray inbound.
2. Xray applies protocol sniffing configured for that inbound.
3. The custom dispatcher patch updates the access-message destination when a domain was sniffed.
4. Xray appends a connection record to its access log.
5. The collector reads the active log and archives, extracts a restricted set of fields, and inserts them into SQLite.
6. The browser retrieves authenticated, paginated records from FastAPI.

The browser UI displays timestamps in `Asia/Colombo`. The collector interprets Xray's access-log timestamps as UTC, matching the recommended server setup. Keep the VPS system clock synchronized.

## Privacy boundary

Domain-level metadata can still be sensitive. Limit dashboard access, define a retention policy, and protect the database and backups. An entry is a network connection record, not proof of a human page view or an individual's intent.
