"""A self-contained first run through the public verification interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .core import verify
from .models import Verdict


def run_demo(evidence_dir: Path | None = None) -> int:
    """Execute real fixture checks, returning success only for the expected sequence."""
    retained = evidence_dir.expanduser().resolve() if evidence_dir is not None else None
    if retained is not None:
        retained.mkdir(parents=True, exist_ok=False)

    print("MCP Behavior demo: an intentional invoice regression")
    print("Requested total: 100. Both implementations return saved: true.\n")
    with TemporaryDirectory(prefix="mcp-behavior-demo-") as temporary:
        root = Path(temporary)
        evidence = retained if retained is not None else root / "evidence"
        stages = (
            ("response-only", "response only", False, 9, 109, Verdict.MATCH),
            ("state-observed", "response + file state", True, 9, 109, Verdict.DIVERGE),
            ("fixed-control", "corrected implementation", True, 0, 100, Verdict.MATCH),
        )
        for name, label, observe, offset, expected_total, expected in stages:
            workspace = root / name
            workspace.mkdir()
            contract = workspace / "mcp-behavior.yaml"
            contract.write_text(
                json.dumps(_contract(workspace, observe=observe, offset=offset), indent=2),
                encoding="utf-8",
                newline="\n",
            )
            report = verify(contract, evidence / name)
            calls = tuple(call.verdict for item in report.scenarios for call in item.calls)
            effects = tuple(effect.verdict for item in report.scenarios for effect in item.effects)
            expected_effects = (expected,) if observe else ()
            if (
                report.verdict is not expected
                or len(report.scenarios) != 1
                or calls != (Verdict.MATCH,)
                or effects != expected_effects
            ):
                print(f"{report.verdict:12} {label}; expected {expected}")
                for scenario in report.scenarios:
                    if scenario.error:
                        print(f"  {scenario.error}")
                print("Demo did not produce the expected results.")
                return 2
            actual = json.loads((workspace / "invoice.json").read_text(encoding="utf-8"))
            if actual != {"invoice_id": "inv-42", "total": expected_total}:
                print(f"Unexpected invoice state for {label}; expected total {expected_total}.")
                return 2
            print(f"{report.verdict:12} {label}: file total = {actual['total']}")

    print("\nDemo passed: MATCH -> DIVERGE -> MATCH.")
    print("A direct SDK test with a file assertion can detect this fixture too.")
    if retained is not None:
        print(f"Evidence: {retained}")
    else:
        print("Temporary workspaces and evidence were removed.")
    return 0


def _contract(workspace: Path, *, observe: bool, offset: int) -> dict[str, object]:
    scenario: dict[str, object] = {
        "name": "success response must match the written invoice",
        "calls": [
            {
                "name": "export invoice",
                "tool": "export_invoice",
                "arguments": {"invoice_id": "inv-42", "total": 100},
                "normalize": {
                    "ignore": ["$.content", "$._meta['io.modelcontextprotocol/serverInfo']"]
                },
                "expect": {
                    "outcome": "success",
                    "paths_equal": {
                        "$.structuredContent.saved": True,
                        "$.structuredContent.invoice_id": "inv-42",
                    },
                },
            }
        ],
    }
    if observe:
        scenario["observers"] = [
            {
                "name": "invoice file",
                "kind": "file",
                "root": ".",
                "path": "invoice.json",
                "phase": "delta",
                "expect": {
                    "contains": {
                        "change": "created",
                        "after": {
                            "state": "present",
                            "encoding": "utf-8",
                            "text": '{"invoice_id":"inv-42","total":100}\n',
                        },
                    }
                },
            }
        ]
    return {
        "version": 1,
        "name": "invoice-demo",
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [sys.executable, "-m", "mcp_behavior._demo_server", str(offset)],
                "cwd": str(workspace),
                "workspace": str(workspace),
            }
        },
        "scenarios": [scenario],
    }
