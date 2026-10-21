# Expected tool errors and broken connections

The local `lookup_item` tool succeeds for `known` and rejects `missing` with an MCP
tool error. The contract explicitly expects that rejection with
`expect.outcome: error`:

```bash
mcp-behavior verify mcp-behavior.yaml --diff-detail full
```

Expected exit code: `0` (`MATCH`). Both calls match their declared outcomes: a
successful lookup and a completed tool-error response for an invalid ID. A tool
error is an observed application result, not automatically a failed test. This
contract checks the outcome category; it does not assert the exact error text.

For the counterexample, the same fixture exits before establishing its MCP
connection:

```bash
mcp-behavior verify broken-connection.yaml --diff-detail full
```

Expected exit code: `2` (`INCONCLUSIVE`). No completed MCP tool result exists, so
`expect.outcome: error` cannot turn the broken connection into a match. Evidence
records the connection failure separately from the expected application error.

No credentials, network services, or model calls are required. Both contracts are
included in the clean-wheel smoke matrix.
