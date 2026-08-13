# Contributing

## Package metadata changes

Do not edit `bucket/*.json` or `Formula/*.rb` independently. Both files are deterministic outputs from one definition in `packages/*.yml` and one verified upstream release.

A package definition contains only repository-owned metadata: stable package identity, source repository, description, license, executable, non-mutating version arguments, asset naming, and supported targets. Definitions use JSON syntax despite the `.yml` extension so Python can parse them without a third-party dependency.

To validate definitions and repository consistency:

```sh
python3 scripts/package_repository.py validate-definitions
python3 scripts/validate_metadata.py repository
python3 -m unittest discover -s tests -v
```

To verify and render a published release:

```sh
scripts/update-package \
  --package azc \
  --repository mathwro/azc \
  --tag v1.2.3 \
  --version 1.2.3
```

The updater requires a published, non-draft, non-prerelease release with `checksums.txt` and every archive declared by the package definition. It downloads every selected archive, independently computes SHA-256, rejects unsafe archive members, and then writes both generated files. Repeating the command for the same immutable release must produce no diff.

## Onboard a source repository

For agent-driven onboarding, give [`ONBOARDING_AGENT_PROMPT.md`](ONBOARDING_AGENT_PROMPT.md) to an agent working in the new tool's source repository. It covers Go/Rust branches, adding a central language adapter, repository settings, validation, deployment order, and completion criteria.

For a supported language, onboarding is data rather than a copied release implementation:

1. Add the allowlisted distribution definition under `packages/<package>.yml`.
2. Add a schema-1 `release.json` to the source repository. Select the `go` or `rust` adapter, the stable package and binary names, and only typed adapter options. Go tools may map version, commit, and date linker symbols; Rust tools use `Cargo.toml` as the release version source.
3. Copy the thin `Release` caller shown in `README.md`. Do not copy build, archive, checksum, publication, or dispatch steps.
4. Create the protected `release` environment and the `DISTRIBUTION_DISPATCH_TOKEN` repository secret.
5. Merge central adapter changes before the caller, then exercise an annotated tag through `workflow_dispatch` with `dry_run: true`.
6. Push an annotated stable tag only after the dry run passes all six native target jobs.

`scripts/source_release.py` is the typed adapter boundary. It rejects unknown configuration fields, path traversal, mixed adapters, and arbitrary build commands. A new language is implemented and tested once in that driver and `.github/workflows/release-tool.yml`; individual tools never carry language-specific release scripts.

## Upstream release contract

Each source repository must publish:

- a stable tag and release named `vMAJOR.MINOR.PATCH`;
- ZIP archives for `windows_amd64` and `windows_arm64`;
- tar.gz archives for `darwin_amd64`, `darwin_arm64`, `linux_amd64`, and `linux_arm64`;
- one root-level executable in each archive;
- `checksums.txt` with lowercase SHA-256 values for the exact uploaded archive bytes;
- immutable assets; corrections use a new patch release;
- a non-mutating command whose output contains the released version.

After release verification, `.github/workflows/release-tool.yml` calls `.github/workflows/notify-release.yml`. The notifier verifies the exact published stable release and sends this canonical `repository_dispatch` event:

```json
{
  "event_type": "cli-release",
  "client_payload": {
    "repository": "mathwro/azc",
    "package": "azc",
    "tag": "v1.2.3",
    "version": "1.2.3"
  }
}
```

Source repositories normally call `mathwro/homebrew-tools/.github/workflows/release-tool.yml@main`; direct use of `notify-release.yml` is reserved for sources with an independently reviewed publisher. Each caller stores the same `DISTRIBUTION_DISPATCH_TOKEN` repository secret: a fine-grained token restricted to this repository with permission to send repository dispatches. Scheduled reconciliation remains the credential-independent safety net.

Source repositories call `.github/workflows/lint-workflows.yml` to run the centrally pinned `actionlint` version. Merge shared-workflow changes here before updating callers because an external reusable-workflow reference resolves from the named remote ref.

Every payload is a hint. The distribution repository accepts only checked-in package/repository pairs and derives URLs, commands, archive paths, and metadata from its definition.

## Review and verification

An update pull request must change exactly `bucket/<package>.json` and `Formula/<package>.rb`. Its body links the release and lists every independently verified archive. Separate Scoop and Homebrew workflows perform online hash checks, clean install, version verification, package-manager tests, and uninstall on each declared target.

Changes under `.github/workflows/`, `scripts/`, and `packages/` require code-owner review. Never include tokens, private keys, or personal contact details in metadata or workflow output.
