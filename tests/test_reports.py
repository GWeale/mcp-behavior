from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

from mcp_behavior.evidence import digest_report_payload, semantic_report_payload
from mcp_behavior.models import (
    CallReport,
    Difference,
    EffectReport,
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


def test_terminal_supports_first_diff_quiet_verbose_and_color(tmp_path: Path) -> None:
    report = _report(tmp_path)
    call = report.scenarios[0].calls[0]
    expanded = replace(
        report,
        scenarios=(
            ScenarioReport(
                name="echo",
                verdict=Verdict.DIVERGE,
                calls=(
                    CallReport(
                        name=call.name,
                        tool=call.tool,
                        verdict=call.verdict,
                        differences=(
                            *call.differences,
                            Difference("$.other", "candidate key is missing", 1, None),
                        ),
                        candidate={"message": "b"},
                        reference={"message": "a"},
                        duration_ms=7,
                    ),
                ),
                duration_ms=9,
            ),
        ),
        duration_ms=11,
    )

    first = render_report(expanded, "terminal", difference_limit=1)
    first_markdown = render_report(expanded, "markdown", difference_limit=1)
    quiet = render_report(expanded, "terminal", verbosity="quiet", color=True)
    verbose = render_report(expanded, "terminal", verbosity="verbose")

    assert "$.message" in first and "$.other" not in first
    assert "1 more difference" in first
    assert "$.message" in first_markdown and "$.other" not in first_markdown
    assert "1 more difference" in first_markdown
    assert quiet == "\x1b[31mDIVERGE\x1b[0m\n"
    assert "duration: 11 ms" in verbose
    assert 'reference: {"message":"a"}' in verbose


def test_semantic_digest_excludes_all_runtime_durations() -> None:
    first = ScenarioReport(
        name="effect",
        verdict=Verdict.MATCH,
        calls=(CallReport("call", "tool", Verdict.MATCH, duration_ms=1),),
        effects=(EffectReport("file", "file", Verdict.MATCH, duration_ms=2),),
        duration_ms=3,
    )
    second = ScenarioReport(
        name="effect",
        verdict=Verdict.MATCH,
        calls=(CallReport("call", "tool", Verdict.MATCH, duration_ms=100),),
        effects=(EffectReport("file", "file", Verdict.MATCH, duration_ms=200),),
        duration_ms=300,
    )

    first_digest = digest_report_payload(
        semantic_report_payload("contract", "expectations", (first,))
    )
    second_digest = digest_report_payload(
        semantic_report_payload("contract", "expectations", (second,))
    )

    assert first_digest == second_digest
