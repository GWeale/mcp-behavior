"""Dependency-free command-line interface for MCP Behavior."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from .contract import ContractError, load_contract
from .core import record, verify
from .evidence import EvidenceError, digest_report_payload
from .execution import ExecutionError
from .models import JsonValue
from .reports import render_manifest, render_report
from .targets import TargetError

REPORT_FORMATS = ("terminal", "json", "markdown", "junit")

STARTER_CONTRACT = """# mcp-behavior.yaml
version: 1
name: my-mcp-server

targets:
  candidate:
    transport: stdio
    command: [python, path/to/server.py]
    workspace: .mcp-behavior/workspace

scenarios:
  - name: example tool succeeds
    tags: [smoke]
    calls:
      - name: example
        tool: example_tool
        arguments: {}
        expect:
          outcome: success
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        return int(arguments.handler(arguments))
    except (ContractError, EvidenceError, ExecutionError, TargetError, OSError, ValueError) as exc:
        print(f"mcp-behavior: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-behavior",
        description=(
            "Parity tests for MCP migrations, including tool results and observable side effects."
        ),
        epilog=(
            "Start with `mcp-behavior init`, then run `mcp-behavior verify mcp-behavior.yaml`."
        ),
    )
    parser.add_argument("--version", action="version", version="mcp-behavior 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="write a strict starter contract",
        description="Write an expectations-mode starter contract without replacing existing work.",
    )
    init_parser.add_argument("path", nargs="?", default="mcp-behavior.yaml", type=Path)
    init_parser.add_argument("--force", action="store_true", help="replace an existing file")
    init_parser.set_defaults(handler=_init)

    record_parser = subparsers.add_parser(
        "record",
        help="record a candidate baseline",
        description="Run selected candidate scenarios and write a digest-protected JSON baseline.",
    )
    _selection_arguments(record_parser)
    record_parser.add_argument("contract", type=Path, help="versioned YAML contract")
    record_parser.add_argument("--output", "-o", type=Path, help="baseline output path")
    record_parser.add_argument("--quiet", "-q", action="store_true", help="suppress success output")
    record_parser.set_defaults(handler=_record)

    verify_parser = subparsers.add_parser(
        "verify",
        help="verify expectations or a baseline",
        description=(
            "Run selected scenarios against explicit expectations or a reviewed baseline. "
            "Exit 0 for MATCH, 1 for DIVERGE, and 2 for INCONCLUSIVE."
        ),
    )
    _verification_arguments(verify_parser)
    verify_parser.set_defaults(handler=_verify)

    diff_parser = subparsers.add_parser(
        "diff",
        help="compare candidate and reference targets",
        description=(
            "Execute a differential contract against its reference and candidate targets. "
            "Exit 0 for MATCH, 1 for DIVERGE, and 2 for INCONCLUSIVE."
        ),
    )
    _verification_arguments(diff_parser)
    diff_parser.set_defaults(handler=_diff)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="inspect deterministic evidence",
        description="Validate and print an evidence manifest or evidence directory.",
    )
    inspect_parser.add_argument("evidence", type=Path, help="manifest path or evidence directory")
    inspect_parser.add_argument("--format", choices=("terminal", "json"), default="terminal")
    _display_arguments(inspect_parser, include_diff=False)
    inspect_parser.set_defaults(handler=_inspect)
    return parser


def _selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--name", action="append", default=[], help="select an exact scenario name; repeatable"
    )
    parser.add_argument(
        "--tag", action="append", default=[], help="select scenarios with this tag; repeatable"
    )


def _verification_arguments(parser: argparse.ArgumentParser) -> None:
    _selection_arguments(parser)
    parser.add_argument("contract", type=Path, help="versioned YAML contract")
    parser.add_argument("--evidence", type=Path, default=Path(".mcp-behavior/evidence"))
    parser.add_argument("--format", choices=REPORT_FORMATS, default="terminal")
    parser.add_argument("--output", "-o", type=Path, help="write the rendered report to a file")
    _display_arguments(parser, include_diff=True)


def _display_arguments(parser: argparse.ArgumentParser, *, include_diff: bool) -> None:
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--quiet", "-q", action="store_true", help="print only the verdict")
    verbosity.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help=(
            "include timings and sanitized observed values"
            if include_diff
            else "include scenario error details"
        ),
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="color terminal verdicts (default: auto; NO_COLOR disables color)",
    )
    if include_diff:
        parser.add_argument(
            "--diff-detail",
            choices=("first", "full"),
            default="first",
            help="show the first or every human-readable difference",
        )


def _init(arguments: argparse.Namespace) -> int:
    path = arguments.path.expanduser().resolve()
    if path.exists() and not arguments.force:
        raise ValueError(f"refusing to replace existing file: {path}; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STARTER_CONTRACT, encoding="utf-8", newline="\n")
    print(path)
    return 0


def _record(arguments: argparse.Namespace) -> int:
    digest = record(
        arguments.contract,
        arguments.output,
        names=tuple(arguments.name),
        tags=tuple(arguments.tag),
    )
    if not arguments.quiet:
        print(f"baseline recorded: {digest}")
    return 0


def _verify(arguments: argparse.Namespace) -> int:
    return _run_verification(arguments)


def _diff(arguments: argparse.Namespace) -> int:
    contract = load_contract(arguments.contract)
    if contract.mode != "differential":
        raise ContractError(
            contract.source, "$.targets.reference", "diff requires a reference target"
        )
    return _run_verification(arguments)


def _run_verification(arguments: argparse.Namespace) -> int:
    report = verify(
        arguments.contract,
        arguments.evidence,
        names=tuple(arguments.name),
        tags=tuple(arguments.tag),
    )
    color = _use_color(arguments.color, arguments.format) and arguments.output is None
    verbosity = "quiet" if arguments.quiet else "verbose" if arguments.verbose else "normal"
    difference_limit = 1 if arguments.diff_detail == "first" else None
    rendered = render_report(
        report,
        arguments.format,
        color=color,
        difference_limit=difference_limit,
        verbosity=verbosity,
    )
    if arguments.output:
        output = arguments.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8", newline="\n")
        if not arguments.quiet:
            print(output)
    else:
        print(rendered, end="")
    return report.exit_code


def _inspect(arguments: argparse.Namespace) -> int:
    evidence = arguments.evidence.expanduser().resolve()
    manifest_path = evidence / "manifest.json" if evidence.is_dir() else evidence
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"evidence manifest does not exist: {manifest_path}") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"evidence manifest is not valid UTF-8 JSON: {exc}") from exc
    manifest = _json_object(raw)
    expected = manifest.get("semantic_digest")
    semantic = {
        key: value for key, value in manifest.items() if key not in {"semantic_digest", "verdict"}
    }
    if not isinstance(expected, str) or digest_report_payload(semantic) != expected:
        raise EvidenceError("evidence semantic digest is missing or invalid")
    verbosity = "quiet" if arguments.quiet else "verbose" if arguments.verbose else "normal"
    print(
        render_manifest(
            manifest,
            arguments.format,
            color=_use_color(arguments.color, arguments.format),
            verbosity=verbosity,
        ),
        end="",
    )
    return 0


def _json_object(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise EvidenceError("evidence manifest root must be an object")
    converted = _json_value(value)
    assert isinstance(converted, dict)
    return converted


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise EvidenceError("evidence manifest contains a non-string object key")
        return {str(key): _json_value(item) for key, item in value.items()}
    raise EvidenceError(f"evidence manifest contains unsupported value {type(value).__name__}")


def _use_color(setting: str, format_name: str) -> bool:
    if format_name != "terminal" or "NO_COLOR" in os.environ:
        return False
    if setting == "always":
        return True
    if setting == "never":
        return False
    return sys.stdout.isatty()


if __name__ == "__main__":
    raise SystemExit(main())
