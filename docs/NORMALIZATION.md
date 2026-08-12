# Normalization

Normalization removes declared runtime noise before comparison. Every rule is visible in the contract. MCP Behavior does not infer fields to ignore from a passing or failing run.

## Rule order

Rules run in this order:

1. Narrow built-in transforms
2. `ignore` paths
3. `redact` paths
4. `replace` paths

The input observation is copied before any rule runs.

```yaml
normalize:
  builtins: [timestamps, uuids, request_ids, ports, temp_paths]
  ignore:
    - $.content
  redact:
    - $.structuredContent.debug
  replace:
    $.structuredContent.host: <host>
```

## Built-ins

| Name | Values it replaces |
|---|---|
| `timestamps` | Complete ISO-8601 timestamp strings |
| `uuids` | Complete RFC 4122 UUID strings |
| `request_ids` | Values under request, trace, or run ID keys |
| `ports` | Integer port fields and ports embedded in URLs |
| `temp_paths` | Windows temporary paths and `/tmp/...` paths |

Built-ins are intentionally narrow. For example, `timestamps` does not rewrite an arbitrary sentence that happens to contain a date.

## JSON paths

The supported path subset is deterministic:

```text
$
$.result.items[0].id
$._meta['io.modelcontextprotocol/serverInfo']
```

Dot keys, numeric list indexes, and quoted object keys are supported. Wildcards, filters, recursive descent, slices, and expressions are rejected while loading the contract.

`ignore` removes a value at the declared path. `redact` retains the path and replaces its value with `<redacted>`. `replace` uses the literal value from the contract. Missing paths are left unchanged; no undeclared path is modified.

## Normalization versus secret sanitization

Normalization is comparison policy. Secret sanitization is a persistence boundary and always runs before evidence is written. Values resolved through `from_env`, common credential-shaped keys, bearer credentials, and common key formats receive defensive redaction even when the contract has no normalization rule.

Do not use normalization to hide a real behavior change. Review ignored paths in the same way you review test assertions.
