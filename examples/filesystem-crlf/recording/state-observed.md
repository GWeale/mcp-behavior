# MCP Behavior report

**Verdict:** `DIVERGE`<br>
**Mode:** `expectations`<br>
**Semantic digest:** `d24a7f2fe28a435d0f5daaf4d33184698c142bc189d18ccfa6e1d852c186e230`

| Scenario | Verdict | Calls | Effects |
|---|---:|---:|---:|
| edit preserves CRLF | `DIVERGE` | 1 | 1 |

## edit preserves CRLF

- effect <code>preserved line endings</code> at <code>$.text</code>: values differ
  <br>Expected: <code>&quot;c\r\nb\r\n&quot;</code>
  <br>Actual: <code>&quot;c\nb\n&quot;</code>
