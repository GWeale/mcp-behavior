# Positioning

Updated: 2026-08-11

## One sentence

MCP Behavior is a parity gate for MCP migrations: it runs the same declared scenario against old and new servers, then compares returned values and observable effects.

## The gap

The official MCP Inspector provides Web, TUI, and scriptable CLI clients for inspecting and exercising servers. Its CLI works in automation and CI. The official conformance framework validates protocol implementations. `mcp-contracts` snapshots and compares exposed schemas and runs schema-oriented boundary checks. `mcp-lock` pins package identity and integrity.

Broader test frameworks also overlap with parts of MCP Behavior. MCP Test Harness is a code-first framework for functional, snapshot, performance, resiliency, and security testing. MCP Observatory focuses on CI-native security testing, schema drift, and health scoring.

MCP Behavior takes a narrower path. It starts after protocol and schema validity, at the point where a team is replacing or refactoring a server. A tool can keep the same name, description, and JSON Schema while returning a different business result, writing the wrong file, or mutating the wrong state. Differential execution and declared effect observers make that migration visible in one reviewable report.

## In scope

- Scenario execution against stdio and Streamable HTTP targets
- Reference-versus-candidate, recorded-baseline, and explicit-expectation modes
- Result normalization and deterministic comparison
- Explicit observation of files, directory trees, SQLite queries, and trusted custom probes
- Reproducible, sanitized evidence suitable for code review and CI

## Out of scope

- MCP wire-protocol conformance
- Schema compatibility classification
- Dependency or tarball integrity
- Interactive browsing and debugging UI
- Agent/model quality evaluation
- Isolation of malicious servers
- Hosted storage, telemetry, or dashboards

## Primary sources

- MCP Inspector: https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector
- MCP specification: https://modelcontextprotocol.io/specification/2026-07-28
- MCP conformance: https://github.com/modelcontextprotocol/conformance
- MCP Contracts: https://github.com/mcp-contracts/mcp-contracts
- MCP Lock: https://github.com/mcpguards/mcp-lock
- MCP Test Harness: https://github.com/vaquarkhan/mcp-test-harness
- MCP Observatory: https://github.com/KryptosAI/mcp-observatory
