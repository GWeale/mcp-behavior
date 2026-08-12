"""Deep verification orchestration behind the public API."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Coroutine
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, TypeVar

from .comparison import assert_observation, compare_observations
from .contract import (
    CallSpec,
    Contract,
    ContractError,
    ObserverSpec,
    ScenarioSpec,
    TargetSpec,
    load_contract,
)
from .effects import EffectCapture, capture_observer, make_delta
from .evidence import (
    EvidenceError,
    digest_report_payload,
    read_baseline,
    semantic_report_payload,
    write_baseline,
    write_evidence,
)
from .execution import CommandResult, ExecutionError, run_command
from .models import (
    AssertionSpec,
    CallReport,
    ComparisonSpec,
    Difference,
    EffectReport,
    JsonValue,
    NormalizationSpec,
    Observation,
    ScenarioReport,
    Verdict,
    VerificationReport,
    aggregate_verdict,
)
from .normalization import normalize, sanitize
from .targets import ConnectedTarget, TargetError, connect_target

_T = TypeVar("_T")


@dataclass(slots=True)
class _TargetRun:
    calls: dict[str, Observation]
    effects: dict[str, Observation]
    error: str | None
    duration_ms: int
    logs: str
    secrets: tuple[str, ...]


def verify(
    contract_path: str | Path,
    evidence_dir: str | Path,
    target_overrides: dict[str, TargetSpec] | None = None,
    *,
    names: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> VerificationReport:
    """Verify selected scenarios and write sanitized evidence."""

    return _run_sync(
        verify_async(
            contract_path,
            evidence_dir,
            target_overrides,
            names=names,
            tags=tags,
        )
    )


async def verify_async(
    contract_path: str | Path,
    evidence_dir: str | Path,
    target_overrides: dict[str, TargetSpec] | None = None,
    *,
    names: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> VerificationReport:
    contract = load_contract(contract_path)
    if target_overrides:
        unknown = sorted(set(target_overrides) - set(contract.targets))
        if unknown:
            raise ContractError(
                contract.source,
                "$.targets",
                f"unknown target overrides: {', '.join(unknown)}",
            )
        contract = replace(contract, targets={**contract.targets, **target_overrides})
    selected = _select_scenarios(contract, names, tags)
    baseline = read_baseline(contract.baseline) if contract.baseline is not None else None
    if baseline is not None and baseline.get("contract_name") != contract.name:
        raise EvidenceError(
            f"baseline contract is {baseline.get('contract_name')!r}, expected {contract.name!r}"
        )

    started = time.perf_counter()
    reports: list[ScenarioReport] = []
    logs: dict[str, str] = {}
    for index, scenario in enumerate(selected):
        elapsed = time.perf_counter() - started
        remaining = contract.timeouts.total - elapsed
        if remaining <= 0:
            reports.extend(_timeout_reports(selected[index:], contract.timeouts.total))
            break
        try:
            scenario_report, scenario_logs = await asyncio.wait_for(
                _verify_scenario(contract, scenario, baseline),
                timeout=remaining,
            )
        except TimeoutError:
            reports.extend(_timeout_reports(selected[index:], contract.timeouts.total))
            break
        reports.append(scenario_report)
        logs[scenario.name] = scenario_logs

    scenario_tuple = tuple(reports)
    payload = semantic_report_payload(contract.name, contract.mode, scenario_tuple)
    digest = digest_report_payload(payload)
    verification_report = VerificationReport(
        contract=str(contract.source),
        mode=contract.mode,
        verdict=aggregate_verdict(tuple(item.verdict for item in scenario_tuple)),
        scenarios=scenario_tuple,
        semantic_digest=digest,
        evidence_dir=str(Path(evidence_dir).expanduser().resolve()),
        duration_ms=round((time.perf_counter() - started) * 1000),
    )
    write_evidence(verification_report, contract.name, logs)
    return verification_report


def record(
    contract_path: str | Path,
    baseline_path: str | Path | None = None,
    *,
    names: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> str:
    return _run_sync(record_async(contract_path, baseline_path, names=names, tags=tags))


async def record_async(
    contract_path: str | Path,
    baseline_path: str | Path | None = None,
    *,
    names: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> str:
    contract = load_contract(contract_path, allow_unasserted=True)
    if "reference" in contract.targets:
        raise ContractError(
            contract.source,
            "$.targets.reference",
            "record uses the candidate target only; remove the reference target",
        )
    output = Path(baseline_path).expanduser().resolve() if baseline_path else contract.baseline
    if output is None:
        raise ContractError(
            contract.source,
            "$.baseline",
            "record requires baseline in the contract or an explicit output path",
        )
    selected = _select_scenarios(contract, names, tags)
    records: list[JsonValue] = []
    for scenario in selected:
        run = await _execute_target_scenario(
            contract,
            scenario,
            contract.targets["candidate"],
        )
        if run.error:
            safe_error = _sanitize_text(run.error, run.secrets)
            raise EvidenceError(f"cannot record scenario {scenario.name!r}: {safe_error}")
        records.append(_baseline_scenario(scenario, run))
    return write_baseline(output, contract.name, records)


async def _verify_scenario(
    contract: Contract,
    scenario: ScenarioSpec,
    baseline: dict[str, JsonValue] | None,
) -> tuple[ScenarioReport, str]:
    started = time.perf_counter()
    reference_run = None
    if contract.mode == "differential":
        reference_run = await _execute_target_scenario(
            contract,
            scenario,
            contract.targets["reference"],
        )
    candidate_run = await _execute_target_scenario(
        contract,
        scenario,
        contract.targets["candidate"],
    )
    secrets = tuple(
        dict.fromkeys((reference_run.secrets if reference_run else ()) + candidate_run.secrets)
    )
    baseline_scenario = _find_baseline_scenario(baseline, scenario.name)

    call_reports = tuple(
        _evaluate_call(
            call,
            candidate_run,
            reference_run,
            baseline_scenario,
            contract.mode,
            secrets,
        )
        for call in scenario.calls
    )
    effect_reports = tuple(
        _evaluate_effect(
            observer,
            candidate_run,
            reference_run,
            baseline_scenario,
            contract.mode,
            secrets,
        )
        for observer in scenario.observers
    )
    errors = [
        error
        for error in (
            reference_run.error if reference_run else None,
            candidate_run.error,
        )
        if error
    ]
    safe_error = _sanitize_text("; ".join(errors), secrets) if errors else None
    verdicts = [item.verdict for item in call_reports]
    verdicts.extend(item.verdict for item in effect_reports)
    if safe_error:
        verdicts.append(Verdict.INCONCLUSIVE)
    report = ScenarioReport(
        name=scenario.name,
        verdict=aggregate_verdict(verdicts),
        calls=call_reports,
        effects=effect_reports,
        error=safe_error,
        duration_ms=round((time.perf_counter() - started) * 1000),
    )
    combined_logs = "\n".join(
        item
        for item in (
            reference_run.logs if reference_run else "",
            candidate_run.logs,
        )
        if item
    )
    safe_logs = _sanitize_text(combined_logs, secrets)
    if len(safe_logs.encode("utf-8")) > contract.limits.log_bytes:
        encoded = safe_logs.encode("utf-8")[: contract.limits.log_bytes]
        safe_logs = encoded.decode("utf-8", errors="ignore") + "\n<log-truncated>\n"
    return report, safe_logs


async def _execute_target_scenario(
    contract: Contract,
    scenario: ScenarioSpec,
    target: TargetSpec,
) -> _TargetRun:
    started = time.perf_counter()
    calls: dict[str, Observation] = {}
    effects: dict[str, Observation] = {}
    before: dict[str, Observation] = {}
    log_parts: list[str] = []
    secrets: list[str] = []
    error: str | None = None
    active = False
    connected: ConnectedTarget | None = None
    assert target.workspace is not None
    target.workspace.mkdir(parents=True, exist_ok=True)
    try:
        for index, command in enumerate(scenario.setup):
            active = True
            result = await run_command(
                command,
                source=contract.source,
                label=f"scenario {scenario.name!r} setup command {index + 1}",
                workspace=target.workspace,
                default_timeout=contract.timeouts.operation,
                log_limit=contract.limits.log_bytes,
            )
            _collect_command(result, log_parts, secrets, f"setup {index + 1}")
            if result.returncode != 0:
                raise ExecutionError(
                    f"scenario {scenario.name!r} setup command {index + 1} "
                    f"exited with code {result.returncode}"
                )
        active = True
        for observer in scenario.observers:
            if observer.phase == "delta":
                capture = await capture_observer(
                    observer,
                    contract,
                    scenario_name=scenario.name,
                    phase="before",
                    workspace=target.workspace,
                )
                before[observer.name] = capture.observation
                _collect_effect(capture, log_parts, secrets, f"observer {observer.name} before")

        async with connect_target(target, contract) as active_connection:
            connected = active_connection
            for call in scenario.calls:
                call_started = time.perf_counter()
                observation = await connected.call_tool(call.tool, call.arguments)
                calls[call.name] = Observation(
                    observation.value,
                    observation.is_error,
                    {
                        **observation.metadata,
                        "duration_ms": round((time.perf_counter() - call_started) * 1000),
                    },
                )
        _collect_connection(connected, log_parts, secrets)
        connected = None

        for observer in scenario.observers:
            observer_started = time.perf_counter()
            capture = await capture_observer(
                observer,
                contract,
                scenario_name=scenario.name,
                phase="after",
                workspace=target.workspace,
            )
            _collect_effect(capture, log_parts, secrets, f"observer {observer.name} after")
            observation = (
                make_delta(before[observer.name], capture.observation)
                if observer.phase == "delta"
                else capture.observation
            )
            effects[observer.name] = Observation(
                observation.value,
                observation.is_error,
                {
                    **observation.metadata,
                    "duration_ms": round((time.perf_counter() - observer_started) * 1000),
                },
            )
    except (ExecutionError, TargetError, OSError, ValueError) as exc:
        if connected is not None:
            _collect_connection(connected, log_parts, secrets)
        error = str(exc)
    finally:
        if active:
            for index, command in enumerate(scenario.cleanup):
                try:
                    result = await run_command(
                        command,
                        source=contract.source,
                        label=f"scenario {scenario.name!r} cleanup command {index + 1}",
                        workspace=target.workspace,
                        default_timeout=contract.timeouts.operation,
                        log_limit=contract.limits.log_bytes,
                    )
                    _collect_command(result, log_parts, secrets, f"cleanup {index + 1}")
                    if result.returncode != 0:
                        raise ExecutionError(
                            f"cleanup command {index + 1} exited with code {result.returncode}"
                        )
                except (ExecutionError, OSError, ValueError) as exc:
                    error = f"{error}; cleanup failed: {exc}" if error else f"cleanup failed: {exc}"
    return _TargetRun(
        calls,
        effects,
        error,
        round((time.perf_counter() - started) * 1000),
        "\n".join(log_parts),
        tuple(dict.fromkeys(secrets)),
    )


def _evaluate_call(
    spec: CallSpec,
    candidate_run: _TargetRun,
    reference_run: _TargetRun | None,
    baseline_scenario: dict[str, JsonValue] | None,
    mode: str,
    secrets: tuple[str, ...],
) -> CallReport:
    candidate = candidate_run.calls.get(spec.name)
    reference = (
        reference_run.calls.get(spec.name)
        if reference_run is not None
        else _baseline_observation(baseline_scenario, "calls", spec.name)
    )
    result = _evaluate_observation(
        name=spec.name,
        kind=spec.tool,
        candidate=candidate,
        reference=reference,
        assertion=spec.assertion,
        normalization=spec.normalization,
        comparison=spec.comparison,
        mode=mode,
        secrets=secrets,
        is_effect=False,
    )
    assert isinstance(result, CallReport)
    return replace(result, arguments=_sanitize_value(spec.arguments, secrets))


def _evaluate_effect(
    spec: ObserverSpec,
    candidate_run: _TargetRun,
    reference_run: _TargetRun | None,
    baseline_scenario: dict[str, JsonValue] | None,
    mode: str,
    secrets: tuple[str, ...],
) -> EffectReport:
    candidate = candidate_run.effects.get(spec.name)
    reference = (
        reference_run.effects.get(spec.name)
        if reference_run is not None
        else _baseline_observation(baseline_scenario, "effects", spec.name)
    )
    result = _evaluate_observation(
        name=spec.name,
        kind=spec.kind,
        candidate=candidate,
        reference=reference,
        assertion=spec.assertion,
        normalization=spec.normalization,
        comparison=spec.comparison,
        mode=mode,
        secrets=secrets,
        is_effect=True,
    )
    assert isinstance(result, EffectReport)
    return result


def _evaluate_observation(
    *,
    name: str,
    kind: str,
    candidate: Observation | None,
    reference: Observation | None,
    assertion: AssertionSpec | None,
    normalization: NormalizationSpec,
    comparison: ComparisonSpec,
    mode: str,
    secrets: tuple[str, ...],
    is_effect: bool,
) -> CallReport | EffectReport:
    differences: tuple[Difference, ...]
    if candidate is None:
        verdict = Verdict.INCONCLUSIVE
        differences = (Difference(path="$", message="candidate observation was not completed"),)
        safe_candidate = None
        safe_reference = _safe_observation_value(reference, normalization, secrets)
    else:
        normalized_candidate = Observation(
            normalize(candidate.value, normalization),
            candidate.is_error,
            candidate.metadata,
        )
        safe_candidate = _sanitize_value(normalized_candidate.value, secrets)
        safe_reference = None
        found_differences: list[Difference] = []
        if mode in {"differential", "baseline"}:
            if reference is None:
                verdict = Verdict.INCONCLUSIVE
                found_differences.append(
                    Difference(path="$", message="reference observation is missing")
                )
            else:
                normalized_reference = Observation(
                    normalize(reference.value, normalization),
                    reference.is_error,
                    reference.metadata,
                )
                if mode == "baseline":
                    normalized_candidate = Observation(
                        _sanitize_value(normalized_candidate.value, secrets),
                        normalized_candidate.is_error,
                        normalized_candidate.metadata,
                    )
                safe_reference = _sanitize_value(normalized_reference.value, secrets)
                found_differences.extend(
                    compare_observations(normalized_reference, normalized_candidate, comparison)
                )
                verdict = Verdict.DIVERGE if found_differences else Verdict.MATCH
        else:
            verdict = Verdict.MATCH
        if assertion is not None:
            found_differences.extend(
                assert_observation(normalized_candidate, assertion, comparison)
            )
            if found_differences and verdict is not Verdict.INCONCLUSIVE:
                verdict = Verdict.DIVERGE
        differences = tuple(_sanitize_difference(item, secrets) for item in found_differences)

    if is_effect:
        return EffectReport(
            name=name,
            kind=kind,
            verdict=verdict,
            differences=differences,
            candidate=safe_candidate,
            reference=safe_reference,
            duration_ms=_duration(candidate),
        )
    return CallReport(
        name=name,
        tool=kind,
        verdict=verdict,
        differences=differences,
        candidate=safe_candidate,
        reference=safe_reference,
        duration_ms=_duration(candidate),
    )


def _duration(observation: Observation | None) -> int:
    if observation is None:
        return 0
    value = observation.metadata.get("duration_ms")
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _baseline_scenario(scenario: ScenarioSpec, run: _TargetRun) -> JsonValue:
    return {
        "name": scenario.name,
        "calls": [
            {
                "name": call.name,
                "tool": call.tool,
                "value": _sanitize_value(
                    normalize(run.calls[call.name].value, call.normalization),
                    run.secrets,
                ),
                "is_error": run.calls[call.name].is_error,
            }
            for call in scenario.calls
        ],
        "effects": [
            {
                "name": observer.name,
                "kind": observer.kind,
                "value": _sanitize_value(
                    normalize(run.effects[observer.name].value, observer.normalization),
                    run.secrets,
                ),
                "is_error": run.effects[observer.name].is_error,
            }
            for observer in scenario.observers
        ],
    }


def _find_baseline_scenario(
    baseline: dict[str, JsonValue] | None,
    name: str,
) -> dict[str, JsonValue] | None:
    if baseline is None:
        return None
    scenarios = baseline.get("scenarios")
    if not isinstance(scenarios, list):
        return None
    for item in scenarios:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return None


def _baseline_observation(
    scenario: dict[str, JsonValue] | None,
    collection: str,
    name: str,
) -> Observation | None:
    if scenario is None:
        return None
    items = scenario.get(collection)
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("name") == name:
            return Observation(item.get("value"), bool(item.get("is_error", False)))
    return None


def _select_scenarios(
    contract: Contract,
    names: tuple[str, ...],
    tags: tuple[str, ...],
) -> tuple[ScenarioSpec, ...]:
    known_names = {scenario.name for scenario in contract.scenarios}
    unknown = sorted(set(names) - known_names)
    if unknown:
        raise ContractError(
            contract.source,
            "$.scenarios",
            f"unknown selected scenarios: {', '.join(unknown)}",
        )
    selected = tuple(
        scenario
        for scenario in contract.scenarios
        if (not names or scenario.name in names)
        and (not tags or set(tags).intersection(scenario.tags))
    )
    if not selected:
        raise ContractError(contract.source, "$.scenarios", "scenario selection matched nothing")
    return selected


def _timeout_reports(
    scenarios: tuple[ScenarioSpec, ...],
    total_timeout: float,
) -> list[ScenarioReport]:
    return [
        ScenarioReport(
            name=scenario.name,
            verdict=Verdict.INCONCLUSIVE,
            error=f"verification exceeded total timeout of {total_timeout:g} seconds",
        )
        for scenario in scenarios
    ]


def _collect_command(
    result: CommandResult,
    logs: list[str],
    secrets: list[str],
    label: str,
) -> None:
    secrets.extend(result.secrets)
    if result.stdout:
        logs.append(f"[{label} stdout]\n{result.stdout}")
    if result.stderr:
        logs.append(f"[{label} stderr]\n{result.stderr}")


def _collect_effect(
    capture: EffectCapture,
    logs: list[str],
    secrets: list[str],
    label: str,
) -> None:
    secrets.extend(capture.secrets)
    if capture.logs:
        logs.append(f"[{label}]\n{capture.logs}")


def _collect_connection(
    connected: ConnectedTarget,
    logs: list[str],
    secrets: list[str],
) -> None:
    secrets.extend(connected.secrets)
    if connected.logs:
        logs.append(f"[{connected.name} stderr]\n{connected.logs}")


def _safe_observation_value(
    observation: Observation | None,
    normalization: NormalizationSpec,
    secrets: tuple[str, ...],
) -> JsonValue:
    if observation is None:
        return None
    return _sanitize_value(normalize(observation.value, normalization), secrets)


def _sanitize_difference(item: Difference, secrets: tuple[str, ...]) -> Difference:
    return Difference(
        path=item.path,
        message=_sanitize_text(item.message, secrets),
        reference=_sanitize_value(item.reference, secrets),
        candidate=_sanitize_value(item.candidate, secrets),
    )


def _sanitize_value(value: JsonValue, secrets: tuple[str, ...]) -> JsonValue:
    return sanitize(value, secrets)


def _sanitize_text(value: str, secrets: tuple[str, ...]) -> str:
    sanitized = sanitize(value, secrets)
    assert isinstance(sanitized, str)
    return sanitized


def _run_sync(awaitable: Coroutine[Any, Any, _T]) -> _T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("a running event loop was detected; use the async API instead")
