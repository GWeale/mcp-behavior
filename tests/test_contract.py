from __future__ import annotations

from pathlib import Path

import pytest

from mcp_behavior.contract import ContractError, load_contract


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "behavior.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_differential_contract_and_resolves_relative_paths(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
name: price behavior
targets:
  reference:
    transport: stdio
    command: [python, reference.py]
    cwd: servers/reference
  candidate:
    transport: http
    url: http://127.0.0.1:9000/mcp
scenarios:
  - name: quote one item
    tags: [smoke, pricing]
    setup:
      - command: [python, prepare.py]
    calls:
      - name: quote
        tool: quote_price
        arguments: {sku: A1, quantity: 1}
        normalize:
          builtins: [request_ids]
          ignore: [$.generated_at]
        compare:
          numeric_tolerance: 0.01
          unordered: [$.items]
    observers:
      - name: receipt
        kind: file
        root: sandbox
        path: receipt.json
        phase: delta
    cleanup:
      - command: [python, cleanup.py]
timeouts: {connect: 5, operation: 10, total: 30}
limits: {output_bytes: 4096, log_bytes: 2048}
""",
    )

    contract = load_contract(path)

    assert contract.mode == "differential"
    assert contract.name == "price behavior"
    assert contract.targets["reference"].cwd == (tmp_path / "servers/reference").resolve()
    assert contract.targets["reference"].command == ("python", "reference.py")
    assert contract.scenarios[0].tags == ("smoke", "pricing")
    assert contract.scenarios[0].observers[0].root == Path("sandbox")
    assert contract.scenarios[0].calls[0].comparison.numeric_tolerance == 0.01
    assert contract.timeouts.total == 30
    assert contract.limits.output_bytes == 4096


def test_expectations_are_required_without_reference_or_baseline(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
targets:
  candidate:
    transport: stdio
    command: [python, server.py]
scenarios:
  - name: missing expectation
    calls:
      - tool: status
""",
    )

    with pytest.raises(ContractError, match="required when no reference"):
        load_contract(path)


def test_explicit_expectation_contract_is_valid(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
targets:
  candidate:
    transport: stdio
    command: [python, server.py]
scenarios:
  - name: status
    calls:
      - tool: status
        expect:
          outcome: success
          contains: {status: ok}
          paths_equal: {$.count: 1}
          paths_absent: [$.debug]
""",
    )

    contract = load_contract(path)

    assert contract.mode == "expectations"
    assertion = contract.scenarios[0].calls[0].assertion
    assert assertion is not None
    assert assertion.has_contains
    assert assertion.paths_equal == (("$.count", 1),)


def test_sensitive_target_values_must_be_environment_references(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
targets:
  candidate:
    transport: http
    url: https://example.test/mcp
    headers:
      Authorization: Bearer plaintext
scenarios:
  - name: status
    calls:
      - tool: status
        expect: {equals: {status: ok}}
""",
    )

    with pytest.raises(ContractError, match="sensitive values must use from_env"):
        load_contract(path)


@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@example.test/mcp",
        "https://example.test/mcp?api_key=plaintext",
    ],
)
def test_http_urls_cannot_embed_credentials(tmp_path: Path, url: str) -> None:
    path = _write(
        tmp_path,
        f"""
version: 1
targets:
  candidate:
    transport: http
    url: {url}
scenarios:
  - name: status
    calls:
      - tool: status
        expect: {{outcome: success}}
""",
    )

    with pytest.raises(ContractError, match=r"credentials|credential-like"):
        load_contract(path)


def test_environment_reference_resolves_without_entering_description(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_MCP_TOKEN", "private-value")
    path = _write(
        tmp_path,
        """
version: 1
targets:
  candidate:
    transport: http
    url: https://example.test/mcp
    headers:
      Authorization:
        from_env: TEST_MCP_TOKEN
        template: Bearer {value}
scenarios:
  - name: status
    calls:
      - tool: status
        expect: {equals: {status: ok}}
""",
    )

    contract = load_contract(path)
    source = contract.targets["candidate"].headers["Authorization"]

    assert source.describe() == {
        "from_env": "TEST_MCP_TOKEN",
        "template": "Bearer {value}",
    }
    assert source.resolve(path, "$.targets.candidate.headers.Authorization") == (
        "Bearer private-value",
        "private-value",
    )
    assert "private-value" not in str(source.describe())


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        ("unknown: true", "unknown fields"),
        ("name: duplicate\nname: duplicate", "duplicate key"),
        ("name: &shared aliased\ncopy: *shared", "aliases are not supported"),
    ],
)
def test_rejects_unknown_fields_duplicates_and_aliases(
    tmp_path: Path, fragment: str, message: str
) -> None:
    path = _write(
        tmp_path,
        f"""
version: 1
{fragment}
targets:
  candidate:
    transport: stdio
    command: [python, server.py]
scenarios:
  - name: status
    calls:
      - tool: status
        expect: {{equals: {{status: ok}}}}
""",
    )

    with pytest.raises(ContractError, match=message):
        load_contract(path)


def test_rejects_invalid_transport_shapes(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
targets:
  candidate:
    transport: stdio
    command: [python, server.py]
    url: https://example.test/mcp
scenarios:
  - name: status
    calls:
      - tool: status
        expect: {equals: {status: ok}}
""",
    )

    with pytest.raises(ContractError, match="cannot declare url"):
        load_contract(path)


def test_literal_scenario_variables_preserve_types_and_expand_strings(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
variables:
  item_id: item-42
  quantity: 3
  expected: {status: active}
targets:
  candidate:
    transport: stdio
    command: [python, server.py]
scenarios:
  - name: verify ${item_id}
    setup:
      - command: [python, prepare.py, "--item=${item_id}"]
    calls:
      - tool: lookup
        arguments:
          id: ${item_id}
          quantity: ${quantity}
        expect:
          contains: ${expected}
""",
    )

    contract = load_contract(path)

    scenario = contract.scenarios[0]
    assert scenario.name == "verify item-42"
    assert scenario.setup[0].command[-1] == "--item=item-42"
    assert scenario.calls[0].arguments == {"id": "item-42", "quantity": 3}
    assert scenario.calls[0].assertion is not None
    assert scenario.calls[0].assertion.contains == {"status": "active"}


def test_scenario_variables_cannot_read_environment_secrets(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
variables:
  api_token: plaintext
targets:
  candidate: {transport: stdio, command: [python, server.py]}
scenarios:
  - name: status
    calls:
      - tool: status
        expect: {outcome: success}
""",
    )

    with pytest.raises(ContractError, match="cannot hold credentials"):
        load_contract(path)


def test_contract_rejects_invalid_json_paths_and_non_json_options(tmp_path: Path) -> None:
    invalid_path = _write(
        tmp_path,
        """
version: 1
targets:
  candidate: {transport: stdio, command: [python, server.py]}
scenarios:
  - name: status
    calls:
      - tool: status
        normalize: {ignore: ["$.items[*]"]}
        expect: {outcome: success}
""",
    )
    with pytest.raises(ContractError, match="unsupported JSON path"):
        load_contract(invalid_path)

    invalid_options = _write(
        tmp_path,
        """
version: 1
targets:
  candidate: {transport: stdio, command: [python, server.py]}
scenarios:
  - name: status
    calls:
      - tool: status
        compare: {kind: text, numeric_tolerance: 0.1}
        expect: {outcome: success}
""",
    )
    with pytest.raises(ContractError, match="only valid for json"):
        load_contract(invalid_options)
