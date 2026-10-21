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

The terminal demo is an original repository-native SVG asset. The current logo direction was selected from project-specific concepts made with OpenAI image generation, then independently reconstructed as tracked SVG paths for this repository. Its raster assets and social preview are rendered from those tracked vectors; no third-party branding was used.

### Invoice animation added 2026-10-20

`assets/behavior-demo.gif` and `assets/behavior-demo.mp4` are an original 14-second
explanatory animation grounded in executed checks of the public
[invoice fixture](../examples/wrong-effect/). The requested total is 100; the
intentional bug writes 109 while returning `saved: true`. A declared file assertion
catches the mismatch. Removing `+ 9` makes the same assertion pass.

The values, expressions, and verdicts were checked against recorded manifests and
the fixture source. The animation is labeled as an intentional fixture, not a screen
recording or production incident. Its two branches show observable outcomes; the
actual server writes the file before returning. Timing is editorial, not a latency
measurement. A direct SDK test with the same assertion can detect this error too.

The drawing and motion were authored locally with Pillow and encoded with ffmpeg.
System fonts are rendered into pixels; font files are not redistributed. The
[flow recipe](https://github.com/Vincentwei1021/video-shotcraft/blob/main/references/shots/ui-entrance/bezier-source-converge-merge.md)
informed the moving values and drawn paths. No third-party artwork or branding was copied.

## Project name

An exact-name check on 2026-08-11 found no `GWeale/mcp-behavior` repository on GitHub and no `mcp-behavior` project on PyPI. Package availability must be checked again before a package release.

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
