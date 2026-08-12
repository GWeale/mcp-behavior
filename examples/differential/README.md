# Schema-compatible value drift

Both servers expose the same `lookup(user_id)` tool and return the same response shape. The reference returns `status: active`; the candidate returns `status: suspended`.

```bash
mcp-behavior diff mcp-behavior.yaml --diff-detail full
```

Expected exit code: `1` (`DIVERGE`).
