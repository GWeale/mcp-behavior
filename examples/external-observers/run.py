"""Run both external invoice observers against a disposable local MCP fixture."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import yaml

from mcp_behavior import verify


def contract_document(workspace: Path, drift: int = 0) -> dict[str, object]:
    example = Path(__file__).resolve().parent
    expected = {
        "version": 1,
        "state": "present",
        "columns": ["invoice_id", "total_cents"],
        "rows": [["inv-42", 10000]],
    }
    return {
        "version": 1,
        "name": "external invoice projections",
        "timeouts": {"connect": 30, "operation": 15, "total": 90},
        "limits": {"output_bytes": 65_536, "log_bytes": 131_072},
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [sys.executable, str(example / "server.py")],
                "cwd": str(workspace),
                "workspace": str(workspace),
                "env": {"EXAMPLE_DRIFT": str(drift)},
            }
        },
        "scenarios": [
            {
                "name": "invoice projections",
                "calls": [
                    {
                        "tool": "save_invoice",
                        "arguments": {"total_cents": 10000},
                        "expect": {"outcome": "success"},
                    }
                ],
                "observers": [
                    {
                        "name": f"{kind} invoice projection",
                        "kind": "command",
                        "command": [sys.executable, str(example / f"{kind}_probe.py")],
                        "expect": {"equals": json.loads(json.dumps(expected))},
                    }
                    for kind in ("json", "sqlite")
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--write-drift", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mcp-external-probes-") as temporary:
        root = Path(temporary)
        contract = root / "contract.yaml"
        contract.write_text(
            yaml.safe_dump(contract_document(root, 9 if args.write_drift else 0), sort_keys=False),
            encoding="utf-8",
        )
        report = verify(contract, args.evidence.resolve())
    print(
        json.dumps(
            {
                "verdict": report.verdict.value,
                "effects": [effect.verdict.value for effect in report.scenarios[0].effects],
            }
        )
    )
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
