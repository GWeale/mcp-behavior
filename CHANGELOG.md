# Changelog

This project follows [Semantic Versioning](https://semver.org/). Contract and evidence schema changes are called out separately from Python API changes.

## [Unreleased]

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
