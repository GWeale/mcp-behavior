"""Canonical, sanitized evidence serialization."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import JsonValue, ScenarioReport, VerificationReport
from .normalization import semantic_digest

EVIDENCE_SCHEMA_VERSION = 1
BASELINE_SCHEMA_VERSION = 1


class EvidenceError(RuntimeError):
    pass


def semantic_report_payload(
    contract_name: str,
    mode: str,
    scenarios: tuple[ScenarioReport, ...],
) -> dict[str, JsonValue]:
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "contract_name": contract_name,
        "mode": mode,
        "scenarios": [_scenario_semantic(scenario) for scenario in scenarios],
    }


def digest_report_payload(payload: dict[str, JsonValue]) -> str:
    return semantic_digest(payload)


def write_evidence(
    report: VerificationReport,
    contract_name: str,
    logs: dict[str, str],
) -> Path:
    root = _prepare_root(Path(report.evidence_dir), Path(report.contract))
    semantic = semantic_report_payload(contract_name, report.mode, report.scenarios)
    digest = digest_report_payload(semantic)
    if digest != report.semantic_digest:
        raise EvidenceError("report semantic digest does not match its scenario payload")

    manifest: dict[str, Any] = {
        **semantic,
        "semantic_digest": digest,
        "verdict": report.verdict,
    }
    run: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "contract": report.contract,
        "duration_ms": report.duration_ms,
        "warnings": list(report.warnings),
        "scenario_durations_ms": {
            scenario.name: scenario.duration_ms for scenario in report.scenarios
        },
    }
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "run.json", run)

    scenarios_root = root / "scenarios"
    scenarios_root.mkdir()
    for index, scenario in enumerate(report.scenarios, start=1):
        scenario_root = scenarios_root / f"{index:03d}-{_slug(scenario.name)}"
        scenario_root.mkdir()
        observations = {
            "calls": [
                {
                    "name": call.name,
                    "tool": call.tool,
                    "candidate": call.candidate,
                    "reference": call.reference,
                }
                for call in scenario.calls
            ]
        }
        comparisons = {
            "verdict": scenario.verdict,
            "error": scenario.error,
            "calls": [
                {
                    "name": call.name,
                    "verdict": call.verdict,
                    "differences": [asdict(item) for item in call.differences],
                }
                for call in scenario.calls
            ],
        }
        effects = {
            "effects": [asdict(effect) for effect in scenario.effects],
        }
        _write_json(scenario_root / "observation.json", observations)
        _write_json(scenario_root / "comparison.json", comparisons)
        _write_json(scenario_root / "effects.json", effects)
        (scenario_root / "logs.txt").write_text(
            logs.get(scenario.name, ""),
            encoding="utf-8",
            newline="\n",
        )
    return root


def write_baseline(path: Path, contract_name: str, scenarios: JsonValue) -> str:
    payload: dict[str, JsonValue] = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "contract_name": contract_name,
        "scenarios": scenarios,
    }
    digest = semantic_digest(payload)
    document: dict[str, Any] = {**payload, "semantic_digest": digest}
    _write_json(path, document)
    return digest


def read_baseline(path: Path) -> dict[str, JsonValue]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"baseline does not exist: {path}") from exc
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise EvidenceError(f"baseline is not valid UTF-8 JSON: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise EvidenceError("baseline root must be an object")
    digest = raw.pop("semantic_digest", None)
    if not isinstance(digest, str) or semantic_digest(raw) != digest:
        raise EvidenceError("baseline semantic digest is missing or invalid")
    if raw.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise EvidenceError(f"unsupported baseline schema version {raw.get('schema_version')!r}")
    return _as_json_object(raw)


def _scenario_semantic(scenario: ScenarioReport) -> JsonValue:
    return {
        "name": scenario.name,
        "verdict": scenario.verdict,
        "error": scenario.error,
        "calls": [
            {
                "name": call.name,
                "tool": call.tool,
                "verdict": call.verdict,
                "differences": [asdict(item) for item in call.differences],
                "candidate": call.candidate,
                "reference": call.reference,
            }
            for call in scenario.calls
        ],
        "effects": [asdict(effect) for effect in scenario.effects],
    }


def _prepare_root(root: Path, contract: Path) -> Path:
    resolved = root.expanduser().resolve()
    forbidden = {Path(resolved.anchor).resolve(), Path.home().resolve(), contract.parent.resolve()}
    if resolved in forbidden:
        raise EvidenceError(f"refusing to use broad evidence directory: {resolved}")
    if resolved.exists() and not resolved.is_dir():
        raise EvidenceError(f"evidence path is not a directory: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "run.json"):
        target = resolved / name
        if target.exists():
            target.unlink()
    scenarios = resolved / "scenarios"
    if scenarios.exists():
        if not scenarios.is_dir():
            raise EvidenceError(f"owned evidence path is not a directory: {scenarios}")
        shutil.rmtree(scenarios)
    return resolved


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _slug(value: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in slug.split("-") if part)[:64] or "scenario"


def _as_json_object(value: dict[str, Any]) -> dict[str, JsonValue]:
    return {str(key): _as_json(item) for key, item in value.items()}


def _as_json(value: Any) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_as_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _as_json(item) for key, item in value.items()}
    raise EvidenceError(f"unsupported JSON value {type(value).__name__}")
