"""Stable human and machine report renderers."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

from .models import Difference, JsonValue, Verdict, VerificationReport


def render_report(
    report: VerificationReport,
    format_name: str,
    *,
    color: bool = False,
    difference_limit: int | None = None,
    verbosity: str = "normal",
) -> str:
    """Render a verification report without changing its semantic payload."""

    if format_name == "terminal":
        return _terminal(
            report,
            color=color,
            difference_limit=difference_limit,
            verbosity=verbosity,
        )
    if format_name == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if format_name == "markdown":
        return _markdown(report, difference_limit=difference_limit)
    if format_name == "junit":
        return _junit(report)
    raise ValueError(f"unknown report format {format_name!r}")


def write_rendered_report(report: VerificationReport, format_name: str, path: Path) -> Path:
    output = path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(report, format_name), encoding="utf-8", newline="\n")
    return output


def render_manifest(
    manifest: dict[str, JsonValue],
    format_name: str,
    *,
    color: bool = False,
    verbosity: str = "normal",
) -> str:
    """Render a previously written evidence manifest for inspection."""

    if format_name == "json":
        return json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if format_name != "terminal":
        raise ValueError("inspect format must be terminal or json")
    if verbosity == "quiet":
        return _paint(str(manifest.get("verdict", "<unknown>")), color) + "\n"
    scenarios = manifest.get("scenarios")
    lines = [
        f"{manifest.get('contract_name', '<unknown>')} — "
        f"{_paint(str(manifest.get('verdict', '<unknown>')), color)}",
        f"mode: {manifest.get('mode', '<unknown>')}",
        f"digest: {manifest.get('semantic_digest', '<missing>')}",
    ]
    if isinstance(scenarios, list):
        for scenario in scenarios:
            if isinstance(scenario, dict):
                verdict = str(scenario.get("verdict", "?"))
                lines.append(f"  {_paint(f'{verdict:12}', color)} {scenario.get('name', '?')}")
                if verbosity == "verbose":
                    lines.append(f"    error: {scenario.get('error') or '<none>'}")
    return "\n".join(lines) + "\n"


def _terminal(
    report: VerificationReport,
    *,
    color: bool,
    difference_limit: int | None,
    verbosity: str,
) -> str:
    if verbosity == "quiet":
        return _paint(str(report.verdict), color) + "\n"
    lines = [
        f"MCP Behavior: {_paint(str(report.verdict), color)}",
        f"mode: {report.mode}",
        f"digest: {report.semantic_digest}",
    ]
    if verbosity == "verbose":
        lines.append(f"duration: {report.duration_ms} ms")
    for scenario in report.scenarios:
        lines.append(f"\n{_paint(f'{scenario.verdict:12}', color)} {scenario.name}")
        if verbosity == "verbose":
            lines.append(f"  duration: {scenario.duration_ms} ms")
        if scenario.error:
            lines.append(f"  error: {scenario.error}")
        for call in scenario.calls:
            lines.append(f"  {_paint(f'{call.verdict:12}', color)} call {call.name} ({call.tool})")
            _append_differences(lines, call.differences, difference_limit)
            if verbosity == "verbose":
                lines.append(f"    duration: {call.duration_ms} ms")
                lines.append(f"    reference: {_display(call.reference)}")
                lines.append(f"    candidate: {_display(call.candidate)}")
        for effect in scenario.effects:
            lines.append(
                f"  {_paint(f'{effect.verdict:12}', color)} effect {effect.name} ({effect.kind})"
            )
            _append_differences(lines, effect.differences, difference_limit)
            if verbosity == "verbose":
                lines.append(f"    duration: {effect.duration_ms} ms")
                lines.append(f"    reference: {_display(effect.reference)}")
                lines.append(f"    candidate: {_display(effect.candidate)}")
    lines.append(f"\nevidence: {report.evidence_dir}")
    return "\n".join(lines) + "\n"


def _append_differences(
    lines: list[str], differences: tuple[Difference, ...], difference_limit: int | None
) -> None:
    shown = differences if difference_limit is None else differences[:difference_limit]
    lines.extend(f"    {item.path}: {item.message}" for item in shown)
    hidden = len(differences) - len(shown)
    if hidden:
        lines.append(f"    … {hidden} more difference(s); use --diff-detail full")


def _display(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _paint(value: str, enabled: bool) -> str:
    if not enabled:
        return value
    verdict = value.strip()
    code = {"MATCH": "32", "DIVERGE": "31", "INCONCLUSIVE": "33"}.get(verdict)
    return f"\x1b[{code}m{value}\x1b[0m" if code is not None else value


def _markdown(report: VerificationReport, *, difference_limit: int | None) -> str:
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
            shown = differences if difference_limit is None else differences[:difference_limit]
            for subject, path, message in shown:
                lines.append(f"- {subject} at `{path}`: {message}")
            hidden = len(differences) - len(shown)
            if hidden:
                lines.append(f"- {hidden} more difference(s); use `--diff-detail full`")
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
