# Positioning

Updated: 2026-08-08

## One sentence

MCP Behavior runs the same declared scenario against MCP implementations and proves whether their returned values and observable effects agree.

## The gap

The official MCP Inspector is interactive developer tooling for connecting to and exercising servers. The official conformance framework validates protocol implementations. `mcp-contracts` snapshots and compares exposed schemas and runs schema-oriented boundary checks. `mcp-lock` pins package identity and integrity.

Those are useful adjacent tools. MCP Behavior deliberately starts after protocol and schema validity: a tool can keep the same name, description, and JSON Schema while returning a different business result, writing the wrong file, or mutating the wrong state.

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
