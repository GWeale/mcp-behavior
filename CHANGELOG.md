# Changelog

This project follows [Semantic Versioning](https://semver.org/). Contract and evidence schema changes are called out separately from Python API changes.

## [Unreleased]

### Added

- A reproducible, credited case of the official filesystem server's fixed CRLF regression, with published version pins, independent byte checks, and a recorded terminal demo.
- File (default), SQLite, and response-only `init --template` starters.
- Bounded expected/actual previews in terminal and Markdown reports; complete JSON evidence is preserved.

### Changed

- Plain `init` now includes a file-state assertion. Use `init --template response` for the previous response-only starter.
- Clean-wheel smoke checks cover all starter templates and the executable invoice demo.

## [0.1.0] - Unreleased

### Added

- Expectations, recorded-baseline, and live differential verification.
- Official MCP SDK adapters for stdio and Streamable HTTP targets.
- Strict version 1 YAML contracts with literal variables, names, tags, lifecycle commands, explicit normalization, assertions, and comparison controls.
- File, directory-tree, SQLite, and custom-command effect observers.
- Canonical sanitized request/response evidence with per-case hashes and semantic digests.
- Exact, JSON, line-oriented text, and byte-offset comparisons.
- Terminal, JSON, Markdown, and JUnit reports with first/full differences, quiet/verbose modes, and `NO_COLOR` support.
- `init`, `record`, `verify`, `diff`, and `inspect` CLI commands.
- Composite GitHub Action and five runnable example suites covering expectations, baselines, value drift, incorrect effects, normalization, and uncertainty.
- Linux, macOS, and Windows CI across Python 3.11 through 3.14.

[Unreleased]: https://github.com/GWeale/mcp-behavior/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/GWeale/mcp-behavior/releases/tag/v0.1.0
