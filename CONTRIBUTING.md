# Contributing

Contributions are welcome, including documentation corrections, tested compatibility notes, bug reports, and code improvements.

## Responsible use and privacy

This project is intended as an educational reference for authorized administration. Do not contribute features or instructions intended for covert surveillance, unauthorized access, theft of browsing history, credential capture, or unlawful collection or disclosure of personal data.

Only submit synthetic examples. Never include real IP addresses, hostnames, client labels, access logs, private configs, UUIDs, cookies, passwords, API tokens, session secrets, or database files.


## AI-assisted contributions

AI tools may be used as development aids, but contributors remain responsible for the changes they submit. Do not submit unreviewed generated output. Explain material AI assistance where it helps reviewers understand how a change was produced, and include the tests and environment used to verify it.

## Before opening a change

- Keep examples generic and use obviously synthetic data.
- Test shell examples on a disposable Ubuntu VM where practical.
- State the Ubuntu, Xray Core, Go, Python, and panel versions used for any compatibility claim.
- Treat changes to `scripts/patch-xray-dispatcher.py` as version-sensitive. Confirm the expected source-pattern count and inspect the generated diff.
- Do not submit compiled Xray binaries or third-party source trees.
- Check that no secrets, personal information, or real monitoring data are included in the diff.

## Documentation style

Prefer clear, short steps. Explain why a command is needed, identify commands that restart a service, and include a rollback path for changes to Xray or systemd.

## Tests before submitting

```bash
python3 -m py_compile app.py
python3 scripts/patch-xray-dispatcher.py --help
```

For a source patch change, test against the exact pinned Xray Core tag in a clean checkout and inspect `git diff --check` plus the complete diff. Do not test patches against an active production checkout without a backup.
