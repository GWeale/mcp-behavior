# Generated binary file comparison

The local MCP tool generates 18 bytes: integers 0 through 15 followed by `0xff`
and `0x80`. No binary blob is checked in. The `file` observer returns its base64
envelope, and `compare.kind: bytes` compares decoded bytes rather than JSON
metadata or the encoded string.

```bash
mcp-behavior verify mcp-behavior.yaml --diff-detail full
```

Expected exit code: `0` (`MATCH`).

The second contract changes only the byte at zero-based offset 7, from `0x07` to
`0x08`, while returning the same success fields and length:

```bash
mcp-behavior verify wrong-byte.yaml --diff-detail full
```

Expected exit code: `1` (`DIVERGE`), with `$[byte:7]` and
`bytes differ at offset 7`. Both cases remove the generated file after observation;
their evidence retains the actual byte envelope and comparison. Both contracts are
included in the clean-wheel smoke matrix and need no credentials or services.
