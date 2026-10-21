"""Executable repeat-summary design model; not a production repeat runner."""

from __future__ import annotations

import hashlib
import json
from collections import Counter


def summarize(attempts: list[tuple[str, str]], requested: int) -> dict[str, object]:
    """Accept sanitized verdict/digest pairs; exclude every volatile run field."""
    if not 1 <= requested <= 100 or not 0 <= len(attempts) <= requested:
        raise ValueError("invalid attempt count")
    if any(v not in {"MATCH", "DIVERGE", "INCONCLUSIVE"} for v, _ in attempts):
        raise ValueError("unknown verdict")
    if any(len(d) != 64 or any(c not in "0123456789abcdef" for c in d) for _, d in attempts):
        raise ValueError("expected a semantic SHA-256 digest")
    counts = Counter(v for v, _ in attempts)
    complete = len(attempts) == requested and counts["INCONCLUSIVE"] == 0
    verdict = "DIVERGE" if counts["DIVERGE"] else "MATCH" if complete else "INCONCLUSIVE"
    stability = "unknown"
    if complete:
        if len(counts) > 1:
            stability = "variable-verdict"
        elif len({digest for _, digest in attempts}) > 1:
            stability = "variable-observation"
        else:
            stability = "stable"
    payload: dict[str, object] = {
        "kind": "repeat-summary",
        "schema_version": 1,
        "policy": {"attempts": requested, "workspace": "fresh", "total_seconds": 120},
        "attempts": [
            {"ordinal": i, "verdict": verdict, "semantic_digest": digest}
            for i, (verdict, digest) in enumerate(attempts, start=1)
        ],
        "counts": {v: counts[v] for v in ("MATCH", "DIVERGE", "INCONCLUSIVE")},
        "complete": complete,
        "verdict": verdict,
        "stability": stability,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**payload, "semantic_digest": hashlib.sha256(canonical).hexdigest()}


def main() -> None:
    matching, different, uncertain = (
        ("MATCH", "a" * 64),
        ("DIVERGE", "b" * 64),
        (
            "INCONCLUSIVE",
            "c" * 64,
        ),
    )
    first = summarize([matching] * 3, 3)
    assert first == summarize([matching] * 3, 3)
    assert first["stability"] == "stable" and first["verdict"] == "MATCH"
    assert first["semantic_digest"] != summarize([matching] * 2, 2)["semantic_digest"]
    assert summarize([matching, different], 2)["stability"] == "variable-verdict"
    assert summarize([matching, ("MATCH", "d" * 64)], 2)["stability"] == "variable-observation"
    assert summarize([matching, uncertain], 2)["verdict"] == "INCONCLUSIVE"
    assert summarize([different, uncertain], 2)["verdict"] == "DIVERGE"
    assert summarize([different, uncertain], 2)["stability"] == "unknown"
    assert summarize([matching], 2)["verdict"] == "INCONCLUSIVE"
    assert summarize([], 2)["verdict"] == "INCONCLUSIVE"
    print("repeat-summary design checks passed")
    print(json.dumps(first, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
