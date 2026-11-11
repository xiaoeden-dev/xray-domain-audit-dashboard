#!/usr/bin/env python3
"""Apply the Xray v26.10.21 access-log destination patch to dispatcher/default.go.

This intentionally requires exactly two matching dispatcher paths. If upstream
source changes, the script stops rather than making a partial or guessed edit.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

NEEDLE = "destination.Address = net.ParseAddress(domain)\n"
INSERT = (
    NEEDLE
    + "\t\t\tif accessMessage := log.AccessMessageFromContext(ctx); accessMessage != nil {\n"
    + "\t\t\t\taccessMessage.To = destination\n"
    + "\t\t\t}\n"
)
EXPECTED_MATCHES = 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_file", nargs="?", default="app/dispatcher/default.go")
    args = parser.parse_args()
    path = Path(args.source_file)
    if not path.is_file():
        print(f"Source file not found: {path}", file=sys.stderr)
        return 2

    source = path.read_text(encoding="utf-8")
    count = source.count(NEEDLE)
    if count != EXPECTED_MATCHES:
        print(
            f"Refusing to patch: expected {EXPECTED_MATCHES} exact matches, found {count}. "
            "Inspect this Xray version manually; do not force the patch.",
            file=sys.stderr,
        )
        return 3

    backup = path.with_name(path.name + ".before-domain-log.bak")
    if backup.exists():
        print(f"Refusing to overwrite existing backup: {backup}", file=sys.stderr)
        return 4

    backup.write_text(source, encoding="utf-8")
    path.write_text(source.replace(NEEDLE, INSERT), encoding="utf-8")
    print(f"Patched {count} dispatcher paths.")
    print(f"Original source backup: {backup}")
    print("Next: run gofmt, git diff --check, and inspect the complete diff.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
