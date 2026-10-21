"""Reproduce upstream filesystem PR #5011 with two explicitly installed servers."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from mcp_behavior import verify
from mcp_behavior.models import Verdict
from mcp_behavior.reports import render_report

BEFORE_VERSION = "2026.8.31"
AFTER_VERSION = "2.0.0"
EXPECTED = b"c\r\nb\r\n"


def contract(workspace: Path, server: Path, node: str, *, observe: bool) -> dict[str, object]:
    """Use the public contract format; the observer checks bytes decoded as UTF-8."""
    scenario: dict[str, object] = {
        "name": "edit preserves CRLF",
        "calls": [
            {
                "tool": "edit_file",
                "arguments": {
                    "path": str(workspace / "crlf.txt"),
                    "edits": [{"oldText": "a", "newText": "c"}],
                },
                "expect": {"outcome": "success"},
            }
        ],
    }
    if observe:
        scenario["observers"] = [
            {
                "name": "preserved line endings",
                "kind": "file",
                "root": ".",
                "path": "crlf.txt",
                "phase": "after",
                "expect": {"contains": {"state": "present", "text": EXPECTED.decode()}},
            }
        ]
    return {
        "version": 1,
        "name": "official-filesystem-crlf",
        "targets": {
            "candidate": {
                "transport": "stdio",
                "mode": "legacy",
                "command": [node, str(server), str(workspace)],
                "cwd": str(workspace),
                "workspace": str(workspace),
            }
        },
        "scenarios": [scenario],
    }


def installed_version(server: Path) -> str:
    package = json.loads((server.parent.parent / "package.json").read_text(encoding="utf-8"))
    if package["name"] != "@modelcontextprotocol/server-filesystem":
        raise ValueError("Expected the official filesystem package")
    return str(package["version"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True, help="2026.8.31 dist/index.js")
    parser.add_argument("--after", type=Path, required=True, help="2.0.0 dist/index.js")
    parser.add_argument("--evidence", type=Path, required=True, help="new evidence directory")
    args = parser.parse_args()
    before, after = args.before.resolve(strict=True), args.after.resolve(strict=True)
    if (installed_version(before), installed_version(after)) != (BEFORE_VERSION, AFTER_VERSION):
        raise ValueError("Install the exact before/after versions documented in this example")
    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js is required")
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    print("Official filesystem edit_file: a fixed historical regression", flush=True)
    print('Requested: replace a with c; preserve CRLF ("c\\r\\nb\\r\\n").', flush=True)
    print("Upstream fix: modelcontextprotocol/servers#5011\n", flush=True)
    stages = (
        ("response-only", before, False, b"c\nb\n", Verdict.MATCH),
        ("state-observed", before, True, b"c\nb\n", Verdict.DIVERGE),
        ("fixed-control", after, True, EXPECTED, Verdict.MATCH),
    )
    results = []
    diffs: list[object] = []
    with tempfile.TemporaryDirectory(prefix="mcp-crlf-") as temporary:
        workspace = Path(temporary)
        for name, server, observe, expected_bytes, expected_verdict in stages:
            (workspace / "crlf.txt").write_bytes(b"a\r\nb\r\n")
            path = workspace / "contract.json"
            path.write_text(json.dumps(contract(workspace, server, node, observe=observe)))
            report = verify(path, evidence / name)
            (evidence / f"{name}.md").write_text(
                render_report(report, "markdown"), encoding="utf-8", newline="\n"
            )
            actual = (workspace / "crlf.txt").read_bytes()  # Independent byte-level control.
            case = report.scenarios[0]
            if (
                report.verdict != expected_verdict
                or case.calls[0].verdict != Verdict.MATCH
                or actual != expected_bytes
                or (observe and case.effects[0].verdict != expected_verdict)
            ):
                raise RuntimeError(f"Unexpected {name} result: {report.to_dict()}")
            response = case.calls[0].candidate
            if not isinstance(response, dict):
                raise RuntimeError("Missing tool response")
            diffs.append(response.get("content"))
            version = installed_version(server)
            print(f"{report.verdict:12} {version:12} {name}", flush=True)
            print(f"  tool: success; actual bytes: {actual.hex(' ')}", flush=True)
            results.append(
                {
                    "stage": name,
                    "version": version,
                    "verdict": str(report.verdict),
                    "call_verdict": str(case.calls[0].verdict),
                    "actual_hex": actual.hex(" "),
                    "server_entrypoint_sha256": hashlib.sha256(server.read_bytes()).hexdigest(),
                }
            )
    if diffs[0] != diffs[1] or diffs[1] != diffs[2]:
        raise RuntimeError("The tool content differed; inspect evidence before making claims")
    print("\nSame successful edit diff in all three runs. Different file bytes.", flush=True)
    print("MATCH -> DIVERGE -> MATCH; independent read_bytes() checks passed.", flush=True)
    print("A direct SDK test with the same byte assertion catches this too.", flush=True)
    summary = {
        "case": "official filesystem CRLF preservation",
        "upstream_fix": "https://github.com/modelcontextprotocol/servers/pull/5011",
        "expected_hex": EXPECTED.hex(" "),
        "same_tool_content": True,
        "independent_byte_checks": "passed",
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "node_version": subprocess.check_output([node, "--version"], text=True).strip(),
        "tool_content": json.loads(
            json.dumps(diffs[0]).replace(str(workspace).replace("\\", "\\\\"), "<workspace>")
        ),
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "runs": results,
    }
    (evidence / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
