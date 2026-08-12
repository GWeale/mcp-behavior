"""Public result models and shared immutable specifications."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, TypeAlias

JsonValue: TypeAlias = bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"] | None


class Verdict(StrEnum):
    """A verification result that never conflates uncertainty with agreement."""

    MATCH = "MATCH"
    DIVERGE = "DIVERGE"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True, slots=True)
class Difference:
    path: str
    message: str
    reference: JsonValue = None
    candidate: JsonValue = None


@dataclass(frozen=True, slots=True)
class NormalizationSpec:
    ignore: tuple[str, ...] = ()
    redact: tuple[str, ...] = ()
    replace: tuple[tuple[str, JsonValue], ...] = ()
    builtins: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ComparisonSpec:
    kind: str = "json"
    numeric_tolerance: float | None = None
    unordered: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssertionSpec:
    outcome: str = "success"
    equals: JsonValue = None
    has_equals: bool = False
    contains: JsonValue = None
    has_contains: bool = False
    paths_equal: tuple[tuple[str, JsonValue], ...] = ()
    paths_absent: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CallReport:
    name: str
    tool: str
    verdict: Verdict
    arguments: JsonValue = None
    differences: tuple[Difference, ...] = ()
    candidate: JsonValue = None
    reference: JsonValue = None
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class EffectReport:
    name: str
    kind: str
    verdict: Verdict
    differences: tuple[Difference, ...] = ()
    candidate: JsonValue = None
    reference: JsonValue = None
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class ScenarioReport:
    name: str
    verdict: Verdict
    calls: tuple[CallReport, ...] = ()
    effects: tuple[EffectReport, ...] = ()
    error: str | None = None
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class VerificationReport:
    contract: str
    mode: str
    verdict: Verdict
    scenarios: tuple[ScenarioReport, ...]
    semantic_digest: str
    evidence_dir: str
    warnings: tuple[str, ...] = ()
    duration_ms: int = 0
    schema_version: int = 1

    @property
    def exit_code(self) -> int:
        if self.verdict is Verdict.MATCH:
            return 0
        if self.verdict is Verdict.DIVERGE:
            return 1
        return 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def aggregate_verdict(verdicts: list[Verdict] | tuple[Verdict, ...]) -> Verdict:
    if Verdict.DIVERGE in verdicts:
        return Verdict.DIVERGE
    if Verdict.INCONCLUSIVE in verdicts:
        return Verdict.INCONCLUSIVE
    return Verdict.MATCH


@dataclass(frozen=True, slots=True)
class Observation:
    value: JsonValue
    is_error: bool = False
    metadata: dict[str, JsonValue] = field(default_factory=dict)
