"""Deterministic value comparison and explicit expectation checks."""

from __future__ import annotations

import base64
import binascii
import copy
import difflib
import math
from typing import Any

from .models import AssertionSpec, ComparisonSpec, Difference, JsonValue, Observation
from .normalization import canonical_json, get_path, set_path


def compare_observations(
    reference: Observation,
    candidate: Observation,
    spec: ComparisonSpec,
) -> tuple[Difference, ...]:
    differences: list[Difference] = []
    if reference.is_error != candidate.is_error:
        differences.append(
            Difference(
                path="$.is_error",
                message="tool error outcome changed",
                reference=reference.is_error,
                candidate=candidate.is_error,
            )
        )
    differences.extend(compare_values(reference.value, candidate.value, spec))
    return tuple(differences)


def compare_values(
    reference: JsonValue,
    candidate: JsonValue,
    spec: ComparisonSpec,
) -> tuple[Difference, ...]:
    if spec.kind not in {"exact", "json", "text", "bytes"}:
        return (
            Difference(
                path="$",
                message=f"unsupported comparison kind {spec.kind!r}",
                reference=reference,
                candidate=candidate,
            ),
        )

    if spec.kind == "exact":
        if type(reference) is type(candidate) and reference == candidate:
            return ()
        return (
            Difference(
                path="$",
                message="exact values differ",
                reference=reference,
                candidate=candidate,
            ),
        )
    if spec.kind == "text":
        return _compare_text(reference, candidate)
    if spec.kind == "bytes":
        return _compare_bytes(reference, candidate)

    left = copy.deepcopy(reference)
    right = copy.deepcopy(candidate)
    for path in spec.unordered:
        _sort_list_at_path(left, path)
        _sort_list_at_path(right, path)

    differences: list[Difference] = []
    _diff(left, right, "$", differences, spec.numeric_tolerance)
    return tuple(differences)


def _compare_text(reference: JsonValue, candidate: JsonValue) -> tuple[Difference, ...]:
    left = _text_value(reference)
    right = _text_value(candidate)
    if left is None or right is None:
        return (
            Difference(
                path="$",
                message=(
                    "text comparison requires strings or UTF-8 file observations "
                    "with encoding and text fields"
                ),
                reference=reference,
                candidate=candidate,
            ),
        )
    if left == right:
        return ()
    differences: list[Difference] = []
    matcher = difflib.SequenceMatcher(a=left.splitlines(), b=right.splitlines(), autojunk=False)
    for operation, left_start, left_end, right_start, right_end in matcher.get_opcodes():
        if operation == "equal":
            continue
        line = min(left_start, right_start) + 1
        differences.append(
            Difference(
                path=f"$[line:{line}]",
                message=f"text lines {operation}",
                reference="\n".join(left.splitlines()[left_start:left_end]),
                candidate="\n".join(right.splitlines()[right_start:right_end]),
            )
        )
    return tuple(differences)


def _compare_bytes(reference: JsonValue, candidate: JsonValue) -> tuple[Difference, ...]:
    left = _bytes_value(reference)
    right = _bytes_value(candidate)
    if left is None or right is None:
        return (
            Difference(
                path="$",
                message=(
                    "bytes comparison requires a file observation with encoding plus data/text"
                ),
                reference=reference,
                candidate=candidate,
            ),
        )
    if left == right:
        return ()
    shared = min(len(left), len(right))
    offset = next((index for index in range(shared) if left[index] != right[index]), shared)
    if offset == shared and len(left) != len(right):
        message = f"byte length changed from {len(left)} to {len(right)}"
    else:
        message = f"bytes differ at offset {offset}"
    return (
        Difference(
            path=f"$[byte:{offset}]",
            message=message,
            reference=left[offset : offset + 16].hex(),
            candidate=right[offset : offset + 16].hex(),
        ),
    )


def _text_value(value: JsonValue) -> str | None:
    if isinstance(value, str):
        return value
    if (
        isinstance(value, dict)
        and value.get("encoding") == "utf-8"
        and isinstance(value.get("text"), str)
    ):
        text = value["text"]
        assert isinstance(text, str)
        return text
    return None


def _bytes_value(value: JsonValue) -> bytes | None:
    if not isinstance(value, dict):
        return None
    encoding = value.get("encoding")
    if encoding == "utf-8" and isinstance(value.get("text"), str):
        text = value["text"]
        assert isinstance(text, str)
        return text.encode("utf-8")
    if encoding == "base64" and isinstance(value.get("data"), str):
        data = value["data"]
        assert isinstance(data, str)
        try:
            return base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError):
            return None
    return None


def assert_observation(
    observation: Observation,
    assertion: AssertionSpec,
    comparison: ComparisonSpec,
) -> tuple[Difference, ...]:
    differences: list[Difference] = []
    expected_error = assertion.outcome == "error"
    if observation.is_error != expected_error:
        differences.append(
            Difference(
                path="$.is_error",
                message=f"expected {assertion.outcome} outcome",
                reference=expected_error,
                candidate=observation.is_error,
            )
        )
    if assertion.has_equals:
        differences.extend(compare_values(assertion.equals, observation.value, comparison))
    if assertion.has_contains:
        _contains(
            assertion.contains, observation.value, "$", differences, comparison.numeric_tolerance
        )
    for path, expected in assertion.paths_equal:
        exists, actual = get_path(observation.value, path)
        if not exists:
            differences.append(
                Difference(path=path, message="expected path is missing", reference=expected)
            )
        else:
            _diff(expected, actual, path, differences, comparison.numeric_tolerance)
    for path in assertion.paths_absent:
        exists, actual = get_path(observation.value, path)
        if exists:
            differences.append(
                Difference(path=path, message="expected path to be absent", candidate=actual)
            )
    return tuple(differences)


def _sort_list_at_path(value: JsonValue, path: str) -> None:
    exists, current = get_path(value, path)
    if not exists or not isinstance(current, list):
        return
    ordered = sorted(current, key=canonical_json)
    if path == "$":
        current[:] = ordered
    else:
        set_path(value, path, ordered)


def _diff(
    reference: JsonValue,
    candidate: JsonValue,
    path: str,
    differences: list[Difference],
    tolerance: float | None,
) -> None:
    if _numbers_equal(reference, candidate, tolerance):
        return
    if type(reference) is not type(candidate):
        differences.append(
            Difference(
                path=path,
                message=(
                    f"type changed from {type(reference).__name__} to {type(candidate).__name__}"
                ),
                reference=reference,
                candidate=candidate,
            )
        )
        return
    if isinstance(reference, dict) and isinstance(candidate, dict):
        for key in sorted(reference.keys() - candidate.keys()):
            differences.append(
                Difference(
                    path=_child_path(path, key),
                    message="candidate key is missing",
                    reference=reference[key],
                )
            )
        for key in sorted(candidate.keys() - reference.keys()):
            differences.append(
                Difference(
                    path=_child_path(path, key),
                    message="candidate has an additional key",
                    candidate=candidate[key],
                )
            )
        for key in sorted(reference.keys() & candidate.keys()):
            _diff(
                reference[key],
                candidate[key],
                _child_path(path, key),
                differences,
                tolerance,
            )
        return
    if isinstance(reference, list) and isinstance(candidate, list):
        if len(reference) != len(candidate):
            differences.append(
                Difference(
                    path=path,
                    message=f"list length changed from {len(reference)} to {len(candidate)}",
                    reference=reference,
                    candidate=candidate,
                )
            )
            return
        for index, (left, right) in enumerate(zip(reference, candidate, strict=True)):
            _diff(left, right, f"{path}[{index}]", differences, tolerance)
        return
    if reference != candidate:
        differences.append(
            Difference(path=path, message="values differ", reference=reference, candidate=candidate)
        )


def _contains(
    expected: JsonValue,
    actual: JsonValue,
    path: str,
    differences: list[Difference],
    tolerance: float | None,
) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, value in expected.items():
            child = _child_path(path, key)
            if key not in actual:
                differences.append(
                    Difference(path=child, message="contained key is missing", reference=value)
                )
            else:
                _contains(value, actual[key], child, differences, tolerance)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        remaining = list(actual)
        for item in expected:
            match_index = next(
                (
                    index
                    for index, candidate in enumerate(remaining)
                    if not compare_values(
                        item,
                        candidate,
                        ComparisonSpec(numeric_tolerance=tolerance),
                    )
                ),
                None,
            )
            if match_index is None:
                differences.append(
                    Difference(
                        path=path,
                        message="expected list item is missing",
                        reference=item,
                        candidate=actual,
                    )
                )
            else:
                remaining.pop(match_index)
        return
    _diff(expected, actual, path, differences, tolerance)


def _numbers_equal(reference: Any, candidate: Any, tolerance: float | None) -> bool:
    if isinstance(reference, bool) or isinstance(candidate, bool):
        return False
    if isinstance(reference, (int, float)) and isinstance(candidate, (int, float)):
        if tolerance is None:
            return reference == candidate
        return math.isclose(float(reference), float(candidate), rel_tol=0.0, abs_tol=tolerance)
    return False


def _child_path(parent: str, key: str) -> str:
    if key.replace("_", "a").replace("-", "a").isalnum() and not key[:1].isdigit():
        return f"{parent}.{key}"
    return f"{parent}[{key!r}]"
