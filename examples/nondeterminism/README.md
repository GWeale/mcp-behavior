# Nondeterminism and uncertainty

The first scenario returns a fresh timestamp, UUIDs, request ID, port, and temporary path on every call. Explicit normalization makes the semantic evidence stable.

The second scenario terminates the MCP server during a call. MCP Behavior reports `INCONCLUSIVE` instead of treating the missing response as a match or a verified divergence.

```bash
mcp-behavior verify mcp-behavior.yaml --diff-detail full
```

Expected exit code: `2` (`INCONCLUSIVE`).
