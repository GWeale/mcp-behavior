# Unicode filenames

This local fixture writes five UTF-8 files in deliberately unsorted creation order.
A direct `file` observer checks `café-猫.txt`; a `tree` observer checks the mixed
ASCII/Unicode ordering. No credentials or external services are required.

```bash
mcp-behavior verify mcp-behavior.yaml --diff-detail full
```

Expected exit code: `0` (`MATCH`). The fixture removes its generated files after
observation; inspect the evidence to see the captured names and UTF-8 contents.

## Filesystem normalization

MCP Behavior preserves the filenames returned by the host filesystem. It does not
silently normalize Unicode names. Linux and Windows commonly preserve the supplied
code points. Some macOS filesystems may enumerate an accented character as a
decomposed sequence, such as `e` plus a combining accent rather than `é`.

The direct file lookup uses the supplied name; the tree retains the host's spelling.
The composed accent occurs inside the `café-猫.txt` basename, so either form keeps
that name between `A.txt` and `z.txt`. The contract checks the other tree paths;
the integration test checks all names after explicit NFC normalization and also
checks that the unmodified tree sequence and semantic digest are stable across two
runs on the same host. Evidence from different filesystems can still differ when
their Unicode representations differ; cross-host equivalence is not implied.
