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

## Upstream release contract

Each source repository must publish:

- a stable tag and release named `vMAJOR.MINOR.PATCH`;
- ZIP archives for `windows_amd64` and `windows_arm64`;
- tar.gz archives for `darwin_amd64`, `darwin_arm64`, `linux_amd64`, and `linux_arm64`;
- one root-level executable in each archive;
- `checksums.txt` with lowercase SHA-256 values for the exact uploaded archive bytes;
- immutable assets; corrections use a new patch release;
- a non-mutating command whose output contains the released version.

After release verification, the source workflow sends a `repository_dispatch` event of type `cli-release`:

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

The payload is a hint. The distribution repository accepts only checked-in package/repository pairs and derives URLs, commands, archive paths, and metadata from its definition.

## Review and verification

An update pull request must change exactly `bucket/<package>.json` and `Formula/<package>.rb`. Its body links the release and lists every independently verified archive. Separate Scoop and Homebrew workflows perform online hash checks, clean install, version verification, package-manager tests, and uninstall on each declared target.

Changes under `.github/workflows/`, `scripts/`, and `packages/` require code-owner review. Never include tokens, private keys, or personal contact details in metadata or workflow output.
