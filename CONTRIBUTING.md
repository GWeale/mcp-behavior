# Contributing

Bug reports, focused fixes, and examples from different MCP server stacks are welcome.

## Local setup

```bash
git clone https://github.com/GWeale/mcp-behavior.git
cd mcp-behavior
uv sync --all-groups
uv run pytest
```

Before opening a pull request, run:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=mcp_behavior
```

The exact release gate is:

```bash
uv run python scripts/release_gate.py
```

It also audits provenance and secrets, builds the package, installs the wheel in a temporary environment, and dogfoods every public example.

Tests should exercise observable behavior through the public API when possible. A transport adapter or observer deserves a smaller seam only when the behavior actually varies there.

## Pull requests

Keep changes scoped. Include a test for behavior changes and update the contract reference when YAML semantics change. Do not include credentials, private evidence, generated caches, or code copied from a private project.

By submitting a contribution, you agree that it is licensed under Apache-2.0.

See the [ranked roadmap](ROADMAP.md) for direction and the [prepared contributor issues](docs/CONTRIBUTOR_ISSUES.md) for bounded starting points.
