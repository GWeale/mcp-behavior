# Wrong filesystem effect

The `export_invoice` tool returns `saved: true`, but it writes the wrong total. MCP Behavior checks both the call and the declared file delta. The call matches; the file effect diverges.

```bash
mcp-behavior verify mcp-behavior.yaml --diff-detail full
```

Expected exit code: `1` (`DIVERGE`).
