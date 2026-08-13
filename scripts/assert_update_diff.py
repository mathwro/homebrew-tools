#!/usr/bin/env python3
"""Fail unless an update changed only the selected package's generated files."""

from __future__ import annotations

import argparse
import subprocess
import sys

from package_repository import PACKAGE_RE, ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    args = parser.parse_args()
    if not PACKAGE_RE.fullmatch(args.package):
        parser.error("invalid package name")
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    changed = {line[3:] for line in result.stdout.splitlines() if len(line) >= 4}
    expected = {f"bucket/{args.package}.json", f"Formula/{args.package}.rb"}
    unexpected = changed - expected
    if unexpected:
        print(
            "error: update changed unexpected paths: " + ", ".join(sorted(unexpected)),
            file=sys.stderr,
        )
        return 1
    if changed and changed != expected:
        print("error: update must change both generated files", file=sys.stderr)
        return 1
    print(
        "no metadata change"
        if not changed
        else "update changed exactly both generated files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
