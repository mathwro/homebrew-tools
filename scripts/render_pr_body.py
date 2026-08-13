#!/usr/bin/env python3
"""Render an auditable updater pull-request body from verified release JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_json", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.release_json.read_text(encoding="utf-8"))
    lines = [
        f"Updates `{data['package']}` to [{data['tag']}]({data['release_url']}).",
        "",
        "Verified release assets:",
        "",
        "| Target | Asset | SHA-256 |",
        "|---|---|---|",
    ]
    for target, asset in sorted(data["assets"].items()):
        lines.append(f"| `{target}` | `{asset['filename']}` | `{asset['sha256']}` |")
    lines.extend(
        [
            "",
            "The updater independently downloaded each archive, matched its SHA-256 against `checksums.txt`, and inspected archive paths before generating both metadata files.",
            "",
        ]
    )
    args.output.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
