# Homebrew Tools

Unified Scoop bucket and Homebrew tap for command-line tools published by [mathwro](https://github.com/mathwro). This repository distributes immutable prebuilt release archives; each tool remains built and released from its own source repository.

## Availability

Package metadata is generated only after an upstream stable `vMAJOR.MINOR.PATCH` GitHub Release supplies all six required archives and `checksums.txt` and passes independent download, checksum, and archive-safety verification.

| Tool | Description | Source | License | Windows | macOS | Linux |
|---|---|---|---|---|---|---|
| `azc` | Fast subscription context switcher for Azure CLI | [mathwro/azc](https://github.com/mathwro/azc) | MIT | AMD64, ARM64 | Intel, Apple Silicon | AMD64, ARM64 |
| `pim-manager` | TUI for activating Microsoft PIM assignments | [mathwro/pim-manager](https://github.com/mathwro/pim-manager) | MIT | AMD64, ARM64 | Intel, Apple Silicon | AMD64, ARM64 |
| `nwcli` | Network CLI Toolbox | [mathwro/nwcli](https://github.com/mathwro/nwcli) | Upstream has no declared license | AMD64, ARM64 pending release | Intel, Apple Silicon pending release | AMD64, ARM64 pending release |

The hosted CI matrix performs real installs on Windows AMD64/ARM64, macOS Intel/ARM64, and Linux AMD64/ARM64 after metadata exists. A missing runner or failed target blocks its matrix check and therefore blocks automatic merge; syntax-only checks never count as install coverage.

## Shared source workflows

Source repositories contain only a typed `release.json` and a thin caller workflow. `.github/workflows/release-tool.yml` owns tag validation, Go/Rust toolchain setup, tests, six native builds, version/help smoke tests, deterministic archives, checksums, environment-gated publication, and package notification.

```yaml
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

The typed adapters deliberately do not accept repository-provided shell commands. Supported Go or Rust tools onboard through configuration only; supporting another language means adding and testing one adapter here, after which tools using that language need no workflow redesign. `.github/workflows/lint-workflows.yml` centralizes workflow linting, and `.github/workflows/notify-release.yml` is the separately reusable canonical handoff.

The caller needs one repository secret, `DISTRIBUTION_DISPATCH_TOKEN`, containing a fine-grained token restricted to this repository with permission to send repository dispatches. Merge shared-workflow and adapter changes here before updating consumer references to `@main`.

## Scoop

After the selected tool is listed as available above:

```powershell
scoop bucket add mathwro https://github.com/mathwro/homebrew-tools
scoop install mathwro/azc
scoop update azc
```

Replace `azc` with `pim-manager` or `nwcli`.

## Homebrew

Homebrew requires explicit trust for third-party formulae. After the selected tool is listed as available above:

```sh
brew tap mathwro/tools
brew install mathwro/tools/azc
brew upgrade mathwro/tools/azc
```

Replace `azc` with `pim-manager` or `nwcli`. Fully qualified formula names avoid granting trust to the entire tap.

## Troubleshooting

- A package is not found: confirm its table row no longer says `pending release`, then update the bucket or tap.
- A URL or hash fails: open an issue here and include the package name, version, operating system, architecture, and package-manager output.
- The installed command fails or behaves incorrectly: report it in the tool's source repository.
- Scoop metadata/install behavior or Homebrew formula behavior is a packaging issue and belongs in this repository.
- `azc` also requires Azure CLI and an authenticated `az login` session for normal use; its version command does not require authentication.

Release assets are immutable. A broken upstream artifact is corrected with a new patch release, never by replacing an existing asset.
