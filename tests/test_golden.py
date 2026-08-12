from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_behavior.cli import main
from mcp_behavior.evidence import digest_report_payload, semantic_report_payload, write_evidence
from mcp_behavior.models import (
    CallReport,
    Difference,
    ScenarioReport,
    Verdict,
    VerificationReport,
)
from mcp_behavior.normalization import semantic_digest
from mcp_behavior.reports import render_report

GOLDEN = Path(__file__).parent / "golden"


def _report(tmp_path: Path) -> VerificationReport:
    scenario = ScenarioReport(
        name="value drift",
        verdict=Verdict.DIVERGE,
        calls=(
            CallReport(
                name="lookup",
                tool="lookup",
                verdict=Verdict.DIVERGE,
                arguments={"user_id": "user-42"},
                differences=(Difference("$.status", "values differ", "active", "suspended"),),
                candidate={"status": "suspended"},
                reference={"status": "active"},
            ),
        ),
    )
    payload = semantic_report_payload("golden", "differential", (scenario,))
    return VerificationReport(
        contract=str(tmp_path / "contract.yaml"),
        mode="differential",
        verdict=Verdict.DIVERGE,
        scenarios=(scenario,),
        semantic_digest=digest_report_payload(payload),
        evidence_dir=str(tmp_path / "evidence"),
    )


def test_terminal_report_matches_golden(tmp_path: Path) -> None:
    report = _report(tmp_path)
    actual = render_report(report, "terminal").replace(report.evidence_dir, "<evidence>")
    assert actual == (GOLDEN / "terminal-diverge.txt").read_text(encoding="utf-8")


def test_evidence_manifest_and_cli_inspect_match_goldens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _report(tmp_path)
    evidence = write_evidence(report, "golden", {})

    assert (evidence / "manifest.json").read_text(encoding="utf-8") == (
        GOLDEN / "evidence-manifest.json"
    ).read_text(encoding="utf-8")
    assert sorted(path.relative_to(evidence).as_posix() for path in evidence.rglob("*")) == [
        "manifest.json",
        "run.json",
        "scenarios",
        "scenarios/001-value-drift",
        "scenarios/001-value-drift/comparison.json",
        "scenarios/001-value-drift/effects.json",
        "scenarios/001-value-drift/logs.txt",
        "scenarios/001-value-drift/observation.json",
    ]
    observation = json.loads(
        (evidence / "scenarios/001-value-drift/observation.json").read_text(encoding="utf-8")
    )
    assert observation["calls"][0]["request"] == {"user_id": "user-42"}
    assert observation["calls"][0]["candidate_sha256"] == semantic_digest({"status": "suspended"})
    run = json.loads((evidence / "run.json").read_text(encoding="utf-8"))
    assert run["observation_durations_ms"]["value drift"]["calls"]["lookup"] == 0

    assert main(["inspect", str(evidence), "--color", "never"]) == 0
    output = capsys.readouterr().out
    assert output == (GOLDEN / "inspect.txt").read_text(encoding="utf-8")


def test_no_color_environment_overrides_forced_cli_color(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _report(tmp_path)
    evidence = write_evidence(report, "golden", {})
    monkeypatch.setenv("NO_COLOR", "1")

    assert main(["inspect", str(evidence), "--quiet", "--color", "always"]) == 0

    assert capsys.readouterr().out == "DIVERGE\n"
