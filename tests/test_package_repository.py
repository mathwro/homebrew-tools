from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from package_repository import (
    Package,
    PackageError,
    Target,
    enforce_no_downgrade,
    inspect_archive,
    load_package,
    normalize_event,
    parse_checksums,
    parse_version,
    reconcile,
    render_formula,
    render_scoop,
    update_package,
    validate_definitions,
    verify_release,
)


class FakeClient:
    def __init__(self, release: dict[str, Any], content: dict[str, bytes]) -> None:
        self.release = release
        self.content = content

    def get_json(self, path: str) -> Any:
        return self.release

    def get_bytes(self, url: str, max_size: int = 4 << 20) -> bytes:
        return self.content[url]

    def download_and_hash(self, url: str, destination: Path) -> str:
        payload = self.content[url]
        destination.write_bytes(payload)
        return hashlib.sha256(payload).hexdigest()


def zip_bytes(executable: str, extra: tuple[str, bytes] | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(executable, b"binary")
        if extra:
            archive.writestr(*extra)
    return output.getvalue()


def tar_bytes(executable: str, extra: tuple[str, bytes] | None = None) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        entries = [(executable, b"binary")]
        if extra:
            entries.append(extra)
        for name, payload in entries:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return output.getvalue()


def test_package() -> Package:
    targets: dict[str, Target] = {}
    for name in (
        "windows_amd64",
        "windows_arm64",
        "darwin_amd64",
        "darwin_arm64",
        "linux_amd64",
        "linux_arm64",
    ):
        os_name, arch = name.split("_")
        extension = "zip" if os_name == "windows" else "tar.gz"
        executable = "tool.exe" if os_name == "windows" else "tool"
        targets[name] = Target(
            name, f"tool_{{version}}_{os_name}_{arch}.{extension}", executable
        )
    return Package(
        "tool", "owner/tool", "Useful test tool", "MIT", "tool", ("--version",), targets
    )


def valid_release(
    package: Package, version: str = "1.2.3"
) -> tuple[dict[str, Any], dict[str, bytes]]:
    assets: list[dict[str, str]] = []
    content: dict[str, bytes] = {}
    checksums: list[str] = []
    for name, target in package.targets.items():
        filename = target.asset(package.name, version)
        payload = (
            zip_bytes(target.archive_executable)
            if name.startswith("windows_")
            else tar_bytes(target.archive_executable)
        )
        url = f"{package.homepage}/releases/download/v{version}/{filename}"
        assets.append({"name": filename, "browser_download_url": url})
        content[url] = payload
        checksums.append(f"{hashlib.sha256(payload).hexdigest()}  {filename}")
    checksum_url = f"{package.homepage}/releases/download/v{version}/checksums.txt"
    assets.append({"name": "checksums.txt", "browser_download_url": checksum_url})
    content[checksum_url] = ("\n".join(checksums) + "\n").encode()
    release = {
        "id": 123,
        "tag_name": f"v{version}",
        "draft": False,
        "prerelease": False,
        "html_url": f"https://github.com/owner/tool/releases/tag/v{version}",
        "assets": assets,
    }
    return release, content


class PackageRepositoryTests(unittest.TestCase):
    def test_checked_in_definitions_are_valid_and_collision_free(self) -> None:
        packages = validate_definitions()
        self.assertEqual(
            [package.name for package in packages], ["azc", "nwcli", "pim-manager"]
        )

    def test_stable_semver_is_strict(self) -> None:
        self.assertEqual(parse_version("1.2.3"), (1, 2, 3))
        for value in ("v1.2.3", "1.2", "01.2.3", "1.2.3-rc.1", "1.2.3+build"):
            with self.subTest(value=value), self.assertRaises(PackageError):
                parse_version(value)

    def test_checksums_require_lowercase_sha_and_unique_safe_filenames(self) -> None:
        digest = "a" * 64
        self.assertEqual(
            parse_checksums(f"{digest}  tool.zip\n".encode()), {"tool.zip": digest}
        )
        invalid = (
            f"{'A' * 64}  tool.zip\n",
            f"{digest}  ../tool.zip\n",
            f"{digest}  tool.zip\n{digest}  tool.zip\n",
        )
        for content in invalid:
            with self.subTest(content=content), self.assertRaises(PackageError):
                parse_checksums(content.encode())

    def test_valid_release_is_downloaded_hashed_and_inspected(self) -> None:
        package = test_package()
        release, content = valid_release(package)
        verified = verify_release(
            package, "v1.2.3", "1.2.3", FakeClient(release, content)
        )  # type: ignore[arg-type]
        self.assertEqual(set(verified["assets"]), set(package.targets))
        self.assertIn('"version": "1.2.3"', render_scoop(package, verified))
        self.assertIn("class Tool < Formula", render_formula(package, verified))
        self.assertNotIn('  version "1.2.3"', render_formula(package, verified))

    def test_release_id_must_match_exact_release(self) -> None:
        package = test_package()
        release, content = valid_release(package)
        with self.assertRaisesRegex(PackageError, "release ID mismatch"):
            verify_release(
                package,
                "v1.2.3",
                "1.2.3",
                FakeClient(release, content),  # type: ignore[arg-type]
                release_id=456,
            )

    def test_draft_and_prerelease_fail_closed(self) -> None:
        package = test_package()
        for field in ("draft", "prerelease"):
            release, content = valid_release(package)
            release[field] = True
            with self.subTest(field=field), self.assertRaises(PackageError):
                verify_release(package, "v1.2.3", "1.2.3", FakeClient(release, content))  # type: ignore[arg-type]

    def test_noncanonical_release_url_fails_closed(self) -> None:
        package = test_package()
        release, content = valid_release(package)
        release["assets"][0]["browser_download_url"] = (
            "https://attacker.invalid/tool.zip"
        )
        with self.assertRaisesRegex(PackageError, "non-canonical asset URL"):
            verify_release(package, "v1.2.3", "1.2.3", FakeClient(release, content))  # type: ignore[arg-type]

    def test_tag_mismatch_fails_before_network(self) -> None:
        package = test_package()
        release, content = valid_release(package)
        with self.assertRaises(PackageError):
            verify_release(package, "v1.2.4", "1.2.3", FakeClient(release, content))  # type: ignore[arg-type]

    def test_missing_asset_fails_closed(self) -> None:
        package = test_package()
        release, content = valid_release(package)
        missing = package.targets["linux_arm64"].asset(package.name, "1.2.3")
        release["assets"] = [
            asset for asset in release["assets"] if asset["name"] != missing
        ]
        with self.assertRaisesRegex(PackageError, "release is missing required asset"):
            verify_release(package, "v1.2.3", "1.2.3", FakeClient(release, content))  # type: ignore[arg-type]

    def test_checksum_mismatch_fails_closed(self) -> None:
        package = test_package()
        release, content = valid_release(package)
        filename = package.targets["windows_amd64"].asset(package.name, "1.2.3")
        content[f"{package.homepage}/releases/download/v1.2.3/{filename}"] += (
            b"tampered"
        )
        with self.assertRaisesRegex(PackageError, "SHA-256 mismatch"):
            verify_release(package, "v1.2.3", "1.2.3", FakeClient(release, content))  # type: ignore[arg-type]

    def test_archive_rejects_traversal_and_installer_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            traversal = Path(directory) / "tool.zip"
            traversal.write_bytes(zip_bytes("tool.exe", ("../escape", b"bad")))
            with self.assertRaisesRegex(PackageError, "parent traversal"):
                inspect_archive(traversal, "tool.exe")
            script = Path(directory) / "tool.tar.gz"
            script.write_bytes(tar_bytes("tool", ("install.sh", b"bad")))
            with self.assertRaisesRegex(PackageError, "installer script"):
                inspect_archive(script, "tool")

    def test_downgrade_is_rejected_and_same_version_is_idempotent(self) -> None:
        package = test_package()
        with tempfile.TemporaryDirectory() as directory:
            bucket = Path(directory)
            (bucket / "tool.json").write_text('{"version":"2.0.0"}', encoding="utf-8")
            enforce_no_downgrade(package, "2.0.0", bucket)
            with self.assertRaisesRegex(PackageError, "refusing downgrade"):
                enforce_no_downgrade(package, "1.9.9", bucket)

    def test_unknown_package_fails_closed(self) -> None:
        with self.assertRaises(PackageError):
            load_package("unknown-package")

    def test_normalizes_canonical_dispatch_contract(self) -> None:
        self.assertEqual(
            normalize_event(
                "mathwro/azc",
                "azc",
                "v1.2.3",
                "1.2.3",
                "123",
            ),
            {
                "repository": "mathwro/azc",
                "package": "azc",
                "tag": "v1.2.3",
                "version": "1.2.3",
                "release_id": "123",
            },
        )

    def test_event_normalization_rejects_conflicting_untrusted_fields(self) -> None:
        invalid_events = (
            ("azc", "azc", "v1.2.3", "1.2.3", ""),
            ("mathwro/azc", "pim-manager", "v1.2.3", "1.2.3", ""),
            ("mathwro/azc", "azc", "v1.2.3", "1.2.4", ""),
            ("mathwro/azc", "azc", "v1.2.3", "1.2.3", "not-an-id"),
            ("mathwro/azc", "azc", "v1.2.3", "", ""),
        )
        for event in invalid_events:
            with self.subTest(event=event), self.assertRaises(PackageError):
                normalize_event(*event)

    def test_rendering_the_same_release_is_byte_identical(self) -> None:
        package = test_package()
        release, content = valid_release(package)
        client = FakeClient(release, content)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            update_package(package, "v1.2.3", "1.2.3", client, root)  # type: ignore[arg-type]
            first = (
                (root / "bucket/tool.json").read_bytes(),
                (root / "Formula/tool.rb").read_bytes(),
            )
            update_package(package, "v1.2.3", "1.2.3", client, root)  # type: ignore[arg-type]
            second = (
                (root / "bucket/tool.json").read_bytes(),
                (root / "Formula/tool.rb").read_bytes(),
            )
            self.assertEqual(first, second)

    def test_reconciliation_detects_a_missed_stable_release(self) -> None:
        package = test_package()
        definition = {
            "package": package.name,
            "repository": package.repository,
            "description": package.description,
            "license": package.license,
            "executable": package.executable,
            "version_command": list(package.version_args),
            "targets": {
                name: {
                    "asset": target.asset_template,
                    "archive_executable": target.archive_executable,
                }
                for name, target in package.targets.items()
            },
        }

        class ReleasesClient:
            def get_json(self, path: str) -> Any:
                return [
                    {"tag_name": "v1.2.3", "draft": False, "prerelease": False},
                    {"tag_name": "v2.0.0-rc.1", "draft": False, "prerelease": True},
                ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packages = root / "packages"
            bucket = root / "bucket"
            packages.mkdir()
            bucket.mkdir()
            (packages / "tool.yml").write_text(json.dumps(definition), encoding="utf-8")
            self.assertEqual(
                reconcile(ReleasesClient(), packages, bucket),  # type: ignore[arg-type]
                [
                    {
                        "package": "tool",
                        "repository": "owner/tool",
                        "tag": "v1.2.3",
                        "version": "1.2.3",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
