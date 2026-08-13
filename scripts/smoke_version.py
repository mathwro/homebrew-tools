#!/usr/bin/env python3
"""Run a package's non-mutating version command and require the expected version."""

from __future__ import annotations

import argparse
import subprocess
import sys

from package_repository import load_package, parse_version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("version")
    parser.add_argument("executable")
    args = parser.parse_args()
    parse_version(args.version)
    package = load_package(args.package)
    result = subprocess.run(
        [args.executable, *package.version_args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        print(output, file=sys.stderr)
        print(f"error: version command exited {result.returncode}", file=sys.stderr)
        return 1
    if args.version not in output:
        print(output, file=sys.stderr)
        print(f"error: version output does not contain {args.version}", file=sys.stderr)
        return 1
    print(output.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
