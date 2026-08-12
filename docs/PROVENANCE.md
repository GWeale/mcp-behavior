# Provenance and license audit

Audit date: 2026-08-11

## Clean-room origin

MCP Behavior is a new implementation written for this public repository. No code, fixtures, documentation, branding, or confidential implementation details were copied from a private repository or employer project.

The product boundary was informed by public behavior-testing concepts and these primary sources:

- [MCP specification](https://modelcontextprotocol.io/specification/2026-07-28)
- [Official MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [Official MCP conformance suite](https://github.com/modelcontextprotocol/conformance)
- [MCP Contracts](https://github.com/mcp-contracts/mcp-contracts)
- [MCP Lock](https://github.com/mcpguards/mcp-lock)

The [positioning note](POSITIONING.md) records where this project begins and where those tools remain the better fit.

The logo, social preview, and terminal demo are original repository-native SVG assets. The PNG social preview is a rasterization of the tracked SVG.

## Project name

An exact-name check on 2026-08-08 found no `mcp-behavior` project on GitHub, PyPI, or npm. The availability check must be repeated immediately before the public repository and package are created.

## License review

The project uses Apache-2.0. Runtime dependency metadata reports compatible permissive licenses:

| Dependency | Reviewed version | Declared license | Purpose |
|---|---:|---|---|
| `mcp` | 2.0.0 | MIT | official protocol client and transports |
| `httpx2` | 2.9.1 | BSD-3-Clause | configured HTTP client required by the SDK transport |
| `PyYAML` | 6.0.3 | MIT | safe contract parsing |

Version ranges and dependency reasons are documented in [DEPENDENCIES.md](DEPENDENCIES.md). Package metadata and the full license text both declare Apache-2.0.

## Automated release audit

`scripts/audit_release.py` checks source files for:

- private-project provenance terms
- private-key blocks and high-confidence credential shapes
- credential file extensions and `.env` files
- consistency between package metadata and the Apache-2.0 license

`scripts/verify_dist.py` separately checks wheel metadata, archive paths, required modules, and the same private-project provenance boundary inside built artifacts. `pip-audit` checks installed dependencies for known vulnerabilities.

These checks reduce release mistakes. They do not prove authorship or detect every possible secret. A maintainer must still inspect the staged diff, package contents, evidence fixtures, and publication settings before release.
