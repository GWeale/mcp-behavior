# CI and GitHub Action

The CLI's exit codes are stable:

| Code | Verdict | Meaning |
|---:|---|---|
| 0 | `MATCH` | Every selected scenario matched. |
| 1 | `DIVERGE` | At least one behavior difference or failed assertion was found. |
| 2 | `INCONCLUSIVE` | The run could not establish a result. Contract and CLI errors also use 2. |

## Composite action

```yaml
name: MCP behavior
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: GWeale/mcp-behavior@v0.1.0
        with:
          contract: mcp-behavior.yaml
          evidence: .mcp-behavior/evidence
          report: .mcp-behavior/report.xml
      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: mcp-behavior-evidence
          path: .mcp-behavior/
```

The action installs the pinned release specified by its `version` input, runs verification, writes JUnit, and leaves evidence for later upload. It does not upload artifacts on its own.

The repository CI matrix runs Python 3.11 through 3.14 on Ubuntu, macOS, and Windows. Its package job builds the wheel and source archive, verifies their metadata and provenance, installs the wheel in a fresh environment, and runs all five public examples with their documented exit codes.

## Direct CLI

For projects that already manage Python, install the package in the job and call the CLI directly. `--name` can be repeated for exact scenarios. `--tag` can be repeated and matches any listed tag.

```bash
mcp-behavior verify mcp-behavior.yaml \
  --tag smoke \
  --format json \
  --output .mcp-behavior/report.json
```

Use `--diff-detail full` for a complete human report. JSON and JUnit always retain the complete difference set.
