from __future__ import annotations

import pytest

from mcp_behavior.comparison import assert_observation, compare_values
from mcp_behavior.models import (
    AssertionSpec,
    ComparisonSpec,
    NormalizationSpec,
    Observation,
    Verdict,
    VerificationReport,
    aggregate_verdict,
)
from mcp_behavior.normalization import (
    JsonPathError,
    ObservationLimitError,
    enforce_serialized_limit,
    get_path,
    normalize,
    parse_json_path,
    sanitize,
    semantic_digest,
)


def test_json_paths_are_intentionally_small_and_predictable() -> None:
    value = {"items": [{"id": 7}]}

    assert parse_json_path("$.items[0].id") == ("items", 0, "id")
    assert get_path(value, "$.items[0].id") == (True, 7)
    assert get_path(value, "$.items[1]") == (False, None)

    with pytest.raises(JsonPathError, match="must start"):
        parse_json_path("items[0]")
    with pytest.raises(JsonPathError, match="unsupported"):
        parse_json_path("$.items[*]")


def test_json_paths_accept_quoted_object_keys() -> None:
    value = {"_meta": {"io.modelcontextprotocol/serverInfo": {"name": "server"}}}
    path = "$._meta['io.modelcontextprotocol/serverInfo'].name"
    assert get_path(value, path) == (True, "server")


def test_normalization_is_explicit_and_does_not_mutate_input() -> None:
    value = {
        "request_id": "req-raw",
        "created_at": "2026-08-08T12:00:00Z",
        "nested": {"secret": "visible", "remove": 1},
        "url": "http://127.0.0.1:43123/path",
    }
    spec = NormalizationSpec(
        ignore=("$.nested.remove",),
        redact=("$.nested.secret",),
        replace=(("$.url", "<local-url>"),),
        builtins=("request_ids", "timestamps"),
    )

    result = normalize(value, spec)

    assert result == {
        "request_id": "<request-id>",
        "created_at": "<timestamp>",
        "nested": {"secret": "<redacted>"},
        "url": "<local-url>",
    }
    assert value["request_id"] == "req-raw"
    assert value["nested"] == {"secret": "visible", "remove": 1}


def test_sanitizer_redacts_sensitive_keys_and_known_values() -> None:
    value = {
        "Authorization": "Bearer abc.def",
        "message": "token is private-value and sk-abcdefghijklmnop",
        "nested": [{"password": "hunter2"}],
    }

    assert sanitize(value, ["private-value"]) == {
        "Authorization": "<redacted>",
        "message": "token is <redacted> and <redacted>",
        "nested": [{"password": "<redacted>"}],
    }


def test_sanitizer_redacts_common_token_shapes_in_unstructured_text() -> None:
    github = "gh" + "p_abcdefghijklmnopqrstuvwxyz123456"
    aws = "AK" + "IAABCDEFGHIJKLMNOP"
    slack = "xo" + "xb-1234567890-abcdefghijklmnop"
    value = {"message": f"github {github} aws {aws} slack {slack}"}

    assert sanitize(value) == {"message": "github <redacted> aws <redacted> slack <redacted>"}


def test_observation_size_limit_fails_closed() -> None:
    enforce_serialized_limit({"ok": "small"}, 100)
    with pytest.raises(ObservationLimitError, match="configured limit"):
        enforce_serialized_limit({"too_big": "x" * 100}, 20)


def test_semantic_digest_ignores_dictionary_insertion_order() -> None:
    assert semantic_digest({"a": 1, "b": 2}) == semantic_digest({"b": 2, "a": 1})


def test_comparison_supports_tolerance_and_declared_unordered_lists() -> None:
    reference = {"score": 1.0, "items": [{"id": 2}, {"id": 1}]}
    candidate = {"score": 1.01, "items": [{"id": 1}, {"id": 2}]}

    assert not compare_values(
        reference,
        candidate,
        ComparisonSpec(numeric_tolerance=0.02, unordered=("$.items",)),
    )
    differences = compare_values(reference, candidate, ComparisonSpec())
    assert differences[0].path == "$.items[0].id"


def test_exact_text_and_bytes_comparisons_have_distinct_semantics() -> None:
    exact = compare_values(1, 1.0, ComparisonSpec(kind="exact"))
    assert exact[0].message == "exact values differ"

    text = compare_values(
        {"encoding": "utf-8", "text": "first\nold\n"},
        {"encoding": "utf-8", "text": "first\nnew\n"},
        ComparisonSpec(kind="text"),
    )
    assert text[0].path == "$[line:2]"
    assert text[0].reference == "old"
    assert text[0].candidate == "new"

    binary = compare_values(
        {"encoding": "base64", "data": "AAEC"},
        {"encoding": "base64", "data": "AAED"},
        ComparisonSpec(kind="bytes"),
    )
    assert binary[0].path == "$[byte:2]"
    assert binary[0].reference == "02"
    assert binary[0].candidate == "03"


def test_assertions_cover_outcome_subset_paths_and_absence() -> None:
    observation = Observation(value={"status": "ok", "details": {"count": 3}, "items": ["a", "b"]})
    assertion = AssertionSpec(
        contains={"items": ["b"]},
        has_contains=True,
        paths_equal=(("$.details.count", 3),),
        paths_absent=("$.debug",),
    )

    assert not assert_observation(observation, assertion, ComparisonSpec())

    errors = assert_observation(
        Observation(value={"message": "failed"}, is_error=True),
        AssertionSpec(outcome="success"),
        ComparisonSpec(),
    )
    assert errors[0].path == "$.is_error"


def test_verdict_aggregation_never_treats_uncertainty_as_match() -> None:
    assert aggregate_verdict([Verdict.MATCH, Verdict.MATCH]) is Verdict.MATCH
    assert aggregate_verdict([Verdict.MATCH, Verdict.INCONCLUSIVE]) is Verdict.INCONCLUSIVE
    assert aggregate_verdict([Verdict.INCONCLUSIVE, Verdict.DIVERGE]) is Verdict.DIVERGE


def test_public_exit_codes_are_stable() -> None:
    common = {
        "contract": "contract.yaml",
        "mode": "expectations",
        "scenarios": (),
        "semantic_digest": "digest",
        "evidence_dir": "evidence",
    }
    assert VerificationReport(verdict=Verdict.MATCH, **common).exit_code == 0
    assert VerificationReport(verdict=Verdict.DIVERGE, **common).exit_code == 1
    assert VerificationReport(verdict=Verdict.INCONCLUSIVE, **common).exit_code == 2
