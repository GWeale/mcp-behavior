<p align="center">
  <img src="docs/assets/readme-header.png" width="960" alt="MCP Behavior — Test the response. Check the change.">
</p>

[![CI](https://github.com/GWeale/mcp-behavior/actions/workflows/ci.yml/badge.svg)](https://github.com/GWeale/mcp-behavior/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Your MCP tool returned success. Did it write the right thing?**

Regression tests for MCP tool responses **and the state they change**. Declare file, directory, SQLite, or custom-probe checks in YAML; compare against expectations, a baseline, or another server.

## Same successful response. Different file bytes.

The official filesystem server's `edit_file` used to replace CRLF line endings with LF while returning the expected edit diff. Upstream fixed it in [PR #5011](https://github.com/modelcontextprotocol/servers/pull/5011). We reproduced the historical regression using published versions:

```text
MATCH        2026.8.31    response-only    actual: c\nb\n
DIVERGE      2026.8.31    state-observed   expected: c\r\nb\r\n
MATCH        2.0.0        fixed-control    actual: c\r\nb\r\n
```

**[Watch the recorded demo](docs/assets/filesystem-crlf-demo.mp4)** · [Reproduce it](examples/filesystem-crlf/) · [Read the captured output](examples/filesystem-crlf/recording/transcript.txt)

A direct SDK test with the same file assertion catches this too. MCP Behavior gives you one contract, verdict, and evidence bundle. It checks the effects you declare; it does not discover every side effect.

## Try it

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+. No API key or existing server needed.

```bash
uvx --from git+https://github.com/GWeale/mcp-behavior.git@v0.1.0 mcp-behavior demo
```

This separate, intentional invoice fixture runs three real checks and removes its temporary files. It writes 109 while returning `saved: true` for a requested total of 100:

```text
MATCH        response only: file total = 109
DIVERGE      response + file state: file total = 109
MATCH        corrected implementation: file total = 100
```

## Test your server

```bash
uv tool install git+https://github.com/GWeale/mcp-behavior.git@v0.1.0
mcp-behavior init
```

The starter includes a file assertion. Edit the server command, tool arguments, expected path, and contents in `mcp-behavior.yaml`, then run:

```bash
mcp-behavior verify mcp-behavior.yaml
```

Use `mcp-behavior init --template sqlite` for database rows, or `--template response` for tools with no state changes. For semantic JSON comparisons, adapt the [working JSON probe](examples/external-observers/). See the [complete example](examples/expectations/), [observers](docs/EFFECTS.md), and [contract reference](docs/CONTRACT.md).

| Result | Meaning | Exit |
|---|---|---:|
| `MATCH` | The selected checks agree. | 0 |
| `DIVERGE` | A response or declared effect differs. | 1 |
| `INCONCLUSIVE` | The run could not establish a result. | 2 |

Each run saves evidence and differences. Export reports as JSON, Markdown, or JUnit, or use the [GitHub Action](docs/CI.md) in CI.

Found a response that hides a wrong state change? [Open a minimal, sanitized case](https://github.com/GWeale/mcp-behavior/issues/new?template=bug_report.yml) with server/version, request, expected state, and actual state. Reproducible cases are especially useful.

## Reference

[CLI](docs/CLI.md) · [Python API](docs/API.md) · [Evidence](docs/EVIDENCE.md) · [Examples](examples/) · [Authenticated HTTP](docs/AUTHENTICATED_HTTP.md) · [Contributing](CONTRIBUTING.md)

Alpha: install from the pinned GitHub tag or download a wheel from [v0.1.0](https://github.com/GWeale/mcp-behavior/releases/tag/v0.1.0). See [compatibility](docs/COMPATIBILITY.md) for schema guarantees. Configured servers and probes run as trusted code; see [security](docs/SECURITY.md). No telemetry or model calls.
