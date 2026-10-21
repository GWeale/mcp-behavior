# Status

Updated: 2026-10-20

## Current phase

The reviewed alpha is public as [`GWeale/mcp-behavior`](https://github.com/GWeale/mcp-behavior). GitHub source installation and the composite Action are supported; no package, tag, GitHub Release, or announcement is approved.

The first-run flow includes `mcp-behavior demo`, a concise README led by the invoice
example, a generated raster header, and CLI documentation. The README's
SVG logo and animated GIF have been replaced with static images.
The demo executes the checks shown in the illustration without credentials or an
existing MCP server. This is a source update, not a package or tagged release.

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
- Published the reviewed source on GitHub with a focused description, ten topics, Discussions, fourteen project labels, and eight scoped contributor issues.
- Enabled secret scanning, push protection, vulnerability alerts, automated security updates, and private vulnerability reporting.

## Validation

### Static README refresh: 2026-10-20

- Follow-up: removed the invoice diagram from the README at George's request; the main MCP Behavior header is the sole illustration. The diagram file remains archived.

- Replaced the README's vector logo and animation with an original generated PNG header and invoice illustration. Removed the GIF; retained the MP4 as an archived asset.
- Shortened the README to the problem, runnable demo, server setup, result meanings, and reference links. The exact demo output and scope limits remain visible.
- Checked both images for legible text and agreement with the intentional fixture: requested 100, `saved: true`, stored 109, and `DIVERGE`. The images are labeled as illustrations rather than execution evidence.
- Local documentation links, provenance/secret audit, and whitespace checks passed. Runtime tests were not rerun locally for this documentation-only change; required PR CI validates the merged candidate.

### Starter issue completion: 2026-10-20

- All eight starter issues have associated merged PRs; see the [completion record](docs/CONTRIBUTOR_ISSUES.md) for their acceptance criteria and links.
- Added Unicode file/tree coverage, generated binary comparisons, expected MCP error examples, and a credential-redaction-checked authenticated HTTP fixture.
- Defined the Postgres observer and controlled repeat-run designs. The extension boundary is grounded in two working external probes; these proposals do not add a generic SDK, built-in Postgres observer, or repeat-run API.
- The Docker prototype ran on Linux CI: startup 183 ms, successful verification and cleanup 1,542 ms, timeout and cleanup 6,113 ms. Both containers were confirmed removed. This remains a prototype, with the default runner unchanged.
- Consolidated dependency updates, documented their justification, and fixed a process-cleanup race exposed during cross-platform CI. Each issue PR passed the Python 3.11–3.14 matrix on Linux, macOS, and Windows before merging into the integration branch.
- The complete combined release gate passed on Windows with Python 3.12.14: 79 tests, 86.97% coverage, Ruff, strict mypy, documentation links, provenance/secret audit, and no known audited dependency vulnerabilities. Both distribution archives verified; the clean wheel passed all ten example configurations and the semantic-digest repeatability check. The separate repeat-summary design checks also passed.

### Local first-run checks: 2026-10-20

- Pytest: 55 tests passed with 86.41% coverage on Windows with Python 3.12.14, including the new real
  demo/evidence-preservation regression test. Process tests ran outside the outer
  execution sandbox because that sandbox interferes with child-process cleanup.
- Ruff formatting and lint, strict mypy, local documentation links, and the existing
  provenance/secret audit passed.
- A local wheel built successfully, installed with the frozen runtime dependency set
  into a separate environment, and passed dependency consistency checks.
- Both the installed console command and module entry point ran the demo from an
  unrelated directory with the expected call/effect verdicts and totals; the default
  run left that invoking directory unchanged.
- The README animation was visually inspected and matches the recorded fixture values.
  It is labeled as an explanatory animation of an intentional regression fixture.
- The README was shortened to a single first-run path, a minimal server example,
  concise result/workflow tables, and links to the full references. Its GIF and MP4
  are both 14 seconds; the GIF is 1080 x 675 and about 474 KB.
- No runtime dependency was added. Linux/macOS and the full release-candidate gate
  were not rerun for these local changes. No external user or audience test occurred.

### Previous release-gate record: 2026-08-11

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
- Public CI: quality, packaging, and the 12-job Python 3.11-3.14 matrix pass on Linux, macOS, and Windows.
- Public installation: isolated `pipx` and `uvx` installs from the GitHub URL expose the documented CLI.
- Public examples: all five suites pass from a fresh public clone with their documented exit codes.
- Composite Action: a separate private consumer repository passed `GWeale/mcp-behavior@main` and uploaded its evidence and JUnit report.
- Brand system: selected signal-and-endpoint identity reconstructed as light/dark SVGs, transparent raster sizes, favicon assets, and a revised social preview.

## Known risks

- v0.1.0 is an alpha. Contract, baseline, and evidence schema compatibility begins with the first published release.
- Local servers, lifecycle commands, and custom probes are trusted code. Timeouts and containment are not a hostile-code sandbox.
- Windows can occasionally delay a child MCP process long enough to produce the intentionally conservative `INCONCLUSIVE` verdict; repeated public-source runs and the full CI matrix pass.
- The revised social preview image is committed at `docs/assets/social-preview.png`; GitHub does not expose a public REST endpoint for assigning it to repository settings.

## Next actions

- Use early adopter feedback to prioritize future work and decide whether the contract and evidence formats are ready for a stable boundary. Follow the accepted designs when implementing repeat runs or a built-in Postgres observer.
- Assign `docs/assets/social-preview.png` in the GitHub repository settings when a browser session is available.
- Request separate approval before configuring PyPI, creating a tag or GitHub Release, or announcing the project.
