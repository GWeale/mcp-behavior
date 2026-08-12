# Contract reference

MCP Behavior reads strict YAML. Unknown keys, duplicate mapping keys, YAML aliases, unsupported JSON paths, duplicate names, and incompatible mode settings fail before a target starts.

## Top-level fields

| Field | Required | Meaning |
|---|---:|---|
| `version` | yes | Contract schema version. The current value is `1`. |
| `name` | no | Evidence and baseline identity. Defaults to the filename stem. |
| `variables` | no | Non-secret JSON literals used by `${name}` scenario substitution. |
| `targets` | yes | A `candidate` and optional `reference`. |
| `scenarios` | yes | Ordered named scenarios. |
| `baseline` | no | JSON baseline path, relative to the contract. |
| `timeouts` | no | `connect`, `operation`, and `total` seconds. |
| `limits` | no | `output_bytes` and `log_bytes`. |

The presence of `reference` selects differential mode. Otherwise `baseline` selects baseline mode. A contract with neither uses expectations mode and requires `expect` on every call and observer.

## Scenario variables

Top-level variables reduce repeated non-secret literals:

```yaml
variables:
  item_id: item-42
  quantity: 3

scenarios:
  - name: lookup ${item_id}
    calls:
      - tool: lookup
        arguments:
          id: ${item_id}
          quantity: ${quantity}
```

An exact `${name}` value preserves the variable's JSON type. Embedded references interpolate scalar values into a string. Mapping keys are never substituted. Unknown variables, invalid names, and structured values embedded inside a larger string fail during contract loading.

Variables cannot resolve environment values and sensitive-looking variable names are rejected. Put credentials in target or command `from_env` references so the sanitizer can register them before execution.

## Targets

A stdio target declares an argument vector. Commands never pass through a shell.

```yaml
targets:
  candidate:
    transport: stdio
    command: [node, dist/server.js]
    cwd: .
    workspace: .mcp-behavior/candidate
    mode: auto
    env:
      LOG_LEVEL: warning
      SERVICE_TOKEN:
        from_env: SERVICE_TOKEN
```

An HTTP target points to a Streamable HTTP endpoint:

```yaml
targets:
  candidate:
    transport: http
    url: https://localhost:8443/mcp
    workspace: .mcp-behavior/candidate
    headers:
      Authorization:
        from_env: MCP_TOKEN
        template: "Bearer {value}"
```

Sensitive-looking environment variables and headers must use `from_env`. Resolved values stay in memory and are registered with the evidence sanitizer. `mode` accepts `auto`, `modern`, or `legacy`. Modern mode requires protocol version `2026-07-28`; legacy forces the SDK's legacy client mode.

HTTP URLs cannot contain userinfo credentials or credential-like query fields. Redirects are not followed because the redirected host was not explicitly configured as an MCP target.

## Scenarios and lifecycle

Scenarios run in file order. Each target run follows this lifecycle:

1. Run setup commands.
2. Capture the before state for delta observers.
3. Connect and execute calls in order.
4. Close the MCP connection.
5. Capture after states and calculate deltas.
6. Run cleanup commands, even after an earlier failure.

Setup, cleanup, and observer commands are trusted argument vectors with optional `cwd`, `env`, and `timeout` fields. A total contract timeout also covers queued scenarios.

Scenario names are unique. Call and observer names are unique within each scenario. `--name` selects exact scenario names; `--tag` selects any scenario with a matching tag.

## Calls

```yaml
calls:
  - name: get one record
    tool: records/get
    arguments:
      id: record-1
    normalize:
      ignore: [$.structuredContent.generated_at]
      redact: [$.structuredContent.debug]
      replace:
        $.structuredContent.host: "<host>"
      builtins: [timestamps, request_ids]
    compare:
      kind: json
      numeric_tolerance: 0.01
      unordered: [$.structuredContent.tags]
    expect:
      outcome: success
      contains:
        structuredContent:
          id: record-1
      paths_equal:
        $.structuredContent.status: active
      paths_absent: [$.structuredContent.password]
```

`outcome` is `success` by default and can be set to `error`. Assertions can compare the full value with `equals`, require a recursive subset with `contains`, check exact values at paths, or require paths to be absent.

Comparison kinds have distinct behavior:

| Kind | Behavior |
|---|---|
| `json` | structural JSON diff, numeric tolerance, declared unordered arrays |
| `exact` | root type and value must match exactly |
| `text` | strings or UTF-8 file observations, reported by changed line region |
| `bytes` | UTF-8/base64 file observations, reported at the first changed byte |

`numeric_tolerance` and `unordered` are valid only for `json`. `--diff-detail first` shortens human output; complete differences remain in evidence and machine reports.

See [normalization](NORMALIZATION.md) for rule order and path syntax.

## Observers

File, tree, and SQLite observers resolve relative roots against the target workspace.

```yaml
observers:
  - name: output file
    kind: file
    root: .
    path: output.json
    phase: delta

  - name: cache tree
    kind: tree
    root: cache
    phase: after

  - name: persisted rows
    kind: sqlite
    root: .
    path: state.db
    query: SELECT id, status FROM jobs ORDER BY id
```

A custom observer receives one JSON value on stdin and must write one JSON value to stdout. Stderr is retained as bounded evidence.

```json
{"version":1,"scenario":"name","observer":"probe","phase":"before"}
```

Use `phase: after` for one snapshot. Use `phase: delta` to receive `change` (`created`, `deleted`, `modified`, or `unchanged`) plus the `before` and `after` values.

The full observer protocol and containment rules are documented in [observable effects](EFFECTS.md).
