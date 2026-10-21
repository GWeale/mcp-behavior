# Runtime dependency policy

MCP Behavior keeps its runtime dependency set small because it runs local commands and writes evidence that may contain sensitive tool results.

## `mcp`

The official Python SDK owns protocol messages, protocol-version negotiation, and stdio and Streamable HTTP client behavior. Reimplementing that wire protocol would duplicate conformance-sensitive code.

Version 2 is required for the 2026-07-28 protocol and the SDK's explicit legacy client mode. The package requires stable `mcp` 2.3 or newer and excludes the next major version. The 2.3 floor includes the 2.2 Streamable HTTP session-exhaustion fix and the subsequent protocol and Windows stdio fixes. See the official [2.2 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0) and [2.3 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0).

## `httpx2`

The official SDK's Streamable HTTP transport accepts a configured `httpx2.AsyncClient`. MCP Behavior creates that client directly so contract headers can be resolved from environment variables without using a private SDK helper. The range follows the SDK's 2.x HTTP client line. The 2.15.1 floor includes the proxy TLS, SSE buffering, multipart-header and decompression fixes from 2.10–2.12, plus the later SSL-context fix. Its Python 3.11 minimum matches this project's existing minimum. HTTPX2 requires the matching HTTPcore2 version; update the pair together rather than independently overriding HTTPcore2. See the upstream [changelog](https://github.com/pydantic/httpx2/blob/main/src/httpx2/CHANGELOG.md).

## `PyYAML`

Nested scenarios, calls, assertions, and observers are easier to review in YAML than in TOML arrays of tables or raw JSON. MCP Behavior uses a safe loader with stricter checks for duplicate keys, aliases, and unknown fields. Python object construction is disabled.

## Development dependencies

Pytest, coverage, Ruff, mypy, build, and pip-audit enforce the local release gate. They are not installed for CLI users.

The mypy 2.x and pytest-cov 7.x ranges are deliberate development-only major updates. Pytest-cov 7 removes its subprocess hook; subprocess measurement now requires coverage's own configuration, as described in the [upstream changelog](https://pytest-cov.readthedocs.io/en/latest/changelog.html). This project's suite still meets the coverage gate without enabling that optional measurement. Newer PyYAML stubs type `check_event`, so its obsolete type suppression was removed and the stub minimum now includes that correction. Hatchling's build minimum is 1.31; the build gate verifies the selected backend without adding it to runtime dependencies.

## Security floors and the lockfile

The 2026-10-20 refresh keeps the three direct runtime packages unchanged and updates the affected SDK/HTTP stack together. The lock selects `mcp`/`mcp-types` 2.3.0, `httpx2`/`httpcore2` 2.15.1, PyJWT 2.15.1 and urllib3 2.8.0. The browser-only `httpx2-jsfetch` entry is an upstream conditional dependency for Emscripten; it is not installed on normal Windows, Linux or macOS runs.

`tool.uv.constraint-dependencies` sets security floors for already-transitive PyJWT, urllib3 and certifi. Constraints do not introduce packages or bypass upstream requirements. PyJWT is brought by the SDK; urllib3 and certifi are brought by development tooling. The PyJWT and urllib3 updates address the repository's existing Dependabot advisories. A live pip-audit also identified `PYSEC-2026-4320` in certifi 2026.7.22, so the lock and constraint use 2026.10.19 or newer.

These uv constraints protect this repository's resolution and lockfile; they are not published as wheel runtime requirements. Consumers should audit their own resolved environment, especially when using an existing lock or preinstalled transitive packages. An audit passing on one date is not a guarantee about future advisories.

## Actions

Checkout 7.0.0, setup-uv 10.3.0 and the composite action's setup-python 7.0.0 are pinned to the full commits verified against their official release tags. Existing triggers, permissions, matrices and inputs are preserved. Setup-python's removed `pip-install` input is not used here; the workflows continue to use setup-uv. See [checkout 7](https://github.com/actions/checkout/releases/tag/v7.0.0), [setup-uv 10.3](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.0), and [setup-python 7](https://github.com/actions/setup-python/releases/tag/v7.0.0).

## Consolidated PR coverage (2026-10-20)

One tested resolution replaces overlapping bot lockfile edits. After the consolidation lands, the following PRs can be closed as superseded:

| PR | Proposed update | Included resolution |
| --- | --- | --- |
| [25](https://github.com/GWeale/mcp-behavior/pull/25) | MCP 2.2.0 | Stable SDK and matching types 2.3.0; runtime minimum raised. |
| [24](https://github.com/GWeale/mcp-behavior/pull/24) | setup-uv 10.3.0 | Exact official 10.3.0 commit in both workflows. |
| [23](https://github.com/GWeale/mcp-behavior/pull/23) | urllib3 2.8.0 | Lock and transitive security floor 2.8.0. |
| [22](https://github.com/GWeale/mcp-behavior/pull/22) | PyJWT 2.15.0 | Patch 2.15.1 with a transitive security floor. |
| [19](https://github.com/GWeale/mcp-behavior/pull/19) | HTTPcore2 2.10.0 | Matching HTTPX2/HTTPcore2 pair 2.15.1. |
| [18](https://github.com/GWeale/mcp-behavior/pull/18) | HTTPX2 2.12.0 | Matching pair 2.15.1 and runtime minimum. |
| [17](https://github.com/GWeale/mcp-behavior/pull/17) | PyYAML stubs 20260815 | Latest 20260906 stubs, minimum 20260815, obsolete ignore removed. |
| [15](https://github.com/GWeale/mcp-behavior/pull/15) | HTTPX2 2.10.0 minimum | Superseded by the 2.15.1 floor and lock. |
| [5](https://github.com/GWeale/mcp-behavior/pull/5) | Hatchling minimum 1.31 | Same minimum; build remains isolated. |
| [4](https://github.com/GWeale/mcp-behavior/pull/4) | mypy 2.3.0 | Same 2.x floor, lock selects 2.4.0. |
| [3](https://github.com/GWeale/mcp-behavior/pull/3) | pytest-cov 7.1.0 | 7.1.0 floor and lock. |
| [2](https://github.com/GWeale/mcp-behavior/pull/2) | checkout 7 | Exact official 7.0.0 commit in both workflows. |
| [1](https://github.com/GWeale/mcp-behavior/pull/1) | setup-python 7 | Exact official 7.0.0 commit in root `action.yml`. |

Remote Dependabot alerts remain open until the updated lockfile lands and GitHub rescans it. No alert is dismissed as part of this change.
