from __future__ import annotations

import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml

from mcp_behavior import Verdict, verify

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _example_contract(tmp_path: Path, example: str, filename: str = "mcp-behavior.yaml") -> Path:
    source = EXAMPLES / example
    document: dict[str, Any] = yaml.safe_load((source / filename).read_text(encoding="utf-8"))
    for name, target in document["targets"].items():
        target["command"][0] = sys.executable
        target["command"][1] = str(source / target["command"][1])
        target["cwd"] = str(tmp_path / name)
        target["workspace"] = str(tmp_path / name)
    for scenario in document["scenarios"]:
        for phase in ("setup", "cleanup"):
            for action in scenario.get(phase, []):
                action["command"][0] = sys.executable
                if action["command"][1].endswith(".py"):
                    action["command"][1] = str(source / action["command"][1])
    contract = tmp_path / filename
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return contract


def test_unicode_file_and_tree_observations_are_stable(tmp_path: Path) -> None:
    contract = _example_contract(tmp_path, "unicode-files")
    first = verify(contract, tmp_path / "evidence-first")
    second = verify(contract, tmp_path / "evidence-second")
    assert first.verdict is second.verdict is Verdict.MATCH
    assert first.semantic_digest == second.semantic_digest
    scenario = first.scenarios[0]
    assert scenario.calls[0].verdict is Verdict.MATCH
    file_value = scenario.effects[0].candidate
    assert isinstance(file_value, dict)
    assert file_value["encoding"] == "utf-8"
    assert file_value["text"] == "Hello, 世界!\n"
    tree = scenario.effects[1].candidate
    assert isinstance(tree, dict)
    entries = tree["entries"]
    assert isinstance(entries, list)
    raw_paths = [entry["path"] for entry in entries if isinstance(entry, dict)]
    assert all(isinstance(path, str) for path in raw_paths)
    assert raw_paths == sorted(raw_paths)
    assert [unicodedata.normalize("NFC", str(path)) for path in raw_paths] == [
        "A.txt",
        "café-猫.txt",
        "z.txt",
        "π.txt",
        "猫.txt",
    ]
