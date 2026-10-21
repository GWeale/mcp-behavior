# External observers: the working extension boundary

Two runnable command observers project different stores into the same invoice
value: [JSON documents](../examples/external-observers/json_probe.py) and
[SQLite rows](../examples/external-observers/sqlite_probe.py). Both use only the
Python standard library. They run outside the core package as trusted local
processes. [ADR 0007](adr/0007-external-observer-boundary.md) explains why these
examples do not introduce a general plugin SDK or comparator callback.

## Run the actual examples

From a source checkout after `uv sync --frozen`:

```console
uv run python examples/external-observers/run.py --evidence .mcp-behavior/external-match
uv run python examples/external-observers/run.py --write-drift --evidence .mcp-behavior/external-drift
```

The first exits 0 with two `MATCH` effects. The second exits 1 with two `DIVERGE`
effects: the tool returns `saved: true`, but each store contains 10009 cents
instead of 10000. The runner creates and removes a disposable workspace and
retains evidence at the chosen path. The observers do not modify the source
document or database. The separate MCP fixture writes them as the behavior under
test.

## Input and output

Core launches the declared argv without a shell, in the command's configured cwd
or the target workspace. It writes one JSON request on stdin:

```json
{"version":1,"scenario":"invoice projections","observer":"json invoice projection","phase":"after"}
```

Both probes validate version 1 and these fields. An unknown input version exits
nonzero with a generic stderr message. Before and after requests use the same
shape; core, rather than the probe, constructs a delta when `phase: delta` is
configured in the contract.

A successful probe writes exactly one JSON value to stdout and exits 0:

```json
{"version":1,"state":"present","columns":["invoice_id","total_cents"],"rows":[["inv-42",10000]]}
```

The domain payload is version 1: IDs are unique nonempty strings, totals are
integer cents, columns have fixed order, and rows sort by ID. Missing files
produce `state: missing` and empty rows. Invalid data, duplicate IDs, unreadable
state, wrong protocol versions, and bounds failures exit 2 with no stdout value.
Diagnostics do not interpolate paths, input, or database errors.

The JSON probe intentionally ignores storage metadata and source row/object-key
order. It preserves IDs and exact integer cents. The SQLite probe selects only
those columns with a fixed query, orders with BINARY collation, opens a
[`mode=ro` URI](https://docs.python.org/3/library/sqlite3.html#how-to-work-with-sqlite-uris),
and enables [`query_only`](https://www.sqlite.org/pragma.html#pragma_query_only).
It does not accept arbitrary SQL or enable extensions. The shared projection is
the semantic comparison policy: changes outside it are intentionally untested.
The [tests](../tests/test_external_observer_examples.py) check matching Unicode
ordering and unchanged source bytes, as well as changed totals through `verify`.

## What core owns

| Responsibility | Existing behavior |
| --- | --- |
| Process lifetime | Per-command/operation and scenario total timeouts; cleanup on failure |
| Output bounds | Shared stdout/stderr `limits.log_bytes`; parsed value `limits.output_bytes` |
| Data handling | Explicit normalization, registered-secret redaction, normal evidence writer |
| Comparison | Existing `compare` settings and `expect` assertions; probe output is data |
| Verdict | Completed mismatches `DIVERGE`; failed/incomplete capture `INCONCLUSIVE` |

These probes additionally cap request input at 8 KiB, invoice count at 1000, and
serialized output at 64 KiB. The JSON source has a 64 KiB read cap. SQLite fetches
at most 1001 rows to detect overflow; that row cap is not a general memory limit
on cell contents. Core limits still apply if a probe ignores its own bounds.
Neither a row cap nor process termination makes trusted code a hostile-code
sandbox. See [effects](EFFECTS.md) for the existing execution contract.

Credential-bearing command environment entries must use `from_env`, for example:

```yaml
env:
  PROBE_VALUE:
    from_env: MCP_BEHAVIOR_PROBE_TEST_VALUE
```

Core registers the resolved value for redaction. In the test, a generated fake
value also appears in source data; both returned projections and evidence replace
it with `<redacted>`. The probes have no sanitizer and do not receive core
internals. Merely inheriting an environment variable does not register it, and
arbitrary secrets discovered inside source data are not automatically recognized.
Project only data appropriate to retain and explicitly register any needed
credential references. Do not print credentials or return connection errors.

## Failure mapping and version policy

| Observation | Result |
| --- | --- |
| A completed projection contains 10009 where 10000 is expected | `DIVERGE` |
| A missing file returns a valid missing-state value against a present-state expectation | `DIVERGE` |
| Exit nonzero, invalid JSON, timeout, excessive logs or output, or failed source read | `INCONCLUSIVE` |
| Unsupported input version rejected by one of these probes | `INCONCLUSIVE` |
| Valid JSON with a different payload version than the pinned expectation | `DIVERGE` under current JSON comparison |

Core validates JSON syntax, not this invoice schema or its version field. The
probes guarantee their own successful output shape. If a consumer adds a wrapper
for a less trusted source, that wrapper must reject invalid domain responses
with nonzero exit. Never encode an observation failure as `rows: []` or a verdict
field in otherwise successful JSON; core cannot infer that convention.

The shared [protocol helper](../examples/external-observers/probe_protocol.py) is
example-local implementation code, not a supported Python import. Input version
changes and output payload version changes require separate, explicit review.
The alpha compatibility caveat remains; this is the narrow working boundary
from two implemented cases, not a promise of a stable general SDK.

Primary API references checked 2026-10-20. No runtime dependency was added.
