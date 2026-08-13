#!/usr/bin/env python3
"""Typed Go and Rust source-release adapters used by the reusable workflow."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile

from package_repository import PackageError, inspect_archive, parse_checksums


STABLE_VERSION_RE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
PRERELEASE_VERSION_RE = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-"
    r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
)
PACKAGE_NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
BINARY_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
GO_SYMBOL_RE = re.compile(r"[A-Za-z0-9_./-]+\.[A-Za-z_][A-Za-z0-9_]*")
FEATURE_RE = re.compile(r"[A-Za-z0-9_-]+")

TARGETS = (
    {
        "token": "windows_amd64",
        "runner": "windows-2025",
        "goos": "windows",
        "goarch": "amd64",
        "rust_target": "x86_64-pc-windows-msvc",
        "archive": "zip",
    },
    {
        "token": "windows_arm64",
        "runner": "windows-11-arm",
        "goos": "windows",
        "goarch": "arm64",
        "rust_target": "aarch64-pc-windows-msvc",
        "archive": "zip",
    },
    {
        "token": "darwin_amd64",
        "runner": "macos-15-intel",
        "goos": "darwin",
        "goarch": "amd64",
        "rust_target": "x86_64-apple-darwin",
        "archive": "tar.gz",
    },
    {
        "token": "darwin_arm64",
        "runner": "macos-15",
        "goos": "darwin",
        "goarch": "arm64",
        "rust_target": "aarch64-apple-darwin",
        "archive": "tar.gz",
    },
    {
        "token": "linux_amd64",
        "runner": "ubuntu-24.04",
        "goos": "linux",
        "goarch": "amd64",
        "rust_target": "x86_64-unknown-linux-musl",
        "archive": "tar.gz",
    },
    {
        "token": "linux_arm64",
        "runner": "ubuntu-24.04-arm",
        "goos": "linux",
        "goarch": "arm64",
        "rust_target": "aarch64-unknown-linux-musl",
        "archive": "tar.gz",
    },
)

COMMON_KEYS = {
    "schema",
    "package",
    "binary",
    "adapter",
    "project_path",
    "release_branch",
    "version_args",
    "help_args",
    "macos_sign",
    "go",
    "rust",
}
GO_KEYS = {"main", "module_file", "ldflags"}
RUST_KEYS = {"package", "manifest", "features"}


class ReleaseError(RuntimeError):
    """A source release violates the shared contract."""


def _strict_keys(value: dict, allowed: set[str], context: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ReleaseError(f"{context} contains unknown keys: {', '.join(unknown)}")


def _safe_relative(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ReleaseError(f"{field} must stay inside the source repository")
    return path.as_posix()


def _string_list(value: object, field: str, default: tuple[str, ...]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ReleaseError(f"{field} must be a non-empty string array")
    return value


def load_config(path: Path) -> dict:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError(f"cannot read release config {path}: {error}") from error
    if not isinstance(config, dict):
        raise ReleaseError("release config must be a JSON object")
    _strict_keys(config, COMMON_KEYS, "release config")
    if config.get("schema") != 1:
        raise ReleaseError("release config schema must be 1")
    if not isinstance(config.get("package"), str) or not PACKAGE_NAME_RE.fullmatch(
        config["package"]
    ):
        raise ReleaseError("package must be a stable lowercase package name")
    if not isinstance(config.get("binary"), str) or not BINARY_NAME_RE.fullmatch(
        config["binary"]
    ):
        raise ReleaseError("binary must be a safe executable name")
    if config.get("adapter") not in ("go", "rust"):
        raise ReleaseError("adapter must be one of: go, rust")

    config["project_path"] = _safe_relative(config.get("project_path", "."), "project_path")
    config["release_branch"] = config.get("release_branch", "main")
    if not isinstance(config["release_branch"], str) or not re.fullmatch(
        r"[A-Za-z0-9._/-]+", config["release_branch"]
    ):
        raise ReleaseError("release_branch is invalid")
    config["version_args"] = _string_list(
        config.get("version_args"), "version_args", ("--version",)
    )
    config["help_args"] = _string_list(config.get("help_args"), "help_args", ("--help",))
    config["macos_sign"] = config.get("macos_sign", "none")
    if config["macos_sign"] not in ("none", "adhoc"):
        raise ReleaseError("macos_sign must be none or adhoc")

    project = Path(config["project_path"])
    if config["adapter"] == "go":
        if "rust" in config:
            raise ReleaseError("a Go release config cannot contain rust options")
        options = config.get("go", {})
        if not isinstance(options, dict):
            raise ReleaseError("go must be an object")
        _strict_keys(options, GO_KEYS, "go")
        options["main"] = _safe_relative(options.get("main", "."), "go.main")
        options["module_file"] = _safe_relative(
            options.get("module_file", "go.mod"), "go.module_file"
        )
        ldflags = options.get("ldflags", {})
        if not isinstance(ldflags, dict) or set(ldflags) - {"version", "commit", "date"}:
            raise ReleaseError("go.ldflags may contain only version, commit, and date")
        for field, symbol in ldflags.items():
            if not isinstance(symbol, str) or not GO_SYMBOL_RE.fullmatch(symbol):
                raise ReleaseError(f"go.ldflags.{field} is not a valid Go symbol")
        options["ldflags"] = ldflags
        config["go"] = options
        config["toolchain_file"] = (project / options["module_file"]).as_posix()
    else:
        if "go" in config:
            raise ReleaseError("a Rust release config cannot contain go options")
        options = config.get("rust", {})
        if not isinstance(options, dict):
            raise ReleaseError("rust must be an object")
        _strict_keys(options, RUST_KEYS, "rust")
        options["package"] = options.get("package", config["package"])
        if not isinstance(options["package"], str) or not PACKAGE_NAME_RE.fullmatch(
            options["package"]
        ):
            raise ReleaseError("rust.package is invalid")
        options["manifest"] = _safe_relative(
            options.get("manifest", "Cargo.toml"), "rust.manifest"
        )
        features = options.get("features", [])
        if not isinstance(features, list) or not all(
            isinstance(feature, str) and FEATURE_RE.fullmatch(feature) for feature in features
        ):
            raise ReleaseError("rust.features must contain simple Cargo feature names")
        options["features"] = features
        config["rust"] = options
        config["toolchain_file"] = (project / options["manifest"]).as_posix()
    return config


def parse_tag(tag: str) -> tuple[str, bool]:
    if not tag.startswith("v"):
        raise ReleaseError("release tag must start with v")
    version = tag[1:]
    if STABLE_VERSION_RE.fullmatch(version):
        return version, True
    if PRERELEASE_VERSION_RE.fullmatch(version):
        return version, False
    raise ReleaseError("release tag must be stable SemVer or SemVer with a prerelease suffix")


def target(token: str) -> dict:
    for item in TARGETS:
        if item["token"] == token:
            return dict(item)
    raise ReleaseError(f"unsupported release target: {token}")


def target_matrix(binary: str) -> dict:
    include = []
    for item in TARGETS:
        value = dict(item)
        value["executable"] = binary + (".exe" if item["goos"] == "windows" else "")
        include.append(value)
    return {"include": include}


def _run(
    arguments: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> str:
    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            env=env,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = ""
        if isinstance(error, subprocess.CalledProcessError):
            detail = (error.stderr or error.stdout or "").strip()
        raise ReleaseError(
            f"command failed: {' '.join(arguments)}" + (f": {detail}" if detail else "")
        ) from error
    return completed.stdout.strip() if capture else ""


def validate_source(config: dict, tag: str) -> dict[str, str]:
    version, stable = parse_tag(tag)
    tag_type = _run(["git", "cat-file", "-t", f"refs/tags/{tag}"], capture=True)
    if tag_type != "tag":
        raise ReleaseError(f"{tag} must be an annotated or signed tag")
    commit = _run(["git", "rev-list", "-n", "1", tag], capture=True)
    head = _run(["git", "rev-parse", "HEAD"], capture=True)
    if commit != head:
        raise ReleaseError(f"checked-out commit does not match {tag}")
    _run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            commit,
            f"origin/{config['release_branch']}",
        ]
    )
    epoch = _run(["git", "show", "-s", "--format=%ct", commit], capture=True)
    if not epoch.isdigit() or int(epoch) <= 0:
        raise ReleaseError("tagged commit has an invalid timestamp")

    if config["adapter"] == "rust":
        manifest = Path(config["project_path"]) / config["rust"]["manifest"]
        try:
            package_version = tomllib.loads(manifest.read_text(encoding="utf-8"))["package"][
                "version"
            ]
        except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
            raise ReleaseError(f"cannot read Rust package version from {manifest}") from error
        if package_version != version:
            raise ReleaseError(
                f"tag version {version} does not match Cargo package version {package_version}"
            )

    return {
        "tag": tag,
        "version": version,
        "stable": str(stable).lower(),
        "prerelease": str(not stable).lower(),
        "commit": commit,
        "epoch": epoch,
        "package": config["package"],
        "binary": config["binary"],
        "adapter": config["adapter"],
        "toolchain_file": config["toolchain_file"],
        "matrix": json.dumps(target_matrix(config["binary"]), separators=(",", ":")),
    }


def write_outputs(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def test_source(config: dict) -> None:
    cwd = Path(config["project_path"])
    if config["adapter"] == "go":
        _run(["go", "test", "./...", "-count=1"], cwd=cwd)
        return
    command = [
        "cargo",
        "test",
        "--locked",
        "--manifest-path",
        config["rust"]["manifest"],
        "--package",
        config["rust"]["package"],
    ]
    if config["rust"]["features"]:
        command.extend(["--features", ",".join(config["rust"]["features"])])
    _run(command, cwd=cwd)


def _go_binary(
    config: dict, item: dict, version: str, commit: str, epoch: int, destination: Path
) -> None:
    stamp = dt.datetime.fromtimestamp(epoch, tz=dt.UTC).date().isoformat()
    values = {"version": version, "commit": commit, "date": stamp}
    ldflags = ["-s", "-w"]
    for field in ("version", "commit", "date"):
        symbol = config["go"]["ldflags"].get(field)
        if symbol:
            ldflags.extend(["-X", f"{symbol}={values[field]}"])
    environment = os.environ.copy()
    environment.update(
        {
            "CGO_ENABLED": "0",
            "GOOS": item["goos"],
            "GOARCH": item["goarch"],
            "SOURCE_DATE_EPOCH": str(epoch),
        }
    )
    _run(
        [
            "go",
            "build",
            "-mod=readonly",
            "-trimpath",
            "-ldflags",
            " ".join(ldflags),
            "-o",
            str(destination.resolve()),
            config["go"]["main"],
        ],
        cwd=Path(config["project_path"]),
        env=environment,
    )


def _rust_binary(
    config: dict, item: dict, commit: str, epoch: int, destination: Path
) -> None:
    environment = os.environ.copy()
    environment.update({"RELEASE_COMMIT": commit, "SOURCE_DATE_EPOCH": str(epoch)})
    command = [
        "cargo",
        "build",
        "--locked",
        "--release",
        "--target",
        item["rust_target"],
        "--manifest-path",
        config["rust"]["manifest"],
        "--package",
        config["rust"]["package"],
    ]
    if config["rust"]["features"]:
        command.extend(["--features", ",".join(config["rust"]["features"])])
    cwd = Path(config["project_path"])
    _run(command, cwd=cwd, env=environment)
    built = cwd / "target" / item["rust_target"] / "release" / destination.name
    if not built.is_file():
        raise ReleaseError(f"Rust build did not create {built}")
    shutil.copy2(built, destination)


def _smoke_binary(binary: Path, config: dict, version: str) -> None:
    for arguments, require_version in (
        (config["version_args"], True),
        (config["help_args"], False),
    ):
        try:
            completed = subprocess.run(
                [str(binary.resolve()), *arguments],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            output = error.stdout.strip() if isinstance(error, subprocess.CalledProcessError) else ""
            raise ReleaseError(
                f"release smoke command failed: {binary.name} {' '.join(arguments)}"
                + (f": {output}" if output else "")
            ) from error
        if require_version and version not in completed.stdout:
            raise ReleaseError(
                f"version output for {binary.name} does not contain {version!r}: "
                f"{completed.stdout.strip()!r}"
            )


def _write_zip(destination: Path, binary: Path, archive_name: str, epoch: int) -> None:
    stamp = dt.datetime.fromtimestamp(epoch, tz=dt.UTC)
    date_time = max((1980, 1, 1, 0, 0, 0), stamp.timetuple()[:6])
    info = zipfile.ZipInfo(archive_name, date_time=date_time)
    info.create_system = 3
    info.external_attr = 0o755 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(info, binary.read_bytes())


def _write_tar_gz(destination: Path, binary: Path, archive_name: str, epoch: int) -> None:
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                info = tarfile.TarInfo(archive_name)
                info.mode = 0o755
                info.size = binary.stat().st_size
                info.mtime = epoch
                with binary.open("rb") as source:
                    archive.addfile(info, source)


def build_target(
    config: dict, tag: str, commit: str, epoch: int, token: str, output: Path
) -> Path:
    version, _ = parse_tag(tag)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ReleaseError("commit must be a full lowercase Git commit SHA")
    if epoch <= 0:
        raise ReleaseError("source epoch must be positive")
    item = target(token)
    executable = config["binary"] + (".exe" if item["goos"] == "windows" else "")
    output.mkdir(parents=True, exist_ok=True)
    suffix = ".zip" if item["archive"] == "zip" else ".tar.gz"
    destination = output / f"{config['package']}_{version}_{token}{suffix}"

    with tempfile.TemporaryDirectory(prefix="source-release-") as temporary:
        binary = Path(temporary) / executable
        if config["adapter"] == "go":
            _go_binary(config, item, version, commit, epoch, binary)
        else:
            _rust_binary(config, item, commit, epoch, binary)
        binary.chmod(0o755)
        if item["goos"] == "darwin" and config["macos_sign"] == "adhoc":
            _run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(binary)])
        _smoke_binary(binary, config, version)
        if item["archive"] == "zip":
            _write_zip(destination, binary, executable, epoch)
        else:
            _write_tar_gz(destination, binary, executable, epoch)
    try:
        inspect_archive(destination, executable)
    except PackageError as error:
        raise ReleaseError(str(error)) from error
    return destination


def expected_assets(config: dict, version: str) -> list[str]:
    parse_tag("v" + version)
    assets = []
    for item in TARGETS:
        suffix = ".zip" if item["archive"] == "zip" else ".tar.gz"
        assets.append(f"{config['package']}_{version}_{item['token']}{suffix}")
    return sorted(assets)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage_release(config: dict, version: str, directory: Path) -> None:
    expected = expected_assets(config, version)
    actual = sorted(
        path.name for path in directory.iterdir() if path.is_file() and path.name != "checksums.txt"
    )
    if actual != expected:
        raise ReleaseError(f"release assets differ: expected {expected!r}, got {actual!r}")
    for item in TARGETS:
        suffix = ".zip" if item["archive"] == "zip" else ".tar.gz"
        archive = directory / f"{config['package']}_{version}_{item['token']}{suffix}"
        executable = config["binary"] + (".exe" if item["goos"] == "windows" else "")
        try:
            inspect_archive(archive, executable)
        except PackageError as error:
            raise ReleaseError(str(error)) from error

    checksums = directory / "checksums.txt"
    checksums.write_text(
        "".join(f"{_digest(directory / name)}  {name}\n" for name in expected),
        encoding="utf-8",
        newline="\n",
    )
    try:
        parsed = parse_checksums(checksums.read_bytes())
    except PackageError as error:
        raise ReleaseError(str(error)) from error
    if sorted(parsed) != expected:
        raise ReleaseError("checksums.txt does not cover the exact release asset set")
    for name, digest in parsed.items():
        if _digest(directory / name) != digest:
            raise ReleaseError(f"checksum verification failed for {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("release.json"))
    commands = parser.add_subparsers(dest="command", required=True)

    outputs = commands.add_parser("outputs")
    outputs.add_argument("--tag", required=True)
    outputs.add_argument("--github-output", type=Path, required=True)

    commands.add_parser("test")

    build = commands.add_parser("build")
    build.add_argument("--tag", required=True)
    build.add_argument("--commit", required=True)
    build.add_argument("--epoch", type=int, required=True)
    build.add_argument("--target", required=True)
    build.add_argument("--output", type=Path, required=True)

    stage = commands.add_parser("stage")
    stage.add_argument("--version", required=True)
    stage.add_argument("--directory", type=Path, required=True)

    arguments = parser.parse_args()
    try:
        config = load_config(arguments.config)
        if arguments.command == "outputs":
            write_outputs(arguments.github_output, validate_source(config, arguments.tag))
        elif arguments.command == "test":
            test_source(config)
        elif arguments.command == "build":
            build_target(
                config,
                arguments.tag,
                arguments.commit,
                arguments.epoch,
                arguments.target,
                arguments.output,
            )
        else:
            stage_release(config, arguments.version, arguments.directory)
    except ReleaseError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
