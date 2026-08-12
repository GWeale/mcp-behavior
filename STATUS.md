# Status

Updated: 2026-08-11

## Current phase

Corrected local v0.1.0 release candidate is complete and awaiting explicit publication approval. No remote repository, package, tag, issue, or remote setting has been created.

## Completed

- Created a clean-room repository and recorded its product boundary.
- Verified the `mcp-behavior` name had no exact GitHub, PyPI, or npm match on 2026-08-08.
- Implemented strict version 1 YAML contracts and typed reports.
- Implemented expectation, baseline, and differential verification.
- Added official MCP SDK adapters for stdio and Streamable HTTP.
- Added bounded lifecycle execution and file, tree, SQLite, and custom-command observers.
- Added explicit normalization, field-level comparison, canonical evidence, semantic digests, and secret redaction.
- Added literal scenario variables, exact/JSON/text/bytes comparison, first/full difference views, quiet/verbose output, and `NO_COLOR` behavior.
- Added sanitized request and response evidence with per-case timings, hashes, diffs, verdicts, and golden fixtures.
- Added the five-command CLI, four report formats, composite GitHub Action, and five runnable example suites.
- Added public references for architecture, contracts, normalization, effects, evidence, API, CLI, compatibility, CI, security, troubleshooting, provenance, and release audit.
- Added original vector assets, community files, label catalog, eight contributor issue drafts, ranked roadmap, CI, and release automation.

## Validation

- Complete release gate: passing on 2026-08-11.
- Ruff format and lint: passing across 68 checked files.
- Strict mypy: passing across 13 source files.
- Pytest: 54 passing tests on Python 3.13.4.
- Coverage: 86.52%, above the 80% release gate.
- Dependency audit: no known third-party vulnerabilities; the unpublished local package is necessarily skipped.
- Documentation: all local links valid across 32 Markdown files.
- Provenance and secret audit: passing across 96 source files plus both distribution archives.
- Packaging: wheel and source archive built from the source archive, with metadata, contents, provenance, and checksums verified.
- Clean install: the final wheel installed and ran all five public suites with their documented exit codes.
- Compatibility: final clean-wheel checks passed on Python 3.11, 3.12, 3.13, and 3.14.
- Repeatability: the normalized nondeterminism scenario produced one semantic digest across repeated clean-wheel runs.
- Public examples: expectations and baseline return `MATCH`; value drift and wrong effect return `DIVERGE`; abrupt exit returns `INCONCLUSIVE`.
- Visual QA: README demo and 1280 x 640 social preview inspected at rendered size.
- Clean-room scan: no private-project provenance found in public source or distribution archives.

## Known risks

- v0.1.0 is an alpha. Contract, baseline, and evidence schema compatibility begins with the first published release.
- Local servers, lifecycle commands, and custom probes are trusted code. Timeouts and containment are not a hostile-code sandbox.
- The configured Linux/macOS/Windows CI matrix and composite action cannot be verified remotely until the reviewed commit is pushed.
- GitHub and package-registry name availability must be repeated immediately before creating public resources.

## Publication boundary

The remaining work changes public state and requires explicit approval:

- Create the public `GWeale/mcp-behavior` GitHub repository and push `main`.
- Wait for the complete CI matrix, then apply repository topics, social preview, labels, issues, security settings, and branch protection.
- Configure PyPI trusted publishing, tag `v0.1.0`, and publish the GitHub/PyPI release.
- Verify the public install, checksums, release assets, and composite action from a separate repository.
