# New Tool Release-System Onboarding Prompt

Give the text below to an agent working in the source repository of a new CLI tool.

---

You are onboarding the current CLI repository to the centralized release and package-distribution system in `mathwro/homebrew-tools`.

## Goal

Deliver an end-to-end onboarding with minimal source-repository maintenance:

- the source repository contains one typed `release.json` and thin reusable-workflow callers;
- `mathwro/homebrew-tools/.github/workflows/release-tool.yml@main` owns tag validation, tests, toolchain setup, six native builds, smoke tests, deterministic archives, checksums, publication, and distribution notification;
- `mathwro/homebrew-tools` contains the allowlisted package definition used to generate both Scoop and Homebrew metadata;
- a prerelease tag can complete a six-platform dry run, and a stable tag can publish and update the package repository.

Do not introduce repository-specific release scripts, copied build matrices, GoReleaser, cargo-dist, custom archive code, or repository-provided shell commands. If the tool needs a new language adapter, implement that adapter once in `homebrew-tools` instead of adding an escape hatch to `release.json`.

## Authoritative central files

Inspect these files from the current `main` branch before editing:

- `mathwro/homebrew-tools/.github/workflows/release-tool.yml`
- `mathwro/homebrew-tools/.github/workflows/notify-release.yml`
- `mathwro/homebrew-tools/.github/workflows/lint-workflows.yml`
- `mathwro/homebrew-tools/scripts/source_release.py`
- `mathwro/homebrew-tools/packages/pim-manager.yml`
- `mathwro/homebrew-tools/packages/azc.yml`
- `mathwro/homebrew-tools/CONTRIBUTING.md`

Prefer an existing sibling checkout whose `origin` is `mathwro/homebrew-tools`. If none is available, obtain a separate checkout. Keep source-repository and central-repository changes clearly separated. If central-repository access is impossible, finish every source change and provide the exact pending `packages/<package>.yml` content, but report onboarding as blocked rather than complete.

## Step 1: Discover the source contract

Inspect the repository instead of asking for values available from code or Git:

1. Derive `OWNER/REPOSITORY` from the `origin` remote.
2. Choose one stable lowercase hyphenated package name matching `^[a-z0-9]+(-[a-z0-9]+)*$`.
3. Identify the installed executable name. Windows archives use the same name with `.exe`.
4. Identify the language, project root, build manifest, license SPDX identifier, description, and non-mutating version/help arguments.
5. Run the current tests and the executable's version/help paths.
6. Confirm that `--version` succeeds without authentication, network access, configuration, or interactive input and that its output contains the release version.
7. Search existing workflows, release scripts, package metadata, and documentation. Plan a clean cutover rather than a second release path.

Completion criterion: every value required by `release.json` and `packages/<package>.yml` is grounded in the repository, and any version-output defect is identified before workflow changes.

## Step 2: Make the CLI satisfy the runtime contract

The generated archives contain exactly one root-level executable. The executable must:

- run on its declared native target;
- support the configured version arguments, normally `--version`;
- include the exact tag version without the leading `v` in its output;
- support the configured help arguments, normally `--help`;
- perform neither mutation nor authentication for either command.

For Go, expose linkable package-level string variables when normal `go build` cannot otherwise report the tagged version. The central adapter can populate `version`, `commit`, and `date` symbols through `-ldflags -X`. These must be variables, not constants, and the config must use their full Go import paths.

For Rust, the tag version must equal `[package].version` in `Cargo.toml`. The central adapter sets `RELEASE_COMMIT` and `SOURCE_DATE_EPOCH`. A `build.rs` may consume them for provenance while the executable uses `CARGO_PKG_VERSION` for the release version. If the Cargo package name, manifest, or features differ from defaults, express them through typed Rust options in `release.json`.

Add or update behavior tests only where the version/help contract is not already defended.

Completion criterion: a local release-style build reports the intended version and help without side effects.

## Step 3: Add `release.json`

Use schema version 1. Keep this file declarative and small.

### Go

```json
{
  "schema": 1,
  "package": "PACKAGE",
  "binary": "BINARY",
  "adapter": "go",
  "macos_sign": "none",
  "go": {
    "ldflags": {
      "version": "FULL/GO/IMPORT/PATH.versionVariable",
      "commit": "FULL/GO/IMPORT/PATH.commitVariable",
      "date": "FULL/GO/IMPORT/PATH.dateVariable"
    }
  }
}
```

Rules:

- Set `macos_sign` to `adhoc` only when ad-hoc signing is intentionally required.
- `go.main` defaults to `.`.
- `go.module_file` defaults to `go.mod`.
- `version` linker metadata is required when the ordinary binary would otherwise report a development version.
- Omit unused optional linker symbols instead of inventing variables.

### Rust

```json
{
  "schema": 1,
  "package": "PACKAGE",
  "binary": "BINARY",
  "adapter": "rust"
}
```

Optional typed Rust settings:

```json
{
  "rust": {
    "package": "CARGO_PACKAGE",
    "manifest": "Cargo.toml",
    "features": ["FEATURE"]
  }
}
```

Common optional settings are `project_path`, `release_branch`, `version_args`, `help_args`, and `macos_sign`. Use them only when repository evidence requires a non-default value. Unknown fields fail closed.

### Unsupported language

If `adapter` is neither `go` nor `rust`, update `homebrew-tools/scripts/source_release.py`, `release-tool.yml`, and central tests with a typed adapter. Preserve these invariants:

- the config selects capabilities, never a raw command;
- tests and builds use locked/reproducible dependency inputs supported by the language;
- all six target tokens are either genuinely built and natively smoke-tested or the adapter fails closed;
- archives are produced by the central deterministic writers;
- the central stage performs exact asset and checksum verification.

Completion criterion: `source_release.load_config()` accepts the config, rejects misspelled/unknown fields, and exposes no arbitrary command input.

## Step 4: Replace the source release workflow

Create or replace `.github/workflows/release.yml` with this caller. Preserve the expressions exactly unless the central workflow contract has changed on `main`:

```yaml
name: Release

on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      tag:
        description: Existing annotated tag to build
        required: true
        type: string
      dry_run:
        description: Build and validate without publishing
        required: true
        default: true
        type: boolean

permissions:
  contents: read

jobs:
  release:
    permissions:
      contents: write
    uses: mathwro/homebrew-tools/.github/workflows/release-tool.yml@main
    with:
      tag: ${{ github.event_name == 'workflow_dispatch' && inputs.tag || github.ref_name }}
      dry_run: ${{ github.event_name == 'workflow_dispatch' && inputs.dry_run || (github.event_name == 'push' && contains(github.ref_name, '-')) }}
    secrets:
      distribution_token: ${{ secrets.DISTRIBUTION_DISPATCH_TOKEN }}
```

This makes pushed prerelease tags automatic dry runs. Pushed stable tags build and wait for the protected `release` environment before publication.

Remove superseded release/publish workflows and local build, archive, checksum, or dispatch scripts after all callers and documentation use the shared workflow. Remove CI references to deleted release helpers. Retain ordinary source CI.

Completion criterion: exactly one release entry point remains and it calls `release-tool.yml@main`.

## Step 5: Add shared workflow linting

Create or replace `.github/workflows/actionlint.yml`:

```yaml
name: Workflow Lint

on:
  pull_request:
    paths:
      - '.github/workflows/**'
  push:
    branches: [main]
    paths:
      - '.github/workflows/**'

permissions:
  contents: read

concurrency:
  group: workflow-lint-${{ github.ref }}
  cancel-in-progress: true

jobs:
  actionlint:
    uses: mathwro/homebrew-tools/.github/workflows/lint-workflows.yml@main
```

Remove local actionlint download/install logic and runner-label configuration made obsolete by the thin caller.

Completion criterion: workflow linting has one shared implementation and the source repository contains no actionlint installer.

## Step 6: Add the central package definition

In `mathwro/homebrew-tools`, create `packages/PACKAGE.yml`. Despite the extension, the file uses strict JSON syntax:

```json
{
  "package": "PACKAGE",
  "repository": "OWNER/REPOSITORY",
  "description": "ONE-LINE DESCRIPTION",
  "license": "SPDX-LICENSE",
  "executable": "BINARY",
  "version_command": [
    "--version"
  ],
  "targets": {
    "windows_amd64": {
      "asset": "{package}_{version}_windows_amd64.zip",
      "archive_executable": "BINARY.exe"
    },
    "windows_arm64": {
      "asset": "{package}_{version}_windows_arm64.zip",
      "archive_executable": "BINARY.exe"
    },
    "darwin_amd64": {
      "asset": "{package}_{version}_darwin_amd64.tar.gz",
      "archive_executable": "BINARY"
    },
    "darwin_arm64": {
      "asset": "{package}_{version}_darwin_arm64.tar.gz",
      "archive_executable": "BINARY"
    },
    "linux_amd64": {
      "asset": "{package}_{version}_linux_amd64.tar.gz",
      "archive_executable": "BINARY"
    },
    "linux_arm64": {
      "asset": "{package}_{version}_linux_arm64.tar.gz",
      "archive_executable": "BINARY"
    }
  }
}
```

Keep repository-owned metadata here. Generated `bucket/PACKAGE.json` and `Formula/PACKAGE.rb` must not be hand-written before a real stable release exists; the central updater generates both from verified release assets.

Add the tool to the availability table in `homebrew-tools/README.md` as pending release. Update source-repository installation/release documentation to explain the central workflow, protected environment, token, prerelease dry run, immutable stable release, Scoop command, and Homebrew command.

Completion criterion: the source `release.json` and central package definition agree on package, binary, version command, and all six archive names.

## Step 7: Validate locally

Run all existing source tests and format/static checks. Then run the central driver from the source repository using the real path to the `homebrew-tools` checkout.

Validate the adapter tests:

```sh
python3 PATH_TO_HOMEBREW_TOOLS/scripts/source_release.py \
  --config release.json \
  test
```

Build and smoke the current native target. Use a SemVer matching the tool's actual version-output contract; for Rust it must match `Cargo.toml`:

```sh
python3 PATH_TO_HOMEBREW_TOOLS/scripts/source_release.py \
  --config release.json \
  build \
  --tag vX.Y.Z \
  --commit "$(git rev-parse HEAD)" \
  --epoch "$(git show -s --format=%ct HEAD)" \
  --target HOST_TARGET \
  --output "$TMPDIR/source-release-smoke"
```

`HOST_TARGET` is one of `windows_amd64`, `windows_arm64`, `darwin_amd64`, `darwin_arm64`, `linux_amd64`, or `linux_arm64` and must match the machine because the driver executes the built binary.

Validate the central repository:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/package_repository.py validate-definitions
python3 scripts/validate_metadata.py repository
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7
```

Validate source workflows with actionlint as well. Do not claim six-platform runtime coverage from the local host build; that proof comes from the GitHub dry-run matrix.

Completion criterion: source checks pass, central checks pass, the host archive is deterministic/root-only, and the built executable reports the requested version.

## Step 8: Verify repository settings and deployment order

Inspect GitHub settings with `gh` where access permits. Never print or request secret values.

Required source-repository settings:

- protected `main` with ordinary CI and `Workflow Lint` required;
- protected `release` environment with required reviewer approval;
- repository secret `DISTRIBUTION_DISPATCH_TOKEN`, containing a fine-grained token restricted to `mathwro/homebrew-tools` with permission to create repository dispatch events.

If the environment or secret is absent and cannot be configured through current credentials, report the exact missing setting and the command/UI action required. Do not weaken the workflow to bypass it.

Deploy in this order:

1. Merge any new central adapter and package-definition changes into `homebrew-tools`.
2. Merge the source-repository onboarding.
3. Push an annotated prerelease tag and require all six dry-run target jobs plus staging to pass.
4. For Rust, restore/set the intended stable `Cargo.toml` version before the stable tag.
5. Push an annotated stable tag from protected `main`.
6. Approve the `release` environment only after reviewing the completed build artifacts.
7. Confirm the published release contains six archives plus `checksums.txt`.
8. Confirm the canonical `cli-release` dispatch creates one `homebrew-tools` update PR containing only `bucket/PACKAGE.json` and `Formula/PACKAGE.rb`.
9. Confirm separate Scoop and Homebrew checks pass and a repeated update is a no-op.

## Acceptance criteria

Do not report onboarding complete until every applicable statement is true:

- source release maintenance is limited to `release.json`, the thin release caller, and ordinary application version code;
- no obsolete or parallel release implementation remains;
- package/binary/version metadata agree across source code, `release.json`, and `packages/PACKAGE.yml`;
- central and source tests, formatting, static checks, and actionlint pass;
- the central adapter builds, executes, packages, and inspects the host target locally;
- a GitHub prerelease dry run passes every declared native target without publishing;
- the protected stable path publishes six immutable archives and `checksums.txt`;
- notification produces one deterministic Scoop/Homebrew update PR;
- missing credentials, environments, hosted runners, or central access are reported as explicit blockers, never silently skipped.

Final response format:

1. Source-repository changes, with exact files.
2. `homebrew-tools` changes, with exact files.
3. Removed obsolete release paths.
4. Verification commands and observed results.
5. GitHub settings verified or still required.
6. Dry-run/stable-release evidence, clearly separating local proof from GitHub-hosted proof.

---
