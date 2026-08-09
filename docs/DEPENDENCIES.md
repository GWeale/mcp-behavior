# Runtime dependency policy

MCP Behavior keeps its runtime dependency set small because it runs local commands and writes evidence that may contain sensitive tool results.

## `mcp`

The official Python SDK owns protocol messages, protocol-version negotiation, and stdio and Streamable HTTP client behavior. Reimplementing that wire protocol would duplicate conformance-sensitive code.

Version 2 is required for the 2026-07-28 protocol and the SDK's explicit legacy client mode. The package accepts stable `mcp` 2.x releases and excludes the next major version.

## `httpx2`

The official SDK's Streamable HTTP transport accepts a configured `httpx2.AsyncClient`. MCP Behavior creates that client directly so contract headers can be resolved from environment variables without using a private SDK helper. The range follows the SDK's 2.x HTTP client line.

## `PyYAML`

Nested scenarios, calls, assertions, and observers are easier to review in YAML than in TOML arrays of tables or raw JSON. MCP Behavior uses a safe loader with stricter checks for duplicate keys, aliases, and unknown fields. Python object construction is disabled.

## Development dependencies

Pytest, coverage, Ruff, mypy, build, and pip-audit enforce the local release gate. They are not installed for CLI users.
