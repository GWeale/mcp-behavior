# CLI reference

```text
mcp-behavior <command> [options]
```

All commands return `2` for invalid configuration or execution uncertainty. Verification commands return `0` for `MATCH` and `1` for a verified `DIVERGE`.

## `init`

Write a strict expectations-mode starter contract.

```bash
mcp-behavior init [path] [--force]
```

The default path is `mcp-behavior.yaml`. Existing files are preserved unless `--force` is explicit.

## `record`

Run the candidate target and write a reviewed JSON baseline.

```bash
mcp-behavior record CONTRACT [--output PATH] [--name NAME] [--tag TAG] [--quiet]
```

The contract must declare `baseline`, or `--output` must provide a path. Repeat `--name` or `--tag` to select scenarios. Names and tags combine with AND semantics: a selected scenario must match the name set and at least one requested tag.

## `verify`

Verify expectations or a recorded baseline.

```bash
mcp-behavior verify CONTRACT [options]
```

## `diff`

Compare reference and candidate targets from a differential contract.

```bash
mcp-behavior diff CONTRACT [options]
```

`verify` and `diff` share these options:

| Option | Default | Meaning |
|---|---|---|
| `--name NAME` | all | select an exact scenario name; repeatable |
| `--tag TAG` | all | select scenarios with any requested tag; repeatable |
| `--evidence PATH` | `.mcp-behavior/evidence` | evidence directory |
| `--format FORMAT` | `terminal` | `terminal`, `json`, `markdown`, or `junit` |
| `--output PATH`, `-o PATH` | stdout | write the rendered report without ANSI color |
| `--diff-detail first` | first | show the first difference in human output |
| `--diff-detail full` | | show every difference in human output |
| `--quiet`, `-q` | off | print only the terminal verdict, or suppress the output-path message |
| `--verbose`, `-v` | off | include timings and sanitized values in terminal output |
| `--color auto` | auto | color verdicts only on a terminal |
| `--color always` | | force terminal color on stdout |
| `--color never` | | disable color |

JSON and JUnit always contain the complete difference set. Human output can be shortened without changing evidence or the exit code. If `NO_COLOR` is present in the environment, ANSI color is disabled even when `--color always` is passed.

## `inspect`

Validate a semantic evidence digest and print its manifest.

```bash
mcp-behavior inspect EVIDENCE [--format terminal|json] [--quiet|--verbose] [--color MODE]
```

`EVIDENCE` may be a directory containing `manifest.json` or the manifest path itself. A missing or invalid digest returns `2`.

## Selection examples

```bash
mcp-behavior verify mcp-behavior.yaml --tag smoke
mcp-behavior verify mcp-behavior.yaml --name "lookup one item"
mcp-behavior diff mcp-behavior.yaml --tag migration --diff-detail full
```
