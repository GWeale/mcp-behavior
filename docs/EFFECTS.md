# Observable effects

An MCP call can return the expected JSON and still write the wrong file or update the wrong row. Observers make selected state part of the behavior contract.

## Observer types

| Kind | Captured value | Bound |
|---|---|---|
| `file` | missing/present state, encoding, content, byte count, SHA-256 | `limits.output_bytes` |
| `tree` | sorted relative paths, entry type, size, file SHA-256 | serialized output limit |
| `sqlite` | column names and at most 1,000 rows from a read-only query | serialized output limit |
| `command` | one JSON value returned by a trusted argument vector | output, log, and time limits |

## Snapshot and delta phases

`phase: after` captures one value after the target closes. `phase: delta` captures before and after values and derives `created`, `deleted`, `modified`, or `unchanged`.

```yaml
observers:
  - name: generated invoice
    kind: file
    root: .
    path: invoice.json
    phase: delta
    expect:
      contains:
        change: created
        after:
          state: present
```

File creation, modification, and deletion assertions use the delta's `change` field. Content assertions can target `before.text`, `after.text`, hashes, or binary `data`.

## Filesystem containment

Relative observer paths resolve under the declared `root`. An absolute observer path is rejected, and a relative path that resolves outside the root fails the run. Tree observers do not follow symbolic links.

Roots themselves may be absolute because integration tests sometimes observe a prepared workspace. Keep them narrow. Path containment does not restrict the trusted MCP server or custom commands.

## SQLite probes

SQLite connections use URI read-only mode plus `PRAGMA query_only`. Queries must start with `SELECT` or `WITH`. Add `ORDER BY` when row order is semantically important.

## Custom probe protocol

A command observer receives one compact JSON document on stdin:

```json
{"version":1,"scenario":"invoice export","observer":"queue state","phase":"after"}
```

It must write one JSON value to stdout and use stderr for bounded diagnostics. A nonzero exit, invalid JSON, timeout, or oversized value makes the scenario inconclusive. Commands use argument vectors without a shell.

Custom probes and local MCP servers are trusted code. Use a container, VM, or restricted CI runner for untrusted programs.
