"""Dependency-free command-line interface for MCP Behavior."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .contract import ContractError, load_contract
from .core import record, verify
from .evidence import EvidenceError, digest_report_payload
from .execution import ExecutionError
from .models import JsonValue
from .reports import render_manifest, render_report, write_rendered_report
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
        description="Deterministic regression tests for what MCP tools actually do.",
    )
    parser.add_argument("--version", action="version", version="mcp-behavior 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="write a strict starter contract")
    init_parser.add_argument("path", nargs="?", default="mcp-behavior.yaml", type=Path)
    init_parser.add_argument("--force", action="store_true", help="replace an existing file")
    init_parser.set_defaults(handler=_init)

    record_parser = subparsers.add_parser("record", help="record a candidate baseline")
    _selection_arguments(record_parser)
    record_parser.add_argument("contract", type=Path)
    record_parser.add_argument("--output", "-o", type=Path)
    record_parser.set_defaults(handler=_record)

    verify_parser = subparsers.add_parser("verify", help="verify expectations or a baseline")
    _verification_arguments(verify_parser)
    verify_parser.set_defaults(handler=_verify)

    diff_parser = subparsers.add_parser("diff", help="compare candidate and reference targets")
    _verification_arguments(diff_parser)
    diff_parser.set_defaults(handler=_diff)

    inspect_parser = subparsers.add_parser("inspect", help="inspect deterministic evidence")
    inspect_parser.add_argument("evidence", type=Path)
    inspect_parser.add_argument("--format", choices=("terminal", "json"), default="terminal")
    inspect_parser.set_defaults(handler=_inspect)
    return parser


def _selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", action="append", default=[], help="select a scenario name")
    parser.add_argument("--tag", action="append", default=[], help="select scenarios by tag")


def _verification_arguments(parser: argparse.ArgumentParser) -> None:
    _selection_arguments(parser)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--evidence", type=Path, default=Path(".mcp-behavior/evidence"))
    parser.add_argument("--format", choices=REPORT_FORMATS, default="terminal")
    parser.add_argument("--output", "-o", type=Path, help="write the rendered report to a file")


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
    rendered = render_report(report, arguments.format)
    if arguments.output:
        output = write_rendered_report(report, arguments.format, arguments.output)
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
    print(render_manifest(manifest, arguments.format), end="")
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


if __name__ == "__main__":
    raise SystemExit(main())
