#!/usr/bin/env python3
"""Emit a GitHub Actions matrix for generated packages affected by a change."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from package_repository import BUCKET_DIR, FORMULA_DIR, ROOT, load_packages


def changed_files(base: str | None, head: str) -> list[str] | None:
    if not base or set(base) == {"0"}:
        return None
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def select(kind: str, files: list[str] | None) -> list[dict[str, str]]:
    packages = load_packages()
    generated_dir = BUCKET_DIR if kind == "scoop" else FORMULA_DIR
    generated_suffix = ".json" if kind == "scoop" else ".rb"
    available = {
        package.name: package
        for package in packages
        if (generated_dir / f"{package.name}{generated_suffix}").exists()
    }
    if files is None:
        names = set(available)
    else:
        shared = any(
            path.startswith("scripts/")
            or path == f".github/workflows/validate-{kind}.yml"
            for path in files
        )
        names = set(available) if shared else set()
        for path in files:
            candidate = Path(path)
            if candidate.parent.as_posix() in {"packages", generated_dir.name}:
                names.add(candidate.stem)
        names &= available.keys()
    runners = {
        "windows_amd64": "windows-2025",
        "windows_arm64": "windows-11-arm",
        "darwin_amd64": "macos-15-intel",
        "darwin_arm64": "macos-15",
        "linux_amd64": "ubuntu-24.04",
        "linux_arm64": "ubuntu-24.04-arm",
    }
    allowed_targets = (
        {"windows_amd64", "windows_arm64"}
        if kind == "scoop"
        else {
            "darwin_amd64",
            "darwin_arm64",
            "linux_amd64",
            "linux_arm64",
        }
    )
    return [
        {"package": name, "target": target, "runner": runners[target]}
        for name in sorted(names)
        for target in available[name].targets
        if target in allowed_targets
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("scoop", "homebrew"))
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    matrix = {"include": select(args.kind, changed_files(args.base, args.head))}
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
