#!/usr/bin/env python3
"""Validate generated metadata deterministically and optionally verify remote bytes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from package_repository import (
    BUCKET_DIR,
    FORMULA_DIR,
    SHA256_RE,
    GitHubClient,
    Package,
    PackageError,
    _read_json,
    load_package,
    load_packages,
    parse_version,
    render_formula,
    render_scoop,
)


def _asset_record(
    url: Any, digest: Any, expected_url: str, target_name: str
) -> dict[str, str]:
    if not isinstance(url, str) or url != expected_url:
        raise PackageError(f"unexpected URL for {target_name}: {url!r}")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise PackageError(f"invalid SHA-256 for {target_name}")
    return {"filename": url.rsplit("/", 1)[-1], "url": url, "sha256": digest}


def validate_scoop(package: Package) -> tuple[str, dict[str, Any]]:
    path = BUCKET_DIR / f"{package.name}.json"
    data = _read_json(path)
    if not isinstance(data, dict):
        raise PackageError(f"{path} must contain an object")
    version = data.get("version")
    if not isinstance(version, str):
        raise PackageError(f"{path} has no version")
    parse_version(version)
    architecture = data.get("architecture")
    if not isinstance(architecture, dict):
        raise PackageError(f"{path} has no architecture map")
    assets: dict[str, dict[str, str]] = {}
    for target_name, scoop_arch in (
        ("windows_amd64", "64bit"),
        ("windows_arm64", "arm64"),
    ):
        if target_name not in package.targets:
            continue
        entry = architecture.get(scoop_arch)
        if not isinstance(entry, dict):
            raise PackageError(f"{path} is missing {scoop_arch}")
        filename = package.targets[target_name].asset(package.name, version)
        expected_url = f"{package.homepage}/releases/download/v{version}/{filename}"
        assets[target_name] = _asset_record(
            entry.get("url"), entry.get("hash"), expected_url, target_name
        )
    verified = {"version": version, "assets": assets}
    expected = render_scoop(package, verified)
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        raise PackageError(f"{path} is not the deterministic renderer output")
    return version, verified


def validate_formula(package: Package) -> tuple[str, dict[str, Any]]:
    path = FORMULA_DIR / f"{package.name}.rb"
    actual = path.read_text(encoding="utf-8")
    scoop_path = BUCKET_DIR / f"{package.name}.json"
    if not scoop_path.exists():
        raise PackageError(f"{path} has no companion Scoop manifest")
    version, _ = validate_scoop(package)
    pairs = re.findall(
        r'^      url "([^"]+)"\n      sha256 "([0-9a-f]+)"$', actual, re.MULTILINE
    )
    non_windows = [name for name in package.targets if not name.startswith("windows_")]
    if len(pairs) != len(non_windows):
        raise PackageError(
            f"{path} does not contain one URL/hash pair per Homebrew target"
        )
    assets: dict[str, dict[str, str]] = {}
    remaining = dict(pairs)
    for target_name in non_windows:
        filename = package.targets[target_name].asset(package.name, version)
        expected_url = f"{package.homepage}/releases/download/v{version}/{filename}"
        digest = remaining.pop(expected_url, None)
        assets[target_name] = _asset_record(
            expected_url, digest, expected_url, target_name
        )
    if remaining:
        raise PackageError(f"{path} contains unexpected release URLs")
    verified = {"version": version, "assets": assets}
    expected = render_formula(package, verified)
    if actual != expected:
        raise PackageError(f"{path} is not the deterministic renderer output")
    return version, verified


def verify_online(verified: dict[str, Any]) -> None:
    client = GitHubClient()
    for asset in verified["assets"].values():
        with __import__("tempfile").TemporaryDirectory(
            prefix="metadata-hash-"
        ) as directory:
            destination = Path(directory) / asset["filename"]
            actual = client.download_and_hash(asset["url"], destination)
        if actual != asset["sha256"]:
            raise PackageError(f"online SHA-256 mismatch for {asset['filename']}")


def validate_repository() -> None:
    for package in load_packages():
        scoop_path = BUCKET_DIR / f"{package.name}.json"
        formula_path = FORMULA_DIR / f"{package.name}.rb"
        if scoop_path.exists() != formula_path.exists():
            raise PackageError(
                f"{package.name} must have both generated files or neither"
            )
        if scoop_path.exists():
            scoop_version, _ = validate_scoop(package)
            formula_version, _ = validate_formula(package)
            if scoop_version != formula_version:
                raise PackageError(f"generated versions differ for {package.name}")
    known = {package.name for package in load_packages()}
    for path in [*BUCKET_DIR.glob("*.json"), *FORMULA_DIR.glob("*.rb")]:
        if path.stem not in known:
            raise PackageError(f"generated metadata has no package definition: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("repository", "scoop", "homebrew"))
    parser.add_argument("package", nargs="?")
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    try:
        if args.kind == "repository":
            if args.package or args.online:
                parser.error(
                    "repository validation does not accept a package or --online"
                )
            validate_repository()
            print("generated metadata is consistent")
            return 0
        if not args.package:
            parser.error("package is required for Scoop or Homebrew validation")
        package = load_package(args.package)
        version, verified = (
            validate_scoop(package)
            if args.kind == "scoop"
            else validate_formula(package)
        )
        if args.online:
            verify_online(verified)
        print(f"validated {args.kind} metadata for {package.name} {version}")
        return 0
    except (PackageError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
