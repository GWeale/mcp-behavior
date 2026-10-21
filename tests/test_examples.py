from __future__ import annotations

import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pytest
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


@pytest.mark.parametrize("example", ["unicode-files", "binary-file"])
def test_example_cleanup_works_without_site_packages(tmp_path: Path, example: str) -> None:
    result = subprocess.run(
        [sys.executable, "-S", str(EXAMPLES / example / "server.py"), "--cleanup"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr


def test_binary_example_matches_and_reports_the_first_changed_byte(tmp_path: Path) -> None:
    matching = _example_contract(tmp_path / "matching", "binary-file")
    wrong = _example_contract(tmp_path / "wrong", "binary-file", "wrong-byte.yaml")
    good_report = verify(matching, tmp_path / "matching-evidence")
    wrong_report = verify(wrong, tmp_path / "wrong-evidence")
    assert good_report.verdict is Verdict.MATCH
    assert good_report.exit_code == 0
    assert wrong_report.verdict is Verdict.DIVERGE
    assert wrong_report.exit_code == 1
    assert wrong_report.scenarios[0].calls[0].verdict is Verdict.MATCH
    effect = wrong_report.scenarios[0].effects[0]
    assert effect.verdict is Verdict.DIVERGE
    assert len(effect.differences) == 1
    assert effect.differences[0].path == "$[byte:7]"
    assert effect.differences[0].message == "bytes differ at offset 7"
    assert effect.differences[0].reference.startswith("07")
    assert effect.differences[0].candidate.startswith("08")
