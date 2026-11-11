# AI assistance and development disclosure

Project: **Xray Domain Audit Dashboard**.

This repository was developed with targeted assistance from **OpenAI ChatGPT (GPT-6)**. AI use is disclosed clearly; the project is not presented as entirely human-written.

## Where AI was used

AI assistance was used for specific parts of the work:

- discussing the architecture and breaking the deployment into manageable steps;
- drafting and explaining selected code, including the reference FastAPI/SQLite collector, dashboard interface, and version-specific Xray patch helper;
- preparing example shell commands, systemd units, ACL rules, and logrotate configuration;
- interpreting errors and command output during the live setup process;
- drafting, organizing, and checking the written setup guide.

## How the work was developed

The implementation was directed by concrete project requirements and refined iteratively. The commands were executed on a real Ubuntu VPS, not merely described in a generated walkthrough. The operator checked the command results and verified the reference deployment, including Xray domain logging, client labels in access logs, 30-minute log rotation, read-only log access, historical archive import, SQLite collection, and access to the dashboard over a private Tailscale connection.

This distinction matters: AI helped with selected development tasks, but the project was not treated as a one-prompt output to publish without testing. The repository includes the actual source, configuration examples, setup steps, limitations, and troubleshooting notes so others can inspect and reproduce the work.

## Limitations

AI assistance does not constitute a professional security audit, legal review, independent code review, or proof of compatibility beyond the documented reference environment. Generated suggestions can be wrong or incomplete. Review code and commands before use, test in a non-production environment, and verify the source layout before applying the Xray patch to any release other than the pinned version.
