"""Shared protocol for these two examples, not an installed extension API."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

MAX_BYTES = 65_536
MAX_ROWS = 1000


def invoice_value(rows: list[list[Any]], *, state: str = "present") -> dict[str, Any]:
    if len(rows) > MAX_ROWS:
        raise ValueError("row limit")
    identifiers = []
    for identifier, total in rows:
        if not isinstance(identifier, str) or not identifier or type(total) is not int:
            raise ValueError("invoice shape")
        identifiers.append(identifier)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate key")
    return {
        "version": 1,
        "state": state,
        "columns": ["invoice_id", "total_cents"],
        "rows": sorted(rows, key=lambda row: row[0]),
    }


def run(capture: Callable[[], dict[str, Any]]) -> int:
    try:
        payload = sys.stdin.buffer.read(8193)
        if len(payload) > 8192:
            raise ValueError("input limit")
        request = json.loads(payload)
        if (
            not isinstance(request, dict)
            or set(request) != {"version", "scenario", "observer", "phase"}
            or type(request["version"]) is not int
            or request["version"] != 1
            or request["phase"] not in {"before", "after"}
            or not isinstance(request["scenario"], str)
            or not isinstance(request["observer"], str)
        ):
            raise ValueError("unsupported request")
        value = json.dumps(capture(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(value.encode("utf-8")) > MAX_BYTES:
            raise ValueError("output limit")
    except Exception:
        # Do not echo untrusted input, database errors, paths, or credentials.
        print("probe capture failed (invalid input, state, or limit)", file=sys.stderr)
        return 2
    print(value)
    return 0
