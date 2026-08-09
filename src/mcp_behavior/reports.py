"""Stable human and machine report renderers."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

from .models import JsonValue, Verdict, VerificationReport


def render_report(report: VerificationReport, format_name: str) -> str:
    """Render a verification report without changing its semantic payload."""

    if format_name == "terminal":
        return _terminal(report)
    if format_name == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if format_name == "markdown":
        return _markdown(report)
    if format_name == "junit":
        return _junit(report)
    raise ValueError(f"unknown report format {format_name!r}")


def write_rendered_report(report: VerificationReport, format_name: str, path: Path) -> Path:
    output = path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(report, format_name), encoding="utf-8", newline="\n")
    return output


def render_manifest(manifest: dict[str, JsonValue], format_name: str) -> str:
    """Render a previously written evidence manifest for inspection."""

    if format_name == "json":
        return json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if format_name != "terminal":
        raise ValueError("inspect format must be terminal or json")
    scenarios = manifest.get("scenarios")
    lines = [
        f"{manifest.get('contract_name', '<unknown>')} — {manifest.get('verdict', '<unknown>')}",
        f"mode: {manifest.get('mode', '<unknown>')}",
        f"digest: {manifest.get('semantic_digest', '<missing>')}",
    ]
    if isinstance(scenarios, list):
        for scenario in scenarios:
            if isinstance(scenario, dict):
                lines.append(f"  {scenario.get('verdict', '?'):12} {scenario.get('name', '?')}")
    return "\n".join(lines) + "\n"


def _terminal(report: VerificationReport) -> str:
    lines = [
        f"MCP Behavior: {report.verdict}",
        f"mode: {report.mode}",
        f"digest: {report.semantic_digest}",
    ]
    for scenario in report.scenarios:
        lines.append(f"\n{scenario.verdict:12} {scenario.name}")
        if scenario.error:
            lines.append(f"  error: {scenario.error}")
        for call in scenario.calls:
            lines.append(f"  {call.verdict:12} call {call.name} ({call.tool})")
            lines.extend(f"    {item.path}: {item.message}" for item in call.differences)
        for effect in scenario.effects:
            lines.append(f"  {effect.verdict:12} effect {effect.name} ({effect.kind})")
            lines.extend(f"    {item.path}: {item.message}" for item in effect.differences)
    lines.append(f"\nevidence: {report.evidence_dir}")
    return "\n".join(lines) + "\n"


def _markdown(report: VerificationReport) -> str:
    lines = [
        "# MCP Behavior report",
        "",
        f"**Verdict:** `{report.verdict}`  ",
        f"**Mode:** `{report.mode}`  ",
        f"**Semantic digest:** `{report.semantic_digest}`",
        "",
        "| Scenario | Verdict | Calls | Effects |",
        "|---|---:|---:|---:|",
    ]
    for scenario in report.scenarios:
        lines.append(
            f"| {scenario.name} | `{scenario.verdict}` | {len(scenario.calls)} | "
            f"{len(scenario.effects)} |"
        )
    for scenario in report.scenarios:
        differences = [
            (f"call `{call.name}`", item.path, item.message)
            for call in scenario.calls
            for item in call.differences
        ]
        differences.extend(
            (f"effect `{effect.name}`", item.path, item.message)
            for effect in scenario.effects
            for item in effect.differences
        )
        if scenario.error or differences:
            lines.extend(["", f"## {scenario.name}", ""])
            if scenario.error:
                lines.append(f"Error: {scenario.error}")
            for subject, path, message in differences:
                lines.append(f"- {subject} at `{path}`: {message}")
    return "\n".join(lines) + "\n"


def _junit(report: VerificationReport) -> str:
    failures = sum(scenario.verdict is Verdict.DIVERGE for scenario in report.scenarios)
    skipped = sum(scenario.verdict is Verdict.INCONCLUSIVE for scenario in report.scenarios)
    suite = ElementTree.Element(
        "testsuite",
        {
            "name": "mcp-behavior",
            "tests": str(len(report.scenarios)),
            "failures": str(failures),
            "errors": "0",
            "skipped": str(skipped),
            "time": f"{report.duration_ms / 1000:.3f}",
        },
    )
    suite.set("mcp_behavior_digest", report.semantic_digest)
    for scenario in report.scenarios:
        case = ElementTree.SubElement(
            suite,
            "testcase",
            {
                "classname": "mcp-behavior",
                "name": scenario.name,
                "time": f"{scenario.duration_ms / 1000:.3f}",
            },
        )
        detail = _scenario_detail(scenario)
        if scenario.verdict is Verdict.DIVERGE:
            ElementTree.SubElement(case, "failure", {"message": "behavior diverged"}).text = detail
        elif scenario.verdict is Verdict.INCONCLUSIVE:
            ElementTree.SubElement(
                case, "skipped", {"message": "verification inconclusive"}
            ).text = detail
    ElementTree.indent(suite)
    return ElementTree.tostring(suite, encoding="unicode", xml_declaration=True) + "\n"


def _scenario_detail(scenario: object) -> str:
    # Kept local to JUnit so report text never changes semantic evidence.
    from .models import ScenarioReport

    assert isinstance(scenario, ScenarioReport)
    lines = [scenario.error] if scenario.error else []
    for call in scenario.calls:
        lines.extend(
            f"{call.name} {difference.path}: {difference.message}"
            for difference in call.differences
        )
    for effect in scenario.effects:
        lines.extend(
            f"{effect.name} {difference.path}: {difference.message}"
            for difference in effect.differences
        )
    return "\n".join(lines) or str(scenario.verdict)
