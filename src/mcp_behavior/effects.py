"""Explicit, bounded observers for filesystem, SQLite, and trusted probes."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import Contract, ObserverSpec
from .execution import ExecutionError, run_command
from .models import JsonValue, Observation
from .normalization import enforce_serialized_limit


@dataclass(frozen=True, slots=True)
class EffectCapture:
    observation: Observation
    logs: str = ""
    secrets: tuple[str, ...] = ()


async def capture_observer(
    spec: ObserverSpec,
    contract: Contract,
    *,
    scenario_name: str,
    phase: str,
    workspace: Path,
) -> EffectCapture:
    if spec.kind == "file":
        assert spec.root is not None and spec.path is not None
        value = _capture_file(
            _observer_root(workspace, spec.root),
            spec.path,
            contract.limits.output_bytes,
        )
        return EffectCapture(Observation(value))
    if spec.kind == "tree":
        assert spec.root is not None
        value = _capture_tree(
            _observer_root(workspace, spec.root),
            contract.limits.output_bytes,
        )
        return EffectCapture(Observation(value))
    if spec.kind == "sqlite":
        assert spec.root is not None and spec.path is not None and spec.query is not None
        value = _capture_sqlite(
            _observer_root(workspace, spec.root),
            spec.path,
            spec.query,
            contract.limits.output_bytes,
        )
        return EffectCapture(Observation(value))
    if spec.kind == "command":
        assert spec.command is not None
        payload: JsonValue = {
            "version": 1,
            "scenario": scenario_name,
            "observer": spec.name,
            "phase": phase,
        }
        result = await run_command(
            spec.command,
            source=contract.source,
            label=f"custom observer {spec.name!r}",
            workspace=workspace,
            default_timeout=contract.timeouts.operation,
            log_limit=contract.limits.log_bytes,
            stdin_value=payload,
        )
        if result.returncode != 0:
            raise ExecutionError(
                f"custom observer {spec.name!r} exited with code {result.returncode}"
            )
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ExecutionError(
                f"custom observer {spec.name!r} did not return one JSON value: {exc}"
            ) from exc
        json_value = _as_json(value)
        enforce_serialized_limit(json_value, contract.limits.output_bytes)
        return EffectCapture(Observation(json_value), result.stderr, result.secrets)
    raise ExecutionError(f"unsupported observer kind {spec.kind!r}")


def make_delta(before: Observation, after: Observation) -> Observation:
    before_state = _state(before.value)
    after_state = _state(after.value)
    if before_state == "missing" and after_state != "missing":
        change = "created"
    elif before_state != "missing" and after_state == "missing":
        change = "deleted"
    elif before.value == after.value:
        change = "unchanged"
    else:
        change = "modified"
    return Observation(
        {
            "change": change,
            "before": before.value,
            "after": after.value,
        }
    )


def _capture_file(root: Path, relative: str, max_bytes: int) -> JsonValue:
    path = resolve_within(root, relative)
    if not path.exists():
        return {"state": "missing"}
    if not path.is_file():
        raise ExecutionError(f"observed file path is not a regular file: {relative}")
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise ExecutionError(
            f"observed file {relative!r} is {len(data)} bytes; limit is {max_bytes}"
        )
    digest = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        value: JsonValue = {
            "state": "present",
            "encoding": "base64",
            "data": base64.b64encode(data).decode("ascii"),
            "bytes": len(data),
            "sha256": digest,
        }
    else:
        value = {
            "state": "present",
            "encoding": "utf-8",
            "text": text,
            "bytes": len(data),
            "sha256": digest,
        }
    enforce_serialized_limit(value, max_bytes * 2)
    return value


def _capture_tree(root: Path, max_bytes: int) -> JsonValue:
    resolved_root = root.resolve()
    if not resolved_root.exists():
        return {"state": "missing", "entries": []}
    if not resolved_root.is_dir():
        raise ExecutionError(f"observed tree root is not a directory: {root}")
    entries: list[JsonValue] = []
    _walk_tree(resolved_root, resolved_root, entries)
    value: JsonValue = {"state": "present", "entries": entries}
    enforce_serialized_limit(value, max_bytes)
    return value


def _walk_tree(root: Path, current: Path, entries: list[JsonValue]) -> None:
    with os.scandir(current) as iterator:
        directory_entries = sorted(iterator, key=lambda entry: entry.name)
    for entry in directory_entries:
        path = Path(entry.path)
        relative = path.relative_to(root).as_posix()
        if entry.is_symlink():
            entries.append({"path": relative, "type": "symlink"})
        elif entry.is_dir(follow_symlinks=False):
            entries.append({"path": relative, "type": "directory"})
            _walk_tree(root, path, entries)
        elif entry.is_file(follow_symlinks=False):
            data = path.read_bytes()
            entries.append(
                {
                    "path": relative,
                    "type": "file",
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        else:
            entries.append({"path": relative, "type": "other"})


def _capture_sqlite(root: Path, relative: str, query: str, max_bytes: int) -> JsonValue:
    path = resolve_within(root, relative)
    if not path.is_file():
        return {"state": "missing", "columns": [], "rows": []}
    first_word = query.lstrip().split(maxsplit=1)[0].lower() if query.strip() else ""
    if first_word not in {"select", "with"}:
        raise ExecutionError("SQLite observer queries must start with SELECT or WITH")
    uri = f"{path.as_uri()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=2)) as connection:
            connection.execute("PRAGMA query_only = ON")
            cursor = connection.execute(query)
            rows = cursor.fetchmany(1001)
            if len(rows) > 1000:
                raise ExecutionError("SQLite observer returned more than 1000 rows")
            columns = [item[0] for item in cursor.description or ()]
    except sqlite3.Error as exc:
        raise ExecutionError(f"SQLite observer query failed: {exc}") from exc
    value: JsonValue = {
        "state": "present",
        "columns": columns,
        "rows": [[_sqlite_value(item) for item in row] for row in rows],
    }
    enforce_serialized_limit(value, max_bytes)
    return value


def _sqlite_value(value: Any) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"encoding": "base64", "data": base64.b64encode(value).decode("ascii")}
    return str(value)


def resolve_within(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ExecutionError("observer path must be relative to its declared root")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ExecutionError(f"observer path escapes declared root: {relative!r}")
    return resolved


def _observer_root(workspace: Path, root: Path) -> Path:
    return root.resolve() if root.is_absolute() else (workspace / root).resolve()


def _state(value: JsonValue) -> str | None:
    if isinstance(value, dict):
        state = value.get("state")
        return state if isinstance(state, str) else None
    return None


def _as_json(value: Any) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_as_json(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ExecutionError("custom observer JSON object keys must be strings")
        return {str(key): _as_json(item) for key, item in value.items()}
    raise ExecutionError(f"custom observer returned unsupported JSON value {type(value).__name__}")
