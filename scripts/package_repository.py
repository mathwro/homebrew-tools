#!/usr/bin/env python3
"""Verify immutable GitHub releases and render Scoop/Homebrew metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = ROOT / "packages"
BUCKET_DIR = ROOT / "bucket"
FORMULA_DIR = ROOT / "Formula"

PACKAGE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,38})/[A-Za-z0-9_.-]{1,100}$"
)
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ASSET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,199}$")
COMMAND_ARG_RE = re.compile(r"^[A-Za-z0-9_.=:+/-]+$")
LICENSE_RE = re.compile(r"^[A-Za-z0-9-.+() ]{1,100}$")
TARGETS = {
    "windows_amd64": ("windows", "amd64", "zip"),
    "windows_arm64": ("windows", "arm64", "zip"),
    "darwin_amd64": ("darwin", "amd64", "tar.gz"),
    "darwin_arm64": ("darwin", "arm64", "tar.gz"),
    "linux_amd64": ("linux", "amd64", "tar.gz"),
    "linux_arm64": ("linux", "arm64", "tar.gz"),
}
SCRIPT_SUFFIXES = {".bat", ".cmd", ".ps1", ".sh", ".bash", ".zsh", ".fish"}
MAX_ARCHIVE_CONTENT_SIZE = 1 << 30
USER_AGENT = "homebrew-tools-release-verifier/1"
MAX_ARCHIVE_DOWNLOAD_SIZE = 256 << 20


class PackageError(RuntimeError):
    """A package definition, release, or generated file is invalid."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PackageError(f"duplicate key in package definition: {key}")
        result[key] = value
    return result


def _read_json(path: Path, *, reject_duplicates: bool = True) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            hook = _reject_duplicate_pairs if reject_duplicates else None
            return json.load(handle, object_pairs_hook=hook)
    except (OSError, json.JSONDecodeError) as error:
        raise PackageError(f"cannot read {path}: {error}") from error


def _expect_keys(
    value: dict[str, Any], required: set[str], optional: set[str], context: str
) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing:
        raise PackageError(f"{context} is missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise PackageError(f"{context} has unknown keys: {', '.join(sorted(unknown))}")


@dataclass(frozen=True)
class Target:
    name: str
    asset_template: str
    archive_executable: str

    def asset(self, package: str, version: str) -> str:
        os_name, arch, extension = TARGETS[self.name]
        try:
            asset = self.asset_template.format(
                package=package,
                version=version,
                os=os_name,
                arch=arch,
                ext=extension,
            )
        except (KeyError, ValueError) as error:
            raise PackageError(
                f"invalid asset template for {self.name}: {error}"
            ) from error
        if not ASSET_RE.fullmatch(asset) or "/" in asset or "\\" in asset:
            raise PackageError(f"unsafe asset filename for {self.name}: {asset!r}")
        expected_suffix = ".zip" if os_name == "windows" else ".tar.gz"
        if not asset.endswith(expected_suffix):
            raise PackageError(
                f"{self.name} asset must end with {expected_suffix}: {asset}"
            )
        return asset


@dataclass(frozen=True)
class Package:
    name: str
    repository: str
    description: str
    license: str | None
    executable: str
    version_args: tuple[str, ...]
    targets: dict[str, Target]

    @property
    def homepage(self) -> str:
        return f"https://github.com/{self.repository}"

    @property
    def formula_class(self) -> str:
        return "".join(
            part[:1].upper() + part[1:]
            for part in re.split(r"[^A-Za-z0-9]+", self.name)
            if part
        )


def load_package(name: str, packages_dir: Path = PACKAGES_DIR) -> Package:
    if not PACKAGE_RE.fullmatch(name):
        raise PackageError(f"invalid package name: {name!r}")
    path = packages_dir / f"{name}.yml"
    data = _read_json(path)
    if not isinstance(data, dict):
        raise PackageError(f"{path} must contain an object")
    _expect_keys(
        data,
        {
            "package",
            "repository",
            "description",
            "license",
            "executable",
            "version_command",
            "targets",
        },
        set(),
        str(path),
    )
    if data["package"] != name or not PACKAGE_RE.fullmatch(str(data["package"])):
        raise PackageError(f"package identity must match filename: {name}")
    repository = data["repository"]
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        raise PackageError(f"invalid repository for {name}")
    description = data["description"]
    if (
        not isinstance(description, str)
        or not 1 <= len(description) <= 80
        or any(c in description for c in "\r\n\0")
    ):
        raise PackageError(
            f"description for {name} must be 1-80 characters on one line"
        )
    license_value = data["license"]
    if license_value is not None and (
        not isinstance(license_value, str) or not LICENSE_RE.fullmatch(license_value)
    ):
        raise PackageError(f"invalid SPDX license expression for {name}")
    executable = data["executable"]
    if not isinstance(executable, str) or not PACKAGE_RE.fullmatch(executable):
        raise PackageError(f"invalid executable for {name}")
    version_args = data["version_command"]
    if (
        not isinstance(version_args, list)
        or not 1 <= len(version_args) <= 4
        or any(
            not isinstance(arg, str) or not COMMAND_ARG_RE.fullmatch(arg)
            for arg in version_args
        )
    ):
        raise PackageError(f"invalid version_command for {name}")
    targets_data = data["targets"]
    if not isinstance(targets_data, dict) or not targets_data:
        raise PackageError(f"{name} must declare at least one target")
    unknown_targets = targets_data.keys() - TARGETS.keys()
    if unknown_targets:
        raise PackageError(
            f"unsupported targets for {name}: {', '.join(sorted(unknown_targets))}"
        )
    targets: dict[str, Target] = {}
    for target_name in TARGETS:
        if target_name not in targets_data:
            continue
        target_data = targets_data[target_name]
        if not isinstance(target_data, dict):
            raise PackageError(f"target {target_name} for {name} must be an object")
        _expect_keys(
            target_data, {"asset", "archive_executable"}, set(), f"{name}.{target_name}"
        )
        template = target_data["asset"]
        archive_executable = target_data["archive_executable"]
        if not isinstance(template, str) or len(template) > 250:
            raise PackageError(f"invalid asset template for {name}.{target_name}")
        if not isinstance(archive_executable, str) or not ASSET_RE.fullmatch(
            archive_executable
        ):
            raise PackageError(f"invalid archive executable for {name}.{target_name}")
        target = Target(target_name, template, archive_executable)
        target.asset(name, "1.2.3")
        targets[target_name] = target
    return Package(
        name,
        repository,
        description,
        license_value,
        executable,
        tuple(version_args),
        targets,
    )


def load_packages(packages_dir: Path = PACKAGES_DIR) -> list[Package]:
    names = sorted(path.stem for path in packages_dir.glob("*.yml"))
    return [load_package(name, packages_dir) for name in names]


def parse_version(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(version)
    if not match:
        raise PackageError(
            f"version must be stable SemVer MAJOR.MINOR.PATCH: {version!r}"
        )
    return tuple(int(group) for group in match.groups())  # type: ignore[return-value]


def validate_tag_version(tag: str, version: str) -> None:
    parse_version(version)
    if tag != f"v{version}":
        raise PackageError(f"tag/version mismatch: expected v{version}, got {tag}")


def normalize_event(
    repository: str,
    package_name: str,
    tag: str,
    version: str,
    release_id: str,
    packages_dir: Path = PACKAGES_DIR,
) -> dict[str, str]:
    validate_tag_version(tag, version)
    if not REPOSITORY_RE.fullmatch(repository):
        raise PackageError(f"invalid payload repository: {repository!r}")
    if not PACKAGE_RE.fullmatch(package_name):
        raise PackageError(f"invalid payload package: {package_name!r}")

    packages = load_packages(packages_dir)
    matches = [
        package
        for package in packages
        if package.name == package_name and package.repository == repository
    ]
    if len(matches) != 1:
        raise PackageError(
            f"package/repository pair is not allowlisted: {package_name} -> {repository}"
        )
    if release_id and not re.fullmatch(r"[1-9][0-9]*", release_id):
        raise PackageError(f"invalid GitHub release ID: {release_id!r}")
    return {
        "repository": repository,
        "package": package_name,
        "tag": tag,
        "version": version,
        "release_id": release_id,
    }


def write_github_outputs(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def parse_checksums(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PackageError("checksums.txt is not UTF-8") from error
    checksums: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-f]{64})[ \t]+\*?([^\s]+)", line)
        if not match:
            raise PackageError(f"invalid checksums.txt line {line_number}")
        digest, filename = match.groups()
        if not ASSET_RE.fullmatch(filename) or "/" in filename or "\\" in filename:
            raise PackageError(
                f"unsafe checksum filename on line {line_number}: {filename!r}"
            )
        if filename in checksums:
            raise PackageError(f"duplicate checksum filename: {filename}")
        checksums[filename] = digest
    if not checksums:
        raise PackageError("checksums.txt is empty")
    return checksums


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
    ):
        raise PackageError(f"archive contains absolute path: {name!r}")
    if ".." in path.parts:
        raise PackageError(f"archive contains parent traversal: {name!r}")
    return normalized.rstrip("/")


def _reject_installer_script(name: str, expected_executable: str) -> None:
    if (
        PurePosixPath(name).name != expected_executable
        and PurePosixPath(name).suffix.lower() in SCRIPT_SUFFIXES
    ):
        raise PackageError(f"archive contains unexpected installer script: {name}")


def inspect_archive(path: Path, expected_executable: str) -> None:
    found = False
    total_size = 0
    if path.name.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    name = _safe_member_name(member.filename)
                    mode = member.external_attr >> 16
                    if stat.S_ISLNK(mode):
                        raise PackageError(
                            f"archive contains symbolic link: {member.filename}"
                        )
                    total_size += member.file_size
                    if total_size > MAX_ARCHIVE_CONTENT_SIZE:
                        raise PackageError(
                            "archive expands beyond the 1 GiB safety limit"
                        )
                    if not member.is_dir():
                        _reject_installer_script(name, expected_executable)
                    if name == expected_executable and not member.is_dir():
                        found = True
        except (zipfile.BadZipFile, OSError) as error:
            raise PackageError(f"invalid ZIP archive {path.name}: {error}") from error
    elif path.name.endswith(".tar.gz"):
        try:
            with tarfile.open(path, mode="r:gz") as archive:
                for member in archive.getmembers():
                    name = _safe_member_name(member.name)
                    if (
                        member.issym()
                        or member.islnk()
                        or member.isdev()
                        or member.isfifo()
                    ):
                        raise PackageError(
                            f"archive contains unsupported link or device: {member.name}"
                        )
                    total_size += member.size
                    if total_size > MAX_ARCHIVE_CONTENT_SIZE:
                        raise PackageError(
                            "archive expands beyond the 1 GiB safety limit"
                        )
                    if member.isfile():
                        _reject_installer_script(name, expected_executable)
                    if name == expected_executable and member.isfile():
                        found = True
        except (tarfile.TarError, OSError) as error:
            raise PackageError(f"invalid tar archive {path.name}: {error}") from error
    else:
        raise PackageError(f"unsupported archive type: {path.name}")
    if not found:
        raise PackageError(
            f"archive {path.name} does not contain root executable {expected_executable!r}"
        )


class GitHubClient:
    def __init__(
        self, token: str | None = None, api_base: str = "https://api.github.com"
    ) -> None:
        self.token = token
        self.api_base = api_base.rstrip("/")

    def _request(
        self, url: str, accept: str = "application/vnd.github+json"
    ) -> urllib.request.Request:
        headers = {
            "Accept": accept,
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return urllib.request.Request(url, headers=headers)

    def get_json(self, path: str) -> Any:
        url = (
            path
            if path.startswith(("http://", "https://"))
            else f"{self.api_base}{path}"
        )
        try:
            with urllib.request.urlopen(self._request(url), timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as error:
            raise PackageError(f"GitHub request failed for {url}: {error}") from error

    def get_bytes(self, url: str, max_size: int = 4 << 20) -> bytes:
        try:
            with urllib.request.urlopen(
                self._request(url, "application/octet-stream"), timeout=60
            ) as response:
                content = response.read(max_size + 1)
        except (urllib.error.URLError, OSError) as error:
            raise PackageError(f"download failed for {url}: {error}") from error
        if len(content) > max_size:
            raise PackageError(f"download exceeds {max_size} bytes: {url}")
        return content

    def download_and_hash(self, url: str, destination: Path) -> str:
        digest = hashlib.sha256()
        downloaded = 0
        try:
            with urllib.request.urlopen(
                self._request(url, "application/octet-stream"), timeout=120
            ) as response:
                content_length = response.headers.get("Content-Length")
                if (
                    content_length is not None
                    and int(content_length) > MAX_ARCHIVE_DOWNLOAD_SIZE
                ):
                    raise PackageError(
                        f"archive exceeds the 256 MiB download limit: {url}"
                    )
                with destination.open("wb") as output:
                    while chunk := response.read(1 << 20):
                        downloaded += len(chunk)
                        if downloaded > MAX_ARCHIVE_DOWNLOAD_SIZE:
                            raise PackageError(
                                f"archive exceeds the 256 MiB download limit: {url}"
                            )
                        digest.update(chunk)
                        output.write(chunk)
        except (urllib.error.URLError, OSError, ValueError) as error:
            destination.unlink(missing_ok=True)
            raise PackageError(f"download failed for {url}: {error}") from error
        except PackageError:
            destination.unlink(missing_ok=True)
            raise
        return digest.hexdigest()


def _release_assets(release: dict[str, Any]) -> dict[str, str]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise PackageError("release assets are missing")
    result: dict[str, str] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise PackageError("release contains invalid asset metadata")
        name, url = asset.get("name"), asset.get("browser_download_url")
        if (
            not isinstance(name, str)
            or not ASSET_RE.fullmatch(name)
            or not isinstance(url, str)
        ):
            raise PackageError("release contains invalid asset name or URL")
        if name in result:
            raise PackageError(f"release contains duplicate asset: {name}")
        result[name] = url
    return result


def verify_release(
    package: Package,
    tag: str,
    version: str,
    client: GitHubClient,
    release_id: int | None = None,
) -> dict[str, Any]:
    validate_tag_version(tag, version)
    release = client.get_json(f"/repos/{package.repository}/releases/tags/{tag}")
    if not isinstance(release, dict):
        raise PackageError("GitHub returned invalid release metadata")
    if release.get("tag_name") != tag:
        raise PackageError("GitHub release tag does not match the requested tag")
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise PackageError("release must be published, non-draft, and non-prerelease")
    if release_id is not None and release.get("id") != release_id:
        raise PackageError(
            f"GitHub release ID mismatch: expected {release_id}, got {release.get('id')}"
        )
    assets = _release_assets(release)
    checksum_url = assets.get("checksums.txt")
    if checksum_url is None:
        raise PackageError("release is missing checksums.txt")
    expected_checksum_url = _release_url(package, version, "checksums.txt")
    if checksum_url != expected_checksum_url:
        raise PackageError(
            f"release has a non-canonical checksums.txt URL: {checksum_url}"
        )
    checksums = parse_checksums(client.get_bytes(checksum_url))
    selected: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix=f"{package.name}-{version}-") as directory:
        workdir = Path(directory)
        for target_name, target in package.targets.items():
            filename = target.asset(package.name, version)
            expected_hash = checksums.get(filename)
            url = assets.get(filename)
            if expected_hash is None:
                raise PackageError(
                    f"checksums.txt is missing required asset: {filename}"
                )
            if url is None:
                raise PackageError(f"release is missing required asset: {filename}")
            expected_url = _release_url(package, version, filename)
            if url != expected_url:
                raise PackageError(
                    f"release has a non-canonical asset URL for {filename}: {url}"
                )
            destination = workdir / filename
            actual_hash = client.download_and_hash(url, destination)
            if actual_hash != expected_hash:
                raise PackageError(
                    f"SHA-256 mismatch for {filename}: expected {expected_hash}, got {actual_hash}"
                )
            inspect_archive(destination, target.archive_executable)
            selected[target_name] = {
                "filename": filename,
                "url": url,
                "sha256": actual_hash,
            }
    release_url = release.get("html_url")
    expected_release_url = f"{package.homepage}/releases/tag/{tag}"
    if release_url != expected_release_url:
        raise PackageError(f"release has a non-canonical HTML URL: {release_url}")
    return {
        "package": package.name,
        "repository": package.repository,
        "tag": tag,
        "version": version,
        "release_url": release_url,
        "assets": selected,
        "release_id": release.get("id"),
    }


def _existing_version(package: Package, bucket_dir: Path = BUCKET_DIR) -> str | None:
    manifest = bucket_dir / f"{package.name}.json"
    if not manifest.exists():
        return None
    data = _read_json(manifest)
    version = data.get("version") if isinstance(data, dict) else None
    if not isinstance(version, str):
        raise PackageError(f"existing manifest has no valid version: {manifest}")
    parse_version(version)
    return version


def enforce_no_downgrade(
    package: Package, version: str, bucket_dir: Path = BUCKET_DIR
) -> None:
    current = _existing_version(package, bucket_dir)
    if current is not None and parse_version(version) < parse_version(current):
        raise PackageError(
            f"refusing downgrade for {package.name}: {current} -> {version}"
        )


def _release_url(package: Package, version: str, filename: str) -> str:
    return f"{package.homepage}/releases/download/v{version}/{filename}"


def render_scoop(package: Package, verified: dict[str, Any]) -> str:
    version = verified["version"]
    assets = verified["assets"]
    architecture: dict[str, Any] = {}
    autoupdate_architecture: dict[str, Any] = {}
    for target_name, scoop_arch in (
        ("windows_amd64", "64bit"),
        ("windows_arm64", "arm64"),
    ):
        if target_name not in package.targets:
            continue
        target = package.targets[target_name]
        asset = assets[target_name]
        architecture[scoop_arch] = {
            "url": _release_url(package, version, asset["filename"]),
            "hash": asset["sha256"],
        }
        template_filename = target.asset_template.format(
            package=package.name,
            version="$version",
            os="windows",
            arch=TARGETS[target_name][1],
            ext="zip",
        )
        autoupdate_architecture[scoop_arch] = {
            "url": f"{package.homepage}/releases/download/v$version/{template_filename}"
        }
    if not architecture:
        raise PackageError(f"{package.name} has no Windows target for Scoop")
    windows_target = package.targets.get("windows_amd64") or package.targets.get(
        "windows_arm64"
    )
    assert windows_target is not None
    archive_executable = windows_target.archive_executable
    bin_value: str | list[str] = archive_executable
    expected_public = f"{package.executable}.exe"
    if archive_executable != expected_public:
        bin_value = [archive_executable, expected_public]
    manifest = {
        "version": version,
        "description": package.description,
        "homepage": package.homepage,
        "license": package.license or "Unknown",
        "architecture": architecture,
        "bin": bin_value,
        "checkver": {"github": package.homepage},
        "autoupdate": {"architecture": autoupdate_architecture},
    }
    return json.dumps(manifest, indent=4, ensure_ascii=False) + "\n"


def _ruby_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_formula(package: Package, verified: dict[str, Any]) -> str:
    version = verified["version"]
    assets = verified["assets"]
    lines = [
        f"class {package.formula_class} < Formula",
        f"  desc {_ruby_string(package.description)}",
        f"  homepage {_ruby_string(package.homepage)}",
        f"  license {_ruby_string(package.license) if package.license else ':cannot_represent'}",
        "",
    ]
    for platform, brew_platform in (("darwin", "macos"), ("linux", "linux")):
        platform_targets = [
            (arch, f"{platform}_{arch}")
            for arch in ("arm64", "amd64")
            if f"{platform}_{arch}" in package.targets
        ]
        if not platform_targets:
            continue
        lines.append(f"  on_{brew_platform} do")
        for arch, target_name in platform_targets:
            brew_arch = "arm" if arch == "arm64" else "intel"
            asset = assets[target_name]
            lines.extend(
                [
                    f"    on_{brew_arch} do",
                    f"      url {_ruby_string(_release_url(package, version, asset['filename']))}",
                    f"      sha256 {_ruby_string(asset['sha256'])}",
                    "    end",
                ]
            )
        lines.extend(["  end", ""])
    non_windows = [
        target
        for name, target in package.targets.items()
        if not name.startswith("windows_")
    ]
    if not non_windows:
        raise PackageError(f"{package.name} has no macOS or Linux target for Homebrew")
    archive_names = {target.archive_executable for target in non_windows}
    if len(archive_names) != 1:
        raise PackageError(
            f"Homebrew targets for {package.name} must use one archive executable name"
        )
    archive_executable = next(iter(archive_names))
    install_arg = _ruby_string(archive_executable)
    if archive_executable != package.executable:
        install_arg += f" => {_ruby_string(package.executable)}"
    command = " ".join([f"#{{bin}}/{package.executable}", *package.version_args])
    lines.extend(
        [
            "  def install",
            f"    bin.install {install_arg}",
            "  end",
            "",
            "  test do",
            f"    assert_match version.to_s, shell_output({_ruby_string(command)})",
            "  end",
            "end",
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def update_package(
    package: Package,
    tag: str,
    version: str,
    client: GitHubClient,
    root: Path = ROOT,
    release_id: int | None = None,
) -> dict[str, Any]:
    bucket_dir = root / "bucket"
    enforce_no_downgrade(package, version, bucket_dir)
    verified = verify_release(package, tag, version, client, release_id)
    scoop = render_scoop(package, verified)
    formula = render_formula(package, verified)
    _atomic_write(bucket_dir / f"{package.name}.json", scoop)
    _atomic_write(root / "Formula" / f"{package.name}.rb", formula)
    return verified


def latest_stable_release(
    package: Package, client: GitHubClient
) -> tuple[str, str] | None:
    releases = client.get_json(f"/repos/{package.repository}/releases?per_page=30")
    if not isinstance(releases, list):
        raise PackageError(f"invalid releases response for {package.repository}")
    candidates: list[tuple[tuple[int, int, int], str, str]] = []
    for release in releases:
        if (
            not isinstance(release, dict)
            or release.get("draft") is not False
            or release.get("prerelease") is not False
        ):
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str) or not tag.startswith("v"):
            continue
        version = tag[1:]
        try:
            parsed = parse_version(version)
        except PackageError:
            continue
        candidates.append((parsed, tag, version))
    if not candidates:
        return None
    _, tag, version = max(candidates)
    return tag, version


def reconcile(
    client: GitHubClient,
    packages_dir: Path = PACKAGES_DIR,
    bucket_dir: Path = BUCKET_DIR,
) -> list[dict[str, str]]:
    pending: list[dict[str, str]] = []
    for package in load_packages(packages_dir):
        latest = latest_stable_release(package, client)
        if latest is None:
            continue
        tag, version = latest
        current = _existing_version(package, bucket_dir)
        if current is None or parse_version(version) > parse_version(current):
            pending.append(
                {
                    "package": package.name,
                    "repository": package.repository,
                    "tag": tag,
                    "version": version,
                }
            )
    return pending


def validate_definitions(packages_dir: Path = PACKAGES_DIR) -> list[Package]:
    packages = load_packages(packages_dir)
    if not packages:
        raise PackageError("packages/ must contain at least one package definition")
    repositories: set[str] = set()
    executables: set[str] = set()
    for package in packages:
        if package.repository.casefold() in repositories:
            raise PackageError(f"duplicate source repository: {package.repository}")
        if package.executable.casefold() in executables:
            raise PackageError(f"duplicate executable: {package.executable}")
        repositories.add(package.repository.casefold())
        executables.add(package.executable.casefold())
    return packages


def _print_error(error: Exception) -> int:
    print(f"error: {error}", file=sys.stderr)
    return 1


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser = subparsers.add_parser(
        "verify", help="verify one exact upstream release"
    )
    update_parser = subparsers.add_parser(
        "update", help="verify and render one exact upstream release"
    )
    for subparser in (verify_parser, update_parser):
        subparser.add_argument("--package", required=True)
        subparser.add_argument("--repository", required=True)
        subparser.add_argument("--tag", required=True)
        subparser.add_argument("--version", required=True)
        subparser.add_argument("--release-id", default="")
    normalize_parser = subparsers.add_parser(
        "normalize-event", help="normalize an allowlisted source release event"
    )
    normalize_parser.add_argument("--repository", required=True)
    normalize_parser.add_argument("--package", required=True)
    normalize_parser.add_argument("--tag", required=True)
    normalize_parser.add_argument("--version", required=True)
    normalize_parser.add_argument("--release-id", default="")
    normalize_parser.add_argument("--github-output", required=True, type=Path)
    subparsers.add_parser(
        "validate-definitions", help="validate every package definition"
    )
    subparsers.add_parser("reconcile", help="print pending updates as a JSON matrix")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "normalize-event":
            event = normalize_event(
                args.repository,
                args.package,
                args.tag,
                args.version,
                args.release_id,
            )
            write_github_outputs(args.github_output, event)
            print(json.dumps(event, sort_keys=True))
            return 0
        token = os.environ.get("GITHUB_TOKEN")
        client = GitHubClient(token)
        if args.command == "validate-definitions":
            packages = validate_definitions()
            print(f"validated {len(packages)} package definitions")
            return 0
        if args.command == "reconcile":
            print(json.dumps({"include": reconcile(client)}, separators=(",", ":")))
            return 0
        package = load_package(args.package)
        if args.repository != package.repository:
            raise PackageError(
                f"repository is not allowlisted for {package.name}: expected {package.repository}, got {args.repository}"
            )
        enforce_no_downgrade(package, args.version)
        if args.release_id and not re.fullmatch(r"[1-9][0-9]*", args.release_id):
            raise PackageError(f"invalid GitHub release ID: {args.release_id!r}")
        release_id = int(args.release_id) if args.release_id else None
        if args.command == "verify":
            result = verify_release(package, args.tag, args.version, client, release_id)
        else:
            result = update_package(
                package, args.tag, args.version, client, release_id=release_id
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except PackageError as error:
        return _print_error(error)


if __name__ == "__main__":
    raise SystemExit(main())
