"""Strict compilation of human-authored scenario contracts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

from .models import AssertionSpec, ComparisonSpec, JsonValue, NormalizationSpec

_SENSITIVE_NAME = re.compile(
    r"(?:authorization|api[_-]?key|token|secret|password|credential)", re.I
)
_BUILTINS = {"timestamps", "uuids", "temp_paths", "ports", "request_ids"}


class ContractError(ValueError):
    """A source-attributed contract problem."""

    def __init__(self, source: Path, field_path: str, message: str) -> None:
        self.source = source
        self.field_path = field_path
        self.detail = message
        super().__init__(f"{source}:{field_path}: {message}")


class _StrictLoader(yaml.SafeLoader):
    def compose_node(self, parent: Any, index: Any) -> yaml.Node:
        # PyYAML's published stubs omit these parser method signatures.
        if self.check_event(yaml.AliasEvent):  # type: ignore[no-untyped-call]
            event = self.get_event()  # type: ignore[no-untyped-call]
            raise ConstructorError(
                None,
                None,
                "YAML aliases are not supported",
                event.start_mark,
            )
        node = super().compose_node(parent, index)
        assert node is not None
        return node


def _construct_mapping(
    loader: _StrictLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True, slots=True)
class ValueSource:
    literal: str | None = None
    from_env: str | None = None
    template: str = "{value}"

    def resolve(self, source: Path, field_path: str) -> tuple[str, str | None]:
        if self.from_env is None:
            assert self.literal is not None
            return self.literal, None
        value = os.environ.get(self.from_env)
        if value is None:
            raise ContractError(
                source,
                field_path,
                f"environment variable {self.from_env!r} is not set",
            )
        return self.template.replace("{value}", value), value

    def describe(self) -> JsonValue:
        if self.from_env is not None:
            return {"from_env": self.from_env, "template": self.template}
        return self.literal


@dataclass(frozen=True, slots=True)
class TargetSpec:
    name: str
    transport: str
    command: tuple[str, ...] = ()
    url: str | None = None
    cwd: Path | None = None
    workspace: Path | None = None
    env: dict[str, ValueSource] = field(default_factory=dict)
    headers: dict[str, ValueSource] = field(default_factory=dict)
    mode: str = "auto"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    command: tuple[str, ...]
    cwd: Path | None
    env: dict[str, ValueSource] = field(default_factory=dict)
    timeout: float | None = None


@dataclass(frozen=True, slots=True)
class CallSpec:
    name: str
    tool: str
    arguments: dict[str, JsonValue]
    normalization: NormalizationSpec
    comparison: ComparisonSpec
    assertion: AssertionSpec | None = None


@dataclass(frozen=True, slots=True)
class ObserverSpec:
    name: str
    kind: str
    root: Path | None = None
    path: str | None = None
    query: str | None = None
    command: CommandSpec | None = None
    phase: str = "after"
    normalization: NormalizationSpec = field(default_factory=NormalizationSpec)
    comparison: ComparisonSpec = field(default_factory=ComparisonSpec)
    assertion: AssertionSpec | None = None


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    name: str
    tags: tuple[str, ...]
    setup: tuple[CommandSpec, ...]
    calls: tuple[CallSpec, ...]
    observers: tuple[ObserverSpec, ...]
    cleanup: tuple[CommandSpec, ...]


@dataclass(frozen=True, slots=True)
class Timeouts:
    connect: float = 10.0
    operation: float = 30.0
    total: float = 120.0


@dataclass(frozen=True, slots=True)
class Limits:
    output_bytes: int = 1_048_576
    log_bytes: int = 262_144


@dataclass(frozen=True, slots=True)
class Contract:
    source: Path
    name: str
    targets: dict[str, TargetSpec]
    scenarios: tuple[ScenarioSpec, ...]
    timeouts: Timeouts
    limits: Limits
    baseline: Path | None = None
    version: int = 1

    @property
    def mode(self) -> str:
        if "reference" in self.targets:
            return "differential"
        if self.baseline is not None:
            return "baseline"
        return "expectations"


def load_contract(path: str | Path, *, allow_unasserted: bool = False) -> Contract:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ContractError(source, "$", "contract file does not exist")
    try:
        document = yaml.load(source.read_text(encoding="utf-8"), Loader=_StrictLoader)
    except (yaml.YAMLError, UnicodeError) as exc:
        raise ContractError(source, "$", str(exc)) from exc
    data = _mapping(document, source, "$")
    _unknown(
        data,
        {"version", "name", "targets", "scenarios", "timeouts", "limits", "baseline"},
        source,
        "$",
    )
    version = _integer(data.get("version"), source, "$.version")
    if version != 1:
        raise ContractError(source, "$.version", f"unsupported contract version {version!r}")
    name = _string(data.get("name", source.stem), source, "$.name")
    base = source.parent
    targets_data = _mapping(data.get("targets"), source, "$.targets")
    if "candidate" not in targets_data:
        raise ContractError(source, "$.targets", "a candidate target is required")
    _unknown(targets_data, {"candidate", "reference"}, source, "$.targets")
    targets = {
        target_name: _target(target_name, target_data, source, base, f"$.targets.{target_name}")
        for target_name, target_data in targets_data.items()
    }
    scenarios_raw = _list(data.get("scenarios"), source, "$.scenarios")
    if not scenarios_raw:
        raise ContractError(source, "$.scenarios", "at least one scenario is required")
    scenarios = tuple(
        _scenario(item, source, base, f"$.scenarios[{index}]")
        for index, item in enumerate(scenarios_raw)
    )
    names = [scenario.name for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ContractError(source, "$.scenarios", "scenario names must be unique")
    timeouts = _timeouts(data.get("timeouts", {}), source)
    limits = _limits(data.get("limits", {}), source)
    baseline_raw = data.get("baseline")
    baseline = (
        _resolve_path(base, _string(baseline_raw, source, "$.baseline"))
        if baseline_raw is not None
        else None
    )
    contract = Contract(source, name, targets, scenarios, timeouts, limits, baseline, version)
    _validate_mode(contract, allow_unasserted=allow_unasserted)
    return contract


def _target(name: str, value: Any, source: Path, base: Path, field_path: str) -> TargetSpec:
    data = _mapping(value, source, field_path)
    _unknown(
        data,
        {"transport", "command", "url", "cwd", "workspace", "env", "headers", "mode"},
        source,
        field_path,
    )
    transport = _string(data.get("transport"), source, f"{field_path}.transport")
    if transport not in {"stdio", "http"}:
        raise ContractError(source, f"{field_path}.transport", "must be 'stdio' or 'http'")
    mode = _string(data.get("mode", "auto"), source, f"{field_path}.mode")
    if mode not in {"auto", "modern", "legacy"}:
        raise ContractError(source, f"{field_path}.mode", "must be auto, modern, or legacy")
    env = _value_sources(data.get("env", {}), source, f"{field_path}.env")
    headers = _value_sources(data.get("headers", {}), source, f"{field_path}.headers")
    if transport == "stdio":
        command = _string_list(data.get("command"), source, f"{field_path}.command")
        if not command:
            raise ContractError(source, f"{field_path}.command", "must not be empty")
        if "url" in data or headers:
            raise ContractError(source, field_path, "stdio targets cannot declare url or headers")
        cwd = _resolve_path(base, _string(data.get("cwd", "."), source, f"{field_path}.cwd"))
        workspace = _resolve_path(
            base,
            _string(data.get("workspace", str(cwd)), source, f"{field_path}.workspace"),
        )
        return TargetSpec(
            name=name,
            transport=transport,
            command=tuple(command),
            cwd=cwd,
            workspace=workspace,
            env=env,
            mode=mode,
        )
    url = _string(data.get("url"), source, f"{field_path}.url")
    if "command" in data or "cwd" in data or env:
        raise ContractError(source, field_path, "http targets cannot declare command, cwd, or env")
    if not url.startswith(("http://", "https://")):
        raise ContractError(source, f"{field_path}.url", "must be an http:// or https:// URL")
    workspace = _resolve_path(
        base,
        _string(data.get("workspace", "."), source, f"{field_path}.workspace"),
    )
    return TargetSpec(
        name=name,
        transport=transport,
        url=url,
        workspace=workspace,
        headers=headers,
        mode=mode,
    )


def _scenario(value: Any, source: Path, base: Path, field_path: str) -> ScenarioSpec:
    data = _mapping(value, source, field_path)
    _unknown(data, {"name", "tags", "setup", "calls", "observers", "cleanup"}, source, field_path)
    name = _string(data.get("name"), source, f"{field_path}.name")
    tags = tuple(_string_list(data.get("tags", []), source, f"{field_path}.tags"))
    setup = _commands(data.get("setup", []), source, base, f"{field_path}.setup")
    calls_raw = _list(data.get("calls"), source, f"{field_path}.calls")
    if not calls_raw:
        raise ContractError(source, f"{field_path}.calls", "at least one call is required")
    calls = tuple(
        _call(item, source, f"{field_path}.calls[{index}]") for index, item in enumerate(calls_raw)
    )
    call_names = [call.name for call in calls]
    if len(set(call_names)) != len(call_names):
        raise ContractError(source, f"{field_path}.calls", "call names must be unique")
    observers = tuple(
        _observer(item, source, base, f"{field_path}.observers[{index}]")
        for index, item in enumerate(
            _list(data.get("observers", []), source, f"{field_path}.observers")
        )
    )
    observer_names = [observer.name for observer in observers]
    if len(set(observer_names)) != len(observer_names):
        raise ContractError(source, f"{field_path}.observers", "observer names must be unique")
    cleanup = _commands(data.get("cleanup", []), source, base, f"{field_path}.cleanup")
    return ScenarioSpec(name, tags, setup, calls, observers, cleanup)


def _call(value: Any, source: Path, field_path: str) -> CallSpec:
    data = _mapping(value, source, field_path)
    _unknown(
        data, {"name", "tool", "arguments", "normalize", "compare", "expect"}, source, field_path
    )
    tool = _string(data.get("tool"), source, f"{field_path}.tool")
    name = _string(data.get("name", tool), source, f"{field_path}.name")
    arguments = _json_mapping(data.get("arguments", {}), source, f"{field_path}.arguments")
    normalization = _normalization(data.get("normalize", {}), source, f"{field_path}.normalize")
    comparison = _comparison(data.get("compare", {}), source, f"{field_path}.compare")
    assertion = (
        _assertion(data["expect"], source, f"{field_path}.expect") if "expect" in data else None
    )
    return CallSpec(name, tool, arguments, normalization, comparison, assertion)


def _observer(value: Any, source: Path, base: Path, field_path: str) -> ObserverSpec:
    data = _mapping(value, source, field_path)
    allowed = {
        "name",
        "kind",
        "root",
        "path",
        "query",
        "command",
        "cwd",
        "env",
        "timeout",
        "phase",
        "normalize",
        "compare",
        "expect",
    }
    _unknown(data, allowed, source, field_path)
    name = _string(data.get("name"), source, f"{field_path}.name")
    kind = _string(data.get("kind"), source, f"{field_path}.kind")
    if kind not in {"file", "tree", "sqlite", "command"}:
        raise ContractError(source, f"{field_path}.kind", "must be file, tree, sqlite, or command")
    phase = _string(data.get("phase", "after"), source, f"{field_path}.phase")
    if phase not in {"after", "delta"}:
        raise ContractError(source, f"{field_path}.phase", "must be after or delta")
    normalization = _normalization(data.get("normalize", {}), source, f"{field_path}.normalize")
    comparison = _comparison(data.get("compare", {}), source, f"{field_path}.compare")
    assertion = (
        _assertion(data["expect"], source, f"{field_path}.expect") if "expect" in data else None
    )
    if kind == "command":
        command = _command(data, source, base, field_path, inline=True)
        return ObserverSpec(
            name,
            kind,
            command=command,
            phase=phase,
            normalization=normalization,
            comparison=comparison,
            assertion=assertion,
        )
    root = Path(_string(data.get("root", "."), source, f"{field_path}.root")).expanduser()
    path = data.get("path")
    path_value = _string(path, source, f"{field_path}.path") if path is not None else None
    query = data.get("query")
    query_value = _string(query, source, f"{field_path}.query") if query is not None else None
    if kind in {"file", "sqlite"} and path_value is None:
        raise ContractError(source, f"{field_path}.path", f"{kind} observer requires path")
    if kind == "tree" and path_value is not None:
        raise ContractError(source, field_path, "tree observer uses root and does not accept path")
    if kind == "sqlite" and query_value is None:
        raise ContractError(source, f"{field_path}.query", "sqlite observer requires query")
    if kind != "sqlite" and query_value is not None:
        raise ContractError(source, field_path, "query is only valid for sqlite observers")
    return ObserverSpec(
        name, kind, root, path_value, query_value, None, phase, normalization, comparison, assertion
    )


def _commands(value: Any, source: Path, base: Path, field_path: str) -> tuple[CommandSpec, ...]:
    return tuple(
        _command(item, source, base, f"{field_path}[{index}]")
        for index, item in enumerate(_list(value, source, field_path))
    )


def _command(
    value: Any,
    source: Path,
    base: Path,
    field_path: str,
    *,
    inline: bool = False,
) -> CommandSpec:
    data = _mapping(value, source, field_path)
    allowed = {"command", "cwd", "env", "timeout"}
    if not inline:
        _unknown(data, allowed, source, field_path)
    command = _string_list(data.get("command"), source, f"{field_path}.command")
    if not command:
        raise ContractError(source, f"{field_path}.command", "must not be empty")
    cwd = (
        _resolve_path(base, _string(data["cwd"], source, f"{field_path}.cwd"))
        if "cwd" in data
        else None
    )
    env = _value_sources(data.get("env", {}), source, f"{field_path}.env")
    timeout_raw = data.get("timeout")
    timeout = (
        _positive_number(timeout_raw, source, f"{field_path}.timeout")
        if timeout_raw is not None
        else None
    )
    return CommandSpec(tuple(command), cwd, env, timeout)


def _normalization(value: Any, source: Path, field_path: str) -> NormalizationSpec:
    data = _mapping(value, source, field_path)
    _unknown(data, {"ignore", "redact", "replace", "builtins"}, source, field_path)
    ignore = tuple(_string_list(data.get("ignore", []), source, f"{field_path}.ignore"))
    redact = tuple(_string_list(data.get("redact", []), source, f"{field_path}.redact"))
    builtins = tuple(_string_list(data.get("builtins", []), source, f"{field_path}.builtins"))
    unknown_builtins = sorted(set(builtins) - _BUILTINS)
    if unknown_builtins:
        raise ContractError(
            source, f"{field_path}.builtins", f"unknown builtins: {', '.join(unknown_builtins)}"
        )
    replace_data = _mapping(data.get("replace", {}), source, f"{field_path}.replace")
    replace = tuple(
        (str(path), _json(value, source, f"{field_path}.replace.{path}"))
        for path, value in replace_data.items()
    )
    return NormalizationSpec(ignore, redact, replace, builtins)


def _comparison(value: Any, source: Path, field_path: str) -> ComparisonSpec:
    data = _mapping(value, source, field_path)
    _unknown(data, {"kind", "numeric_tolerance", "unordered"}, source, field_path)
    kind = _string(data.get("kind", "json"), source, f"{field_path}.kind")
    if kind not in {"exact", "json", "text", "bytes"}:
        raise ContractError(source, f"{field_path}.kind", "must be exact, json, text, or bytes")
    tolerance_raw = data.get("numeric_tolerance")
    tolerance = (
        _nonnegative_number(tolerance_raw, source, f"{field_path}.numeric_tolerance")
        if tolerance_raw is not None
        else None
    )
    unordered = tuple(_string_list(data.get("unordered", []), source, f"{field_path}.unordered"))
    return ComparisonSpec(kind, tolerance, unordered)


def _assertion(value: Any, source: Path, field_path: str) -> AssertionSpec:
    data = _mapping(value, source, field_path)
    _unknown(
        data, {"outcome", "equals", "contains", "paths_equal", "paths_absent"}, source, field_path
    )
    outcome = _string(data.get("outcome", "success"), source, f"{field_path}.outcome")
    if outcome not in {"success", "error"}:
        raise ContractError(source, f"{field_path}.outcome", "must be success or error")
    equals = _json(data.get("equals"), source, f"{field_path}.equals")
    contains = _json(data.get("contains"), source, f"{field_path}.contains")
    paths_data = _mapping(data.get("paths_equal", {}), source, f"{field_path}.paths_equal")
    paths_equal = tuple(
        (str(path), _json(item, source, f"{field_path}.paths_equal.{path}"))
        for path, item in paths_data.items()
    )
    paths_absent = tuple(
        _string_list(data.get("paths_absent", []), source, f"{field_path}.paths_absent")
    )
    return AssertionSpec(
        outcome, equals, "equals" in data, contains, "contains" in data, paths_equal, paths_absent
    )


def _timeouts(value: Any, source: Path) -> Timeouts:
    data = _mapping(value, source, "$.timeouts")
    _unknown(data, {"connect", "operation", "total"}, source, "$.timeouts")
    return Timeouts(
        _positive_number(data.get("connect", 10), source, "$.timeouts.connect"),
        _positive_number(data.get("operation", 30), source, "$.timeouts.operation"),
        _positive_number(data.get("total", 120), source, "$.timeouts.total"),
    )


def _limits(value: Any, source: Path) -> Limits:
    data = _mapping(value, source, "$.limits")
    _unknown(data, {"output_bytes", "log_bytes"}, source, "$.limits")
    return Limits(
        _positive_integer(data.get("output_bytes", 1_048_576), source, "$.limits.output_bytes"),
        _positive_integer(data.get("log_bytes", 262_144), source, "$.limits.log_bytes"),
    )


def _validate_mode(contract: Contract, *, allow_unasserted: bool) -> None:
    if contract.mode == "differential" and any(
        scenario.setup or scenario.cleanup or scenario.observers for scenario in contract.scenarios
    ):
        candidate_workspace = contract.targets["candidate"].workspace
        reference_workspace = contract.targets["reference"].workspace
        if candidate_workspace == reference_workspace:
            raise ContractError(
                contract.source,
                "$.targets",
                "differential scenarios with commands or observers require "
                "distinct target workspaces",
            )
    if contract.mode != "expectations" or allow_unasserted:
        return
    for scenario_index, scenario in enumerate(contract.scenarios):
        for call_index, call in enumerate(scenario.calls):
            if call.assertion is None:
                raise ContractError(
                    contract.source,
                    f"$.scenarios[{scenario_index}].calls[{call_index}].expect",
                    "required when no reference target or baseline is declared",
                )
        for observer_index, observer in enumerate(scenario.observers):
            if observer.assertion is None:
                raise ContractError(
                    contract.source,
                    f"$.scenarios[{scenario_index}].observers[{observer_index}].expect",
                    "required when no reference target or baseline is declared",
                )


def _value_sources(value: Any, source: Path, field_path: str) -> dict[str, ValueSource]:
    data = _mapping(value, source, field_path)
    result: dict[str, ValueSource] = {}
    for raw_name, raw_value in data.items():
        name = _string(raw_name, source, field_path)
        item_path = f"{field_path}.{name}"
        if isinstance(raw_value, str):
            if _SENSITIVE_NAME.search(name):
                raise ContractError(source, item_path, "sensitive values must use from_env")
            result[name] = ValueSource(literal=raw_value)
            continue
        item = _mapping(raw_value, source, item_path)
        _unknown(item, {"from_env", "template"}, source, item_path)
        env_name = _string(item.get("from_env"), source, f"{item_path}.from_env")
        template = _string(item.get("template", "{value}"), source, f"{item_path}.template")
        if "{value}" not in template:
            raise ContractError(source, f"{item_path}.template", "must contain '{value}'")
        result[name] = ValueSource(from_env=env_name, template=template)
    return result


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _unknown(data: dict[Any, Any], allowed: set[str], source: Path, field_path: str) -> None:
    unknown = sorted(str(key) for key in data if key not in allowed)
    if unknown:
        raise ContractError(source, field_path, f"unknown fields: {', '.join(unknown)}")


def _mapping(value: Any, source: Path, field_path: str) -> dict[Any, Any]:
    if not isinstance(value, dict):
        raise ContractError(source, field_path, "must be a mapping")
    return value


def _json_mapping(value: Any, source: Path, field_path: str) -> dict[str, JsonValue]:
    data = _mapping(value, source, field_path)
    return {str(key): _json(item, source, f"{field_path}.{key}") for key, item in data.items()}


def _list(value: Any, source: Path, field_path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(source, field_path, "must be a list")
    return value


def _string(value: Any, source: Path, field_path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(source, field_path, "must be a non-empty string")
    return value


def _string_list(value: Any, source: Path, field_path: str) -> list[str]:
    items = _list(value, source, field_path)
    return [_string(item, source, f"{field_path}[{index}]") for index, item in enumerate(items)]


def _integer(value: Any, source: Path, field_path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(source, field_path, "must be an integer")
    return int(value)


def _positive_integer(value: Any, source: Path, field_path: str) -> int:
    number = _integer(value, source, field_path)
    if number <= 0:
        raise ContractError(source, field_path, "must be greater than zero")
    return number


def _positive_number(value: Any, source: Path, field_path: str) -> float:
    number = _number(value, source, field_path)
    if number <= 0:
        raise ContractError(source, field_path, "must be greater than zero")
    return number


def _nonnegative_number(value: Any, source: Path, field_path: str) -> float:
    number = _number(value, source, field_path)
    if number < 0:
        raise ContractError(source, field_path, "must not be negative")
    return number


def _number(value: Any, source: Path, field_path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(source, field_path, "must be a number")
    return float(value)


def _json(value: Any, source: Path, field_path: str) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_json(item, source, f"{field_path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError(source, field_path, "JSON object keys must be strings")
            result[key] = _json(item, source, f"{field_path}.{key}")
        return result
    raise ContractError(source, field_path, f"unsupported value type {type(value).__name__}")
