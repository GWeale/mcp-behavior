# Compatibility

## Python and operating systems

| Runtime | Policy |
|---|---|
| Python 3.11 | supported and included in CI |
| Python 3.12 | supported and included in CI |
| Python 3.13 | supported and included in CI |
| Python 3.14 | supported and included in CI |
| Linux | tested on GitHub's latest Ubuntu runner |
| macOS | tested on GitHub's latest macOS runner |
| Windows | tested on GitHub's latest Windows runner |

The matrix runs the same public tests on all twelve OS and Python combinations. The package is pure Python and ships one `py3-none-any` wheel.

## MCP support

| Area | v0.1 support |
|---|---|
| SDK | official Python SDK `mcp>=2,<3` |
| Local transport | stdio commands |
| Remote transport | Streamable HTTP URLs |
| Protocol mode | automatic negotiation, explicit modern, explicit legacy |
| Modern protocol | `2026-07-28` |
| HTTP credentials | static headers resolved through `from_env` |
| OAuth flows | configure outside MCP Behavior and provide the resulting header |

Streamable HTTP redirects are intentionally unsupported. Configure the final endpoint URL directly.

Protocol conformance remains the responsibility of the official conformance suite. MCP Behavior starts after a target can negotiate a client session and focuses on executed tool behavior.

## Evidence and contract compatibility

Contract, baseline, and evidence schemas each start at version `1`. v0.1 rejects unknown schema versions and unknown fields. Backward-compatibility guarantees begin with the first published release. Breaking schema changes require a new schema version and migration notes.

## Known limits

- HTTP targets must already be reachable; MCP Behavior does not start a remote service.
- v0.1 runs scenarios sequentially.
- There is no hostile-code sandbox.
- SQLite is the only database observer in v0.1.
- Custom comparators and observers do not have a public extension SDK yet.
