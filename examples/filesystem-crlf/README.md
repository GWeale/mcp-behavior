# A real edit that returned the same diff and wrote different bytes

This reproduces a **fixed historical regression** in the official
`@modelcontextprotocol/server-filesystem`. It is based on upstream
[PR #5011](https://github.com/modelcontextprotocol/servers/pull/5011), authored by
Cliff Hall and merged on October 5, 2026. The bug and its fix belong to that work;
this project did not discover them.

Start with `a\r\nb\r\n`. Ask `edit_file` to replace `a` with `c`.
The published versions below return identical successful tool content, including
the edit diff. Their resulting files differ:

| Check | Server version | File bytes | Verdict |
|---|---|---|---|
| Response success only | `2026.8.31` | `63 0a 62 0a` (LF) | `MATCH` |
| Response + file expectation | `2026.8.31` | `63 0a 62 0a` (LF) | `DIVERGE` |
| Same expectation, fixed server | `2.0.0` | `63 0d 0a 62 0d 0a` (CRLF) | `MATCH` |

This is one bounded example, not a survey of MCP reliability. A direct SDK test
with a byte assertion catches it too. MCP Behavior packages the response check,
declared state check, verdict, and evidence together.

## Reproduce

Requires Node.js, npm, and this repository's `uv sync --locked` environment.
Run from the repository root. These commands install and execute the two official
servers as trusted local code; no model credentials are needed. Installation
downloads npm dependencies. Only the two top-level server versions are pinned;
npm may resolve different transitive versions on a later installation.

```bash
npm install --prefix .mcp-behavior/crlf-before --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-filesystem@2026.8.31
npm install --prefix .mcp-behavior/crlf-after --ignore-scripts --no-audit --no-fund @modelcontextprotocol/server-filesystem@2.0.0
uv run python examples/filesystem-crlf/reproduce.py --before .mcp-behavior/crlf-before/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js --after .mcp-behavior/crlf-after/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js --evidence .mcp-behavior/crlf-evidence
```

Use a new evidence directory for each run. The script refuses an existing one.
It validates package identity and versions, reseeds one disposable workspace
before each check, and selects the legacy protocol era supported by both servers.
It independently reads the resulting bytes, checks all three verdicts, and
compares the tool content across stages. Any unexpected result fails the script.
The workspace is removed; the evidence and `summary.json` remain.
Each stage also exports a Markdown report. Here is the captured
[state-check report](recording/state-observed.md), including the escaped expected
and actual text values.

The crucial observer is ordinary version 1 YAML:

```yaml
observers:
  - name: preserved line endings
    kind: file
    root: .
    path: crlf.txt
    phase: after
    expect:
      contains:
        state: present
        text: "c\r\nb\r\n"
```

Raw reports include the generated workspace paths, so review them before sharing.
The checked-in [receipt](recording/summary.json) substitutes `<workspace>` only
in the displayed diff. It includes server entrypoint hashes, environment versions,
and independently checked bytes. It does not identify the entire npm dependency
tree or claim cross-platform timing equivalence.

## Recorded demo

[Watch the terminal replay](../../docs/assets/filesystem-crlf-demo.mp4), read the
[captured stdout](recording/transcript.txt), or replay the original
[asciinema cast](recording/demo.cast). The video uses a slower reading pace; its
duration is not execution latency. The cast retains the original output timing.

To record another run, replace the final reproduction command above with:

```bash
uv run python scripts/record_demo.py --output .mcp-behavior/crlf-recording --before .mcp-behavior/crlf-before/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js --after .mcp-behavior/crlf-after/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js --evidence .mcp-behavior/crlf-recorded-evidence
```
