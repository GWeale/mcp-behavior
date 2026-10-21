# Authenticated Streamable HTTP: local header example

This [runnable fixture](../examples/authenticated-http/run.py) starts the official
SDK's Streamable HTTP server on loopback, requires an authorization header, and
passes that header through `from_env`. It generates a fresh test value in memory;
there is no credential to paste into a command, YAML file, or shell history.

From a source checkout with `uv sync --frozen` completed:

```console
uv run python examples/authenticated-http/run.py --evidence .mcp-behavior/http-authorized
```

Expect exit 0 and `MATCH`, with both `redaction_checked` and
`redacted_value_present` true. The tool deliberately returns the generated test
value. The runner checks every evidence file for its absence without printing
the value; the normalizer replaces it with `<redacted>`. This is a fixture for
testing accidental disclosure, not a pattern for a production tool response.

The generated contract uses this header declaration:

```yaml
headers:
  Authorization:
    from_env: MCP_BEHAVIOR_EXAMPLE_TOKEN
    template: "Bearer {value}"
```

`MCP_BEHAVIOR_EXAMPLE_TOKEN` is an example variable name. In your own contract,
have your secret manager populate the referenced environment variable before
verification. Keep credential values out of `variables`, command arguments, URLs,
and literal headers. See [contract fields](CONTRACT.md) and
[the evidence boundary](adr/0003-evidence.md).

## Missing-variable check

```console
uv run python examples/authenticated-http/run.py --missing-token --evidence .mcp-behavior/http-missing
```

Expect exit 2 and `INCONCLUSIVE`. The server retains its generated credential,
but the runner removes the client's variable before verification. The diagnostic
names the missing variable; it does not contain a token. This is configuration
failure, not evidence of changed server behavior. These commands start and stop
only the local fixture and retain the chosen evidence directories.

## What this proves

The [server](../examples/authenticated-http/server.py) rejects a missing or wrong
header with HTTP 401 before passing a request to the MCP application. The client
then completes an MCP call when it receives the matching environment value. The
[tests](../tests/test_authenticated_http_example.py) cover authorization, missing
configuration, and persisted-value redaction.

This fixture uses a single shared test value over local HTTP. It does not perform
OAuth discovery, token issuance, scope checks, refresh, or audience validation.
Production HTTP authorization must follow the
[MCP authorization specification](https://modelcontextprotocol.io/specification/latest/basic/authorization)
and use its required transport protections. Header injection alone does not
implement that authorization flow. The API used here is the official SDK's
[`streamable_http_app`](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/mcpserver/server.py).
Sources checked 2026-10-20; the runnable fixture is checked against this repository's
locked SDK dependency.
