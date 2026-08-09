from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

from mcp_behavior.models import (
    CallReport,
    Difference,
    ScenarioReport,
    Verdict,
    VerificationReport,
)
from mcp_behavior.reports import render_report, write_rendered_report


def _report(tmp_path: Path) -> VerificationReport:
    return VerificationReport(
        contract=str(tmp_path / "contract.yaml"),
        mode="baseline",
        verdict=Verdict.DIVERGE,
        scenarios=(
            ScenarioReport(
                name="echo",
                verdict=Verdict.DIVERGE,
                calls=(
                    CallReport(
                        name="echo once",
                        tool="echo",
                        verdict=Verdict.DIVERGE,
                        differences=(Difference("$.message", "values differ", "a", "b"),),
                    ),
                ),
            ),
        ),
        semantic_digest="abc123",
        evidence_dir=str(tmp_path / "evidence"),
    )


def test_all_report_formats_are_machine_or_human_readable(tmp_path: Path) -> None:
    report = _report(tmp_path)
    terminal = render_report(report, "terminal")
    markdown = render_report(report, "markdown")
    json_report = json.loads(render_report(report, "json"))
    junit = ElementTree.fromstring(render_report(report, "junit"))

    assert "DIVERGE" in terminal and "$.message" in terminal
    assert "| echo | `DIVERGE`" in markdown
    assert json_report["semantic_digest"] == "abc123"
    assert junit.attrib["failures"] == "1"
    assert junit.find("testcase/failure") is not None


def test_rendered_report_write_is_utf8(tmp_path: Path) -> None:
    output = write_rendered_report(_report(tmp_path), "markdown", tmp_path / "out" / "report.md")
    assert output.read_text(encoding="utf-8").startswith("# MCP Behavior report")
