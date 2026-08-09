# Status

Updated: 2026-08-08

## Current phase

Local v0.1.0 release candidate is complete and awaiting explicit publication approval. No remote repository or package has been created.

## Completed

- Created a clean-room repository and recorded its product boundary.
- Verified the `mcp-behavior` name had no exact GitHub, PyPI, or npm match on 2026-08-08.
- Implemented strict version 1 YAML contracts and typed reports.
- Implemented expectation, baseline, and differential verification.
- Added official MCP SDK adapters for stdio and Streamable HTTP.
- Added bounded lifecycle execution and file, tree, SQLite, and custom-command observers.
- Added explicit normalization, field-level comparison, canonical evidence, semantic digests, and secret redaction.
- Added the five-command CLI, four report formats, composite GitHub Action, and three runnable examples.
- Added public documentation, original vector assets, community files, CI, and release automation.

## Validation

- Complete release gate: passing on 2026-08-08.
- Ruff format and lint: passing across 49 checked files.
- Strict mypy: passing across 13 source files.
- Pytest: 33 passing tests on Python 3.13.4.
- Coverage: 85.83%, above the 80% release gate.
- Dependency audit: no known third-party vulnerabilities; the unpublished local package is necessarily skipped.
- Documentation: all local links valid across 21 Markdown files.
- Packaging: wheel and source archive built from the source archive, with metadata, contents, provenance, and checksums verified.
- Clean install: the final wheel installed and ran the expectations example on Python 3.11.14 with the expected semantic digest.
- Compatibility: clean-wheel checks also passed on Python 3.12.12 and 3.13.4 during the release-candidate audit.
- Public examples: expectations and baseline return `MATCH`; differential returns `DIVERGE` with exit code 1.
- Visual QA: README demo and 1280 x 640 social preview inspected at rendered size.
- Clean-room scan: no private-project provenance found in public source or distribution archives.

## Publication boundary

The remaining work changes public state and requires explicit approval:

- Create the public `GWeale/mcp-behavior` GitHub repository and push `main`.
- Apply repository topics, social preview, security settings, and branch protection.
- Configure PyPI trusted publishing, tag `v0.1.0`, and publish the GitHub/PyPI release.
- Verify the public install, checksums, release assets, and composite action from a separate repository.
