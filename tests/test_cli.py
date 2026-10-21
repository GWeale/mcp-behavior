from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from mcp_behavior import Verdict, verify
from mcp_behavior.cli import main
from mcp_behavior.contract import load_contract


def test_init_writes_a_valid_expectations_contract(tmp_path: Path) -> None:
    output = tmp_path / "behavior.yaml"
    assert main(["init", str(output)]) == 0
    contract = load_contract(output)
    assert contract.name == "my-mcp-server"
    assert contract.mode == "expectations"


@pytest.mark.parametrize(
    "template,kind", [("file", "file"), ("sqlite", "sqlite"), ("response", None)]
)
def test_init_selects_valid_state_templates(
    tmp_path: Path, template: str, kind: str | None
) -> None:
    output = tmp_path / "behavior.yaml"
    assert main(["init", str(output), "--template", template]) == 0
    contract = load_contract(output)
    observers = contract.scenarios[0].observers
    assert [observer.kind for observer in observers] == ([kind] if kind else [])


def test_default_starter_catches_wrong_file_after_successful_call(tmp_path: Path) -> None:
    output = tmp_path / "behavior.yaml"
    assert main(["init", str(output)]) == 0
    document = yaml.safe_load(output.read_text(encoding="utf-8"))
    document["targets"]["candidate"].update(
        command=[sys.executable, str(Path(__file__).parent / "fixtures" / "server.py")],
        cwd=str(tmp_path),
        workspace=str(tmp_path),
    )
    scenario = document["scenarios"][0]
    scenario["calls"][0].update(tool="write_note", arguments={"content": "expected contents\n"})
    scenario["observers"][0]["path"] = "note.txt"
    output.write_text(yaml.safe_dump(document), encoding="utf-8")
    good = verify(output, tmp_path / "good")
    assert good.verdict is Verdict.MATCH
    scenario["calls"][0]["arguments"]["content"] = "wrong contents\n"
    output.write_text(yaml.safe_dump(document), encoding="utf-8")
    bad = verify(output, tmp_path / "bad")
    assert bad.verdict is Verdict.DIVERGE
    assert bad.scenarios[0].calls[0].verdict is Verdict.MATCH
    assert bad.scenarios[0].effects[0].verdict is Verdict.DIVERGE


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
