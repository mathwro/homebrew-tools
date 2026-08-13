# Security Policy

## Reporting a vulnerability

Report vulnerabilities privately through [GitHub private vulnerability reporting](https://github.com/mathwro/homebrew-tools/security/advisories/new). Do not open a public issue for a suspected supply-chain vulnerability.

Include the affected package and version, operating system and architecture, package manager, observed behavior, and reproduction steps. Do not include credentials, access tokens, or unrelated personal data.

## Supply-chain guarantees

Distribution automation treats dispatch payloads, GitHub release metadata, checksums, filenames, and archives as untrusted input. It accepts only checked-in repository/package pairs, requires stable SemVer, independently downloads each required asset, computes SHA-256 over the exact archive bytes, compares it with `checksums.txt`, and inspects archive members before generation or execution.

Published release assets are immutable. Corrections require a new patch version and release. Pull requests preserve the release URL and verified asset hashes for audit.
