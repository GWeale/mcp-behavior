"""Explicit normalization, JSON-path access, and persistence redaction."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from ast import literal_eval
from collections.abc import Iterable, Mapping
from typing import Any

from .models import JsonValue, NormalizationSpec

_PATH_TOKEN = re.compile(
    r"(?:\.([A-Za-z_][A-Za-z0-9_-]*))|(?:\[(\d+)\])|"
    r"(?:\[((?:\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'))\])"
)
_SECRET_KEY = re.compile(r"(?:authorization|api[_-]?key|token|secret|password|credential)", re.I)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_OPENAI_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")
_ISO_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)
_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_PORT_IN_URL = re.compile(r"(?<=:)(?:[1-9]\d{1,4})(?=(?:/|$))")
_TEMP_PATH = re.compile(r"(?i)(?:[A-Z]:\\[^\s]+\\Temp\\[^\s]+|/tmp/[^\s]+)")
_REQUEST_ID_KEYS = {"request_id", "requestid", "trace_id", "traceid", "run_id", "runid"}


class JsonPathError(ValueError):
    pass


class ObservationLimitError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def semantic_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_json_path(path: str) -> tuple[str | int, ...]:
    if path == "$":
        return ()
    if not path.startswith("$"):
        raise JsonPathError(f"JSON path must start with '$': {path!r}")
    tokens: list[str | int] = []
    position = 1
    while position < len(path):
        match = _PATH_TOKEN.match(path, position)
        if match is None:
            raise JsonPathError(
                f"unsupported JSON path syntax at character {position + 1}: {path!r}"
            )
        key, index, quoted_key = match.groups()
        if key is not None:
            tokens.append(key)
        elif index is not None:
            tokens.append(int(index))
        else:
            parsed_key = literal_eval(quoted_key)
            if not isinstance(parsed_key, str):  # pragma: no cover - constrained by regex
                raise JsonPathError(f"JSON path key must be text: {path!r}")
            tokens.append(parsed_key)
        position = match.end()
    return tuple(tokens)


def get_path(value: JsonValue, path: str) -> tuple[bool, JsonValue]:
    current: Any = value
    for token in parse_json_path(path):
        if _can_descend(current, token):
            current = current[token]
        else:
            return False, None
    return True, current


def _parent(value: JsonValue, path: str) -> tuple[Any, str | int] | None:
    tokens = parse_json_path(path)
    if not tokens:
        return None
    current: Any = value
    for token in tokens[:-1]:
        if _can_descend(current, token):
            current = current[token]
        else:
            return None
    return current, tokens[-1]


def _can_descend(current: Any, token: str | int) -> bool:
    if isinstance(token, str):
        return isinstance(current, dict) and token in current
    return isinstance(current, list) and 0 <= token < len(current)


def remove_path(value: JsonValue, path: str) -> bool:
    found = _parent(value, path)
    if found is None:
        return False
    parent, token = found
    if isinstance(parent, dict) and isinstance(token, str) and token in parent:
        del parent[token]
        return True
    if isinstance(parent, list) and isinstance(token, int) and 0 <= token < len(parent):
        del parent[token]
        return True
    return False


def set_path(value: JsonValue, path: str, replacement: JsonValue) -> bool:
    if path == "$":
        raise JsonPathError("the document root cannot be replaced by an in-place rule")
    found = _parent(value, path)
    if found is None:
        return False
    parent, token = found
    if isinstance(parent, dict) and isinstance(token, str) and token in parent:
        parent[token] = replacement
        return True
    if isinstance(parent, list) and isinstance(token, int) and 0 <= token < len(parent):
        parent[token] = replacement
        return True
    return False


def normalize(value: JsonValue, spec: NormalizationSpec) -> JsonValue:
    normalized = copy.deepcopy(value)
    normalized = _apply_builtins(normalized, frozenset(spec.builtins))
    for path in spec.ignore:
        remove_path(normalized, path)
    for path in spec.redact:
        set_path(normalized, path, "<redacted>")
    for path, replacement in spec.replace:
        set_path(normalized, path, copy.deepcopy(replacement))
    return normalized


def _apply_builtins(value: JsonValue, enabled: frozenset[str], key: str | None = None) -> JsonValue:
    if isinstance(value, dict):
        return {
            item_key: _apply_builtins(item, enabled, item_key) for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_apply_builtins(item, enabled, key) for item in value]
    if "request_ids" in enabled and key is not None and key.lower() in _REQUEST_ID_KEYS:
        return "<request-id>"
    if (
        "ports" in enabled
        and key is not None
        and key.lower() in {"port", "local_port", "remote_port"}
        and isinstance(value, int)
    ):
        return "<port>"
    if not isinstance(value, str):
        return value
    if "timestamps" in enabled and _ISO_TIMESTAMP.fullmatch(value):
        return "<timestamp>"
    if "uuids" in enabled and _UUID.fullmatch(value):
        return "<uuid>"
    if "ports" in enabled:
        value = _PORT_IN_URL.sub("<port>", value)
    if "temp_paths" in enabled:
        value = _TEMP_PATH.sub("<temp-path>", value)
    return value


def sanitize(value: JsonValue, known_secrets: Iterable[str] = ()) -> JsonValue:
    secrets = tuple(secret for secret in known_secrets if secret)

    def visit(item: JsonValue, key: str | None = None) -> JsonValue:
        if key is not None and _SECRET_KEY.search(key):
            return "<redacted>"
        if isinstance(item, dict):
            return {child_key: visit(child, child_key) for child_key, child in item.items()}
        if isinstance(item, list):
            return [visit(child) for child in item]
        if isinstance(item, str):
            text = _BEARER.sub("Bearer <redacted>", item)
            text = _OPENAI_KEY.sub("<redacted>", text)
            for secret in secrets:
                text = text.replace(secret, "<redacted>")
            return text
        return item

    return visit(value)


def enforce_serialized_limit(value: JsonValue, max_bytes: int) -> None:
    size = len(canonical_json(value).encode("utf-8"))
    if size > max_bytes:
        raise ObservationLimitError(f"observation is {size} bytes; configured limit is {max_bytes}")


def redact_mapping(mapping: Mapping[str, str], known_secrets: Iterable[str] = ()) -> dict[str, str]:
    redacted = sanitize(dict(mapping), known_secrets)
    assert isinstance(redacted, dict)
    return {str(key): str(value) for key, value in redacted.items()}
