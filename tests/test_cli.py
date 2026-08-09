from __future__ import annotations

from pathlib import Path

from mcp_behavior.cli import main
from mcp_behavior.contract import load_contract


def test_init_writes_a_valid_expectations_contract(tmp_path: Path) -> None:
    output = tmp_path / "behavior.yaml"
    assert main(["init", str(output)]) == 0
    contract = load_contract(output)
    assert contract.name == "my-mcp-server"
    assert contract.mode == "expectations"


def test_init_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    output = tmp_path / "behavior.yaml"
    output.write_text("mine", encoding="utf-8")
    assert main(["init", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "mine"
