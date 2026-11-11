# Xray Domain Audit Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Ubuntu 24.04](https://img.shields.io/badge/Reference%20OS-Ubuntu%2024.04-E95420?logo=ubuntu&logoColor=white)](docs/02-prerequisites-and-preparation.md)
[![AI assisted](https://img.shields.io/badge/AI-assisted-OpenAI-412991)](AI-ASSISTANCE.md)\n\n![Project status](https://img.shields.io/badge/status-under%20active%20development-red)\n\n> **Under active development:** This project is still being updated. Features, documentation, and compatibility guidance may change as the project evolves.

A self-hosted, open-source reference implementation for **Xray Core and 3x-ui domain-level connection auditing**. It associates identifiable destination domains with VLESS client labels and timestamps, then provides searchable client activity history through a private FastAPI and SQLite dashboard.

> **Educational purpose:** This repository is provided to demonstrate domain-level connection logging and private administration. Any real deployment must be limited to systems and users the operator is legally authorized to monitor. It is not a full browser-history recorder.

## 🧭 Purpose

This project brings together a version-specific Xray Core access-log patch, a log collector, SQLite storage, and a private dashboard. It is intended for administrators who need a searchable VLESS client connection-history view for authorized troubleshooting and network operations. It demonstrates:

- **Per-client connection auditing:** associate an Xray client label/email with connection destinations that Xray can identify.
- **Troubleshooting:** review connection patterns, destination resolution, and routing behaviour.
- **Operational visibility:** search recorded events by client, domain/destination, and date without manually reading large log files.
- **Private administration:** keep the dashboard reachable through a trusted Tailscale network rather than exposing it on the public VPS interface.

### Responsible use and privacy

**This project is published for educational purposes.** Any practical deployment must be limited to lawful security administration and troubleshooting on infrastructure you own or are explicitly authorized to administer. Provide any notice and obtain any consent or other lawful basis required by the laws and policies that apply to your situation.

Do not use it to secretly spy on people, steal or obtain another person's browsing/connection history without authority, monitor accounts or devices without permission, or collect, use, or disclose personal data unlawfully. Taking or viewing someone else's activity history without authorization may be unlawful and may violate privacy, computer-misuse, data-protection, telecommunications, employment, or other laws, depending on the jurisdiction and circumstances.

The operator is responsible for determining what is lawful, giving required notice, limiting access, and setting an appropriate retention policy. **This repository is not legal advice, and a disclaimer does not make unauthorized monitoring lawful.**

## ⚙️ What it includes

- A small Xray Core dispatcher patch that copies a successfully sniffed destination into the access-log message.
- VLESS client identity from the Xray `email:` field.
- A Python collector for the active access log and rotated/compressed archives.
- SQLite storage with duplicate-event protection.
- A searchable dashboard with client selection, destination search, date filters, timestamps, and periodic refresh.
- Website favicon display with a text fallback (see the browser privacy note below).
- systemd examples for the dashboard and 30-minute log rotation.
- Read-only ACL examples for the collector account.
- Tailscale-only binding examples for private dashboard access.

## Architecture

```text
VLESS clients
    |
    v
Xray Core (sniffing enabled + version-specific patch)
    |
    v
Xray access.log  ---- logrotate every 30 minutes
    |                         |
    |                         +--> dated / compressed archives
    v
Unprivileged Python collector (read-only log access)
    |
    v
SQLite database
    |
    v
FastAPI + dashboard interface
    |
    v
Tailscale private IP --> authorized administrator's browser
```

The dashboard service runs as a dedicated unprivileged Linux user. It has read-only access to the Xray access log and its archives, and write access to its own database directory. The web service should bind only to the VPS's Tailscale address.

## What the dashboard records

Depending on what Xray writes and can identify, the reference collector stores:

- the timestamp from the Xray access-log entry;
- the configured Xray client email/label;
- the domain when sniffing identifies one, or the destination value available in the log;
- TCP/UDP protocol and destination port when parseable;
- inbound/routing tag when present.

The reference collector does not store raw access-log lines or source IP addresses in its event table. It does not capture complete URLs, page paths, browser search terms, messages, passwords, or page contents. It does not decrypt HTTPS or inspect packet payloads.

**A connection record is not proof that a person viewed or interacted with a website.** Applications routinely make background requests to APIs, CDNs, telemetry endpoints, update services, and other domains.

### Browser favicon requests

For each identified domain shown in the interface, the browser attempts to load `https://<domain>/favicon.ico` directly from that website. No third-party favicon lookup service is used. This means the dashboard administrator's browser makes outbound requests to the listed domains; those websites may observe the browser's public IP address and request time. Consider this before using the dashboard in a sensitive environment. If you do not want these requests, remove or disable the `favicon()` image loader in `static/index.html` before deployment.

## Logging limitations

A domain is not available for every connection. Xray may only have an IP address, or may be unable to identify a hostname when an application uses a direct IP, encrypted DNS, TLS Encrypted Client Hello (ECH), or another protocol that does not expose a hostname to the sniffing layer. If a destination is masked in the access log, this dashboard cannot reconstruct the missing domain.

This tool reports what the configured Xray logging path can identify. It does not bypass encryption or reveal otherwise hidden browsing activity.

## Reference environment

The walkthrough was exercised on this reference stack:

| Component | Reference version / configuration |
|---|---|
| Operating system | Ubuntu Server 24.04 LTS, amd64 |
| Panel | 3x-ui 3.11.0 |
| Xray Core source | `XTLS/Xray-core` tag `v26.10.21` |
| Go toolchain | Go 1.27.4, Linux amd64 |
| Dashboard | Python 3.12, FastAPI, Uvicorn, SQLite |
| Private access | Tailscale |

The Xray patch helper is **specific to the `v26.10.21` source layout**. Do not apply it blindly to another Xray release, architecture, or panel. Review the source diff, run the config test, keep a rollback binary, and schedule production replacement carefully.

## Setup guide

Follow the guides in order. They use generic paths and placeholders; adapt them to your own server after verifying the real paths and versions.

1. [Purpose, limitations, and data flow](docs/01-purpose-and-data-flow.md)
2. [Prerequisites and preparation](docs/02-prerequisites-and-preparation.md)
3. [Enable Xray domain sniffing and access logs](docs/03-enable-xray-domain-sniffing.md)
4. [Patch, build, test, and deploy Xray](docs/04-patch-build-and-deploy-xray.md)
5. [30-minute log rotation and read-only ACLs](docs/05-log-rotation-and-read-only-acls.md)
6. [Install the dashboard and collector](docs/06-install-dashboard.md)
7. [Restrict dashboard access with Tailscale](docs/07-private-access-with-tailscale.md)
8. [Operations, security, and troubleshooting](docs/08-operation-security-and-troubleshooting.md)

## Data retention

The example logrotate configuration keeps up to 672 half-hour log rotations (14 days) and compresses older archives. That retention applies to the **raw access-log archives only**. The SQLite database is separate and the reference application does not automatically delete old database records. Decide, document, and implement a database retention policy appropriate to your legal and operational requirements. Protect the database and its backups as sensitive connection metadata.

## Security notes

- Bind Uvicorn to the server's Tailscale IPv4 address only; do not use `0.0.0.0` or the public VPS address for this private deployment.
- Do not expose the dashboard port publicly as a shortcut.
- Keep the environment file root-owned with mode `0600`.
- Run the dashboard as an unprivileged service account.
- Grant read-only access only to the access log and its archives.
- Keep passwords, session secrets, Xray configuration, raw logs, and SQLite files out of Git.
- Limit tailnet membership and device access to trusted administrators.

See [SECURITY.md](SECURITY.md) and the [operations guide](docs/08-operation-security-and-troubleshooting.md).

## 🤖 AI assistance and development approach

**OpenAI ChatGPT (GPT-6) was used as a targeted development assistant, not as an automatic one-prompt project generator.** Its involvement was limited to specific tasks: discussing the architecture, drafting and explaining selected code and shell commands, helping diagnose errors from actual command output, and preparing/reviewing documentation.

The work was directed iteratively by the project requirements. The reference setup was deployed on a real Ubuntu VPS; commands were run step by step, their outputs were checked, and the resulting logging, archive import, private Tailscale binding, and dashboard access were tested. The AI contribution is disclosed openly rather than presenting the project as entirely human-written or hiding the use of AI.

This is not a claim that AI-generated code is automatically correct. The repository has not undergone a professional security audit or broad independent compatibility testing. Review the implementation and test it in a non-production environment before deployment, especially before replacing a production Xray binary. See [AI-ASSISTANCE.md](AI-ASSISTANCE.md) for a more specific breakdown.

## Open-source license and third-party software

The original code, scripts, and documentation in this repository are released under the **MIT License**. MIT is a permissive open-source license: it allows reuse, modification, and redistribution, subject to preserving the copyright and license notice.

The project is described as an educational reference, but the MIT License does **not** restrict use to educational purposes. A field-of-use restriction such as “educational use only” would conflict with the usual definition of an open-source license. See the [Open Source Initiative FAQ](https://opensource.org/faq). The responsible-use guidance above sets the project's intended and lawful-use expectations, but it does not alter the legal terms of the MIT License.

Xray Core, 3x-ui, Tailscale, Python, Go, and the installed Python packages are separate projects. This repository does not bundle their binaries or upstream source trees, and the MIT License here does not replace their own licenses or terms. The upstream Xray Core project declares MPL-2.0, and the 3x-ui project declares GPL-3.0; consult the upstream projects for their current notices and obligations. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Search and project scope

This project is relevant to searches for **Xray Core domain logging**, **3x-ui VLESS client attribution**, **per-client connection history**, **Xray access-log parsing**, **domain-level network auditing**, and a **self-hosted Tailscale-protected dashboard**. It is an educational reference implementation, not an official component of Xray Core, 3x-ui, or Tailscale.

## Repository contents

```text
.
├── README.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── AI-ASSISTANCE.md
├── CONTRIBUTING.md
├── SECURITY.md
├── app.py
├── env.example
├── requirements.txt
├── static/
│   └── index.html
├── config/
│   └── logrotate-x-ui.conf.example
├── systemd/
│   ├── x-ui-logrotate.service
│   ├── x-ui-logrotate.timer
│   └── xray-dashboard.service.example
├── scripts/
│   └── patch-xray-dispatcher.py
├── tests/
│   └── test_parser.py
└── docs/
    ├── 01-purpose-and-data-flow.md
    ├── 02-prerequisites-and-preparation.md
    ├── 03-enable-xray-domain-sniffing.md
    ├── 04-patch-build-and-deploy-xray.md
    ├── 05-log-rotation-and-read-only-acls.md
    ├── 06-install-dashboard.md
    ├── 07-private-access-with-tailscale.md
    └── 08-operation-security-and-troubleshooting.md
```

## Validation

Run the parser regression tests from the repository root after installing `requirements.txt`:

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

The tests cover client attribution, domain extraction, masked/IP destinations, ignored records, and duplicate fingerprints. They are focused unit tests, not a complete integration or security test suite.

## Contributing

Bug reports, documentation corrections, compatibility notes, and code improvements are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before opening an issue or pull request. Never include real client data or server secrets in a public contribution.

## Disclaimer

This repository is provided as an educational and technical reference, **as is and without warranty**. The operator is solely responsible for reviewing the software, securing the deployment, obtaining required authorization, complying with applicable law, and handling collected metadata appropriately. The maintainers do not authorize unlawful surveillance or access to another person's private activity.
