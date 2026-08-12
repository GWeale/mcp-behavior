# Troubleshooting

## The run is `INCONCLUSIVE`

Read the scenario error and the bounded `logs.txt` file first. Common causes are a server that did not complete MCP initialization, a tool timeout, an abrupt connection close, invalid probe JSON, or a cleanup failure.

Increase a timeout only after checking whether the server is blocked:

```yaml
timeouts:
  connect: 20
  operation: 60
  total: 300
```

An inconclusive run exits `2`. It never passes as a match.

## A stdio target cannot connect

Run the command from the contract's `cwd` and confirm it starts an MCP stdio server without writing logs or other non-protocol text to stdout. Use stderr for logs. Use an argument vector, not one shell command string.

When a virtual environment supplies the server's Python dependencies, activate it before running MCP Behavior or use the environment's absolute Python executable in `command`.

## HTTP works in another client but not here

Confirm that the contract URL includes the Streamable HTTP MCP path. Put credentials in `from_env` headers. MCP Behavior does not perform an interactive OAuth flow.

```yaml
headers:
  Authorization:
    from_env: MCP_TOKEN
    template: "Bearer {value}"
```

## The baseline is rejected

A baseline includes its own semantic digest. Manual edits invalidate it. Record again, inspect the JSON diff, and commit the change only when the new behavior is intended.

## Selection matched nothing

`--name` is exact and case-sensitive. `--tag` matches any requested tag. When both are present, a scenario must satisfy both filters.

## A normalization rule has no effect

Check the path against the sanitized observation in `scenarios/.../observation.json`. MCP Behavior supports dot keys, numeric indexes, and quoted object keys. It does not support wildcards or filters. See [normalization](NORMALIZATION.md).

## An observer path is rejected

`path` must be relative to its declared `root` and cannot resolve outside it. For a different workspace, change the root explicitly instead of using `..`.

## Terminal output contains no color

Color is emitted only for terminal output when stdout is a TTY. `NO_COLOR`, machine report formats, redirected output, and `--output` disable ANSI sequences. Use `--color always` only when the receiving terminal supports it.

## Evidence cannot be written

MCP Behavior refuses broad evidence roots such as the filesystem root, home directory, or the directory containing the contract. Choose a dedicated child directory such as `.mcp-behavior/evidence`.

If the problem persists, include the contract with credentials removed, the CLI version, operating system, Python version, and sanitized evidence in a bug report.
