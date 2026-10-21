from __future__ import annotations

import json
from pathlib import Path

from mcp_behavior.cli import main
from mcp_behavior.contract import load_contract


def test_init_writes_a_valid_expectations_contract(tmp_path: Path) -> None:
    output = tmp_path / "behavior.yaml"
    assert main(["init", str(output)]) == 0
    contract = load_contract(output)
    assert contract.name == "my-mcp-server"
    assert contract.mode == "expectations"


def test_init_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    output = tmp_path / "behavior.yaml"
    output.write_text("mine", encoding="utf-8")
    assert main(["init", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "mine"


def test_demo_runs_real_checks_and_preserves_existing_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "demo evidence"
    assert main(["demo", "--evidence", str(evidence)]) == 0
    manifests = {
        name: json.loads((evidence / name / "manifest.json").read_text(encoding="utf-8"))
        for name in ("response-only", "state-observed", "fixed-control")
    }
    assert [report["verdict"] for report in manifests.values()] == ["MATCH", "DIVERGE", "MATCH"]
    assert all(
        report["scenarios"][0]["calls"][0]["verdict"] == "MATCH" for report in manifests.values()
    )
    assert manifests["response-only"]["scenarios"][0]["effects"] == []
    effects = manifests["state-observed"]["scenarios"][0]["effects"]
    assert effects[0]["verdict"] == "DIVERGE"
    assert effects[0]["candidate"]["after"]["text"] == '{"invoice_id":"inv-42","total":109}\n'
    fixed_effects = manifests["fixed-control"]["scenarios"][0]["effects"]
    assert fixed_effects[0]["verdict"] == "MATCH"
    assert fixed_effects[0]["candidate"]["after"]["text"] == (
        '{"invoice_id":"inv-42","total":100}\n'
    )
    before = (evidence / "state-observed" / "manifest.json").read_bytes()
    assert main(["demo", "--evidence", str(evidence)]) == 2
    assert (evidence / "state-observed" / "manifest.json").read_bytes() == before
