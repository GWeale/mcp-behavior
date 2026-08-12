# v0.1.0 release audit

Audit date: 2026-08-11

This ledger maps the v0.1.0 release requirements to code, public artifacts, and executable checks. Public publication remains a separate approval step.

## Final local gate

- Complete gate passed on 2026-08-11.
- 54 tests passed with 86.52% coverage.
- Ruff formatting/lint and strict mypy passed.
- All links across 32 Markdown files passed.
- The source audit checked 96 files; the distribution verifier checked the wheel and source archive.
- `pip-audit` found no known third-party dependency vulnerabilities. The unpublished local package itself is necessarily skipped.
- The final wheel passed all five example suites and the repeatability check on Python 3.11, 3.12, 3.13, and 3.14 in fresh environments.

## Product boundary and provenance

| Requirement | Evidence |
|---|---|
| Available, distinct name | Exact GitHub, PyPI, and npm check recorded in [PROVENANCE.md](PROVENANCE.md); repeat required immediately before publication |
| Clean-room implementation | Dated manual record plus automated source/archive scans in `scripts/audit_release.py` and `scripts/verify_dist.py` |
| Non-overlapping product boundary | [POSITIONING.md](POSITIONING.md) covers Inspector, conformance, MCP Contracts, and MCP Lock |
| Minimal justified dependencies | Three runtime dependencies with purpose, range, and license in [DEPENDENCIES.md](DEPENDENCIES.md) and [PROVENANCE.md](PROVENANCE.md) |
| Deep public interface | `verify(...)`, `verify_async(...)`, typed reports, and target overrides documented in [API.md](API.md); boundaries recorded in ADR 0002 |

## Runtime behavior

| Area | Implemented behavior | Direct evidence |
|---|---|---|
| Targets | stdio and Streamable HTTP through the official SDK; literal-free credential references; redirects disabled | `targets.py`, contract tests, stdio/HTTP integration tests, redirect-containment test |
| Time budgets | connection, operation, and total-run bounds | parameterized public-API integration test for all three budgets |
| Cleanup | setup/cleanup lifecycle, command process-tree kill, official-SDK server tree shutdown | cleanup-after-failure and descendant-process tests; SDK boundary documented in security model |
| Scenarios | ordered setup, calls, observers, assertions, cleanup; exact name/tag selection | contract compiler plus selection, lifecycle, and effect integration tests |
| Variables | typed literal `${name}` substitution with no environment lookup and sensitive-name rejection | contract substitution and secret-boundary tests |
| Modes | expectations, reviewed baseline, live differential | public examples and core integration tests |
| Verdicts | `MATCH`, `DIVERGE`, `INCONCLUSIVE`; exits 0, 1, 2 | model tests plus clean-wheel examples with expected nonzero exits |

## Comparison, normalization, and effects

| Requirement | Evidence |
|---|---|
| Exact, JSON, text, and bytes | comparator unit tests cover root exactness, line regions, first changed byte, and structural JSON |
| Inclusion, exclusion, and equality | recursive `contains`, `paths_absent`, and `paths_equal` assertion tests |
| Numeric and collection policy | tolerance and declared unordered-array tests; ordered behavior is the default |
| Expected MCP errors | official-SDK fixture error returns `MATCH` when `outcome: error` is declared |
| Explicit normalization | path ignore/redact/replace and timestamp, UUID, request-ID, port, and temp-path built-ins in [NORMALIZATION.md](NORMALIZATION.md) |
| File and tree observations | content/bytes/hashes, deterministic tree order, and path containment tests |
| File transitions | public-API assertions for created, modified, and deleted deltas |
| SQLite | URI read-only mode, `query_only`, row cap, and deterministic query test |
| Custom commands | bounded argument-vector execution and versioned JSON stdin/stdout protocol in [EFFECTS.md](EFFECTS.md) |

## Evidence and presentation

| Requirement | Evidence |
|---|---|
| Sanitized requests and responses | typed call arguments plus candidate/reference observations; secret-bearing request/response persistence regression |
| Per-case logs, timings, hashes, diffs, verdicts | scenario evidence directories, `run.json`, value hashes, comparison files, and golden tests |
| Deterministic semantic evidence | durations excluded by test; nondeterminism example produces the same digest twice in a fresh wheel environment |
| Versioned manifest | evidence and baseline schema version 1; digest validation through `inspect` |
| Five CLI commands | `init`, `record`, `verify`, `diff`, and `inspect`, documented in [CLI.md](CLI.md) |
| Reports | terminal, JSON, Markdown, and JUnit tests; first/full differences; quiet/verbose and `NO_COLOR` regression |
| GitHub use | direct CI example plus a pinned-version composite action in `action.yml` |

## Reliability and security

| Requirement | Evidence |
|---|---|
| Secret defense | `from_env`, sensitive literal rejection, URL credential rejection, known-secret replacement, sensitive-key and token-shape redaction |
| Bounds | shared log budget, response/observer limits, SQLite row cap, connection/operation/total timeouts |
| Protocol failures | malformed stdio and abrupt-connection tests return `INCONCLUSIVE` within a bound |
| Filesystem safety | traversal rejection, symlink non-following, and explicit observer roots |
| Runtime network boundary | HTTP client contacts only the declared URL and does not follow redirects; stdio programs remain trusted code |
| Threat model | [SECURITY.md](SECURITY.md) states trusted-code assumptions, non-guarantees, and absence of telemetry/model calls |

## Examples, tests, and repository quality

| Requirement | Evidence |
|---|---|
| Changed business value | `examples/differential` keeps the schema and changes `status` |
| Wrong filesystem effect | `examples/wrong-effect` returns success and writes the wrong invoice total |
| Nondeterminism and uncertainty | `examples/nondeterminism` normalizes runtime noise and then aborts the server |
| Observable test suite | pure unit, stdio/HTTP integration, goldens, negative protocol/contract, security, path/process, and package smoke tests |
| Cross-platform CI | Python 3.11–3.14 on Linux, macOS, and Windows in `.github/workflows/ci.yml` |
| Clean package smoke | built wheel installed in a temporary environment; all five suites and repeatability check run from that install |
| Public repository files | README, Apache-2.0, changelog, roadmap, security/contribution/conduct files, issue forms, PR template, label catalog |
| Contributor entry points | eight scoped drafts in [CONTRIBUTOR_ISSUES.md](CONTRIBUTOR_ISSUES.md), including four `good first issue` drafts |
| Visual assets | original SVG logo/demo and 1280×640 social preview; rendered demo and preview inspected locally |

## Publication boundary

GitHub-only source publication was approved on 2026-08-11. That approval covers creating `GWeale/mcp-behavior`, pushing the reviewed commit, applying repository settings, and opening the reviewed contributor issues.

Tags, GitHub Releases, PyPI publishing, and announcements remain outside the approved scope. After the source repository is public, wait for the full CI matrix and verify the README commands plus composite action from clean environments.
