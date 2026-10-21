from __future__ import annotations

import importlib.util
import json
import secrets
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
import yaml

from mcp_behavior import Verdict, verify

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "external-observers"
REQUEST = {"version": 1, "scenario": "invoice", "observer": "projection", "phase": "after"}


def _state(workspace: Path, rows: list[list[Any]]) -> None:
    (workspace / "invoices.json").write_text(
        json.dumps(
            {
                "storage_metadata": "this is deliberately excluded",
                "invoices": [
                    {"invoice_id": row[0], "total_cents": row[1]} for row in reversed(rows)
                ],
            }
        ),
        encoding="utf-8",
    )
    with closing(sqlite3.connect(workspace / "invoices.sqlite")) as connection:
        connection.execute(
            "CREATE TABLE invoices (invoice_id TEXT PRIMARY KEY, total_cents INTEGER)"
        )
        connection.executemany("INSERT INTO invoices VALUES (?, ?)", rows)
        connection.commit()


def _probe(
    kind: str, workspace: Path, request: object = REQUEST
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXAMPLE / f"{kind}_probe.py")],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        cwd=workspace,
        timeout=10,
        check=False,
    )


def _document(workspace: Path, drift: int = 0) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("external_example_runner", EXAMPLE / "run.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.contract_document(workspace, drift)  # type: ignore[no-any-return]


def _verify(workspace: Path, document: dict[str, Any]) -> Any:
    contract = workspace / "contract.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return verify(contract, workspace / "evidence")


def test_external_probes_share_semantics_without_writing_sources(tmp_path: Path) -> None:
    _state(tmp_path, [["z-last", 200], ["a-first", 100], ["é", 300]])
    files = [tmp_path / "invoices.json", tmp_path / "invoices.sqlite"]
    before = [path.read_bytes() for path in files]
    outputs = [_probe(kind, tmp_path) for kind in ("json", "sqlite")]
    assert all(output.returncode == 0 for output in outputs)
    assert outputs[0].stdout == outputs[1].stdout
    assert json.loads(outputs[0].stdout) == {
        "version": 1,
        "state": "present",
        "columns": ["invoice_id", "total_cents"],
        "rows": [["a-first", 100], ["z-last", 200], ["é", 300]],
    }
    assert [path.read_bytes() for path in files] == before


@pytest.mark.parametrize("kind", ["json", "sqlite"])
def test_external_probes_reject_unknown_protocol_version(tmp_path: Path, kind: str) -> None:
    result = _probe(kind, tmp_path, {**REQUEST, "version": 2})
    assert result.returncode == 2
    assert result.stdout == ""
    assert "probe capture failed" in result.stderr


@pytest.mark.parametrize("kind", ["json", "sqlite"])
def test_external_probes_reject_excess_rows(tmp_path: Path, kind: str) -> None:
    _state(tmp_path, [[f"inv-{index:04d}", index] for index in range(1001)])
    result = _probe(kind, tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""


@pytest.mark.parametrize("drift, verdict", [(0, Verdict.MATCH), (9, Verdict.DIVERGE)])
def test_external_projections_use_core_comparisons(
    tmp_path: Path, drift: int, verdict: Verdict
) -> None:
    report = _verify(tmp_path, _document(tmp_path, drift))
    assert report.verdict is verdict
    assert len(report.scenarios[0].effects) == 2
    assert all(effect.verdict is verdict for effect in report.scenarios[0].effects)
    if drift:
        assert all(
            effect.differences[0].path.endswith("rows[0][1]")
            for effect in report.scenarios[0].effects
        )


@pytest.mark.parametrize(
    "failure", ["exit", "invalid-json", "output-limit", "log-limit", "timeout"]
)
def test_core_owns_failed_probe_verdict_and_bounds(tmp_path: Path, failure: str) -> None:
    document = _document(tmp_path)
    observer = document["scenarios"][0]["observers"][0]
    scripts = {
        "exit": "raise SystemExit(4)",
        "invalid-json": "print('not JSON')",
        "output-limit": "import json; print(json.dumps('x'*70000))",
        "log-limit": "import sys; print('x'*140000, file=sys.stderr)",
        "timeout": "import time; time.sleep(10)",
    }
    observer["command"] = [sys.executable, "-c", scripts[failure]]
    if failure == "timeout":
        observer["timeout"] = 0.2
    report = _verify(tmp_path, document)
    assert report.verdict is Verdict.INCONCLUSIVE
    assert report.scenarios[0].effects[0].verdict is Verdict.INCONCLUSIVE
    messages = {
        "exit": "exited with code 4",
        "invalid-json": "did not return one JSON value",
        "output-limit": "configured limit is 65536",
        "log-limit": "131072-byte log limit",
        "timeout": "timed out after 0.2 seconds",
    }
    assert messages[failure] in report.scenarios[0].error


def test_core_redacts_registered_values_from_external_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = secrets.token_urlsafe(32)
    monkeypatch.setenv("MCP_BEHAVIOR_PROBE_TEST_VALUE", value)
    _state(tmp_path, [[value, 10000]])
    document = _document(tmp_path)
    document["targets"]["candidate"]["command"] = [
        sys.executable,
        str(ROOT / "examples" / "expectations" / "server.py"),
    ]
    document["scenarios"][0]["calls"] = [
        {"tool": "echo", "arguments": {"message": "ready"}, "expect": {"outcome": "success"}}
    ]
    for observer in document["scenarios"][0]["observers"]:
        observer["env"] = {"PROBE_VALUE": {"from_env": "MCP_BEHAVIOR_PROBE_TEST_VALUE"}}
        observer["expect"] = {"contains": {"state": "present"}}
    report = _verify(tmp_path, document)
    assert report.verdict is Verdict.MATCH
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "evidence").rglob("*")
        if path.is_file()
    )
    assert value not in persisted
    assert "<redacted>" in persisted
    assert all(
        effect.candidate["rows"][0][0] == "<redacted>" for effect in report.scenarios[0].effects
    )
