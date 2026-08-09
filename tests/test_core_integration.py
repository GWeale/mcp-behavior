from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import yaml

from mcp_behavior import Verdict, record, verify
from mcp_behavior.cli import main

FIXTURE_SERVER = Path(__file__).parent / "fixtures" / "server.py"


def _write_contract(
    tmp_path: Path,
    *,
    baseline: bool = False,
    variant: str = "stable",
    reference_variant: str | None = None,
) -> Path:
    targets: dict[str, object] = {
        "candidate": {
            "transport": "stdio",
            "command": [sys.executable, str(FIXTURE_SERVER)],
            "cwd": "candidate",
            "workspace": "candidate",
            "env": {"FIXTURE_VARIANT": variant},
        }
    }
    if reference_variant is not None:
        targets["reference"] = {
            "transport": "stdio",
            "command": [sys.executable, str(FIXTURE_SERVER)],
            "cwd": "reference",
            "workspace": "reference",
            "env": {"FIXTURE_VARIANT": reference_variant},
        }
    document: dict[str, object] = {
        "version": 1,
        "name": "fixture",
        "timeouts": {"connect": 30, "operation": 30, "total": 300},
        "targets": targets,
        "scenarios": [
            {
                "name": "echo and write",
                "tags": ["smoke"],
                "calls": [
                    {
                        "name": "echo",
                        "tool": "echo",
                        "arguments": {"message": "hello"},
                        "normalize": {"builtins": ["uuids"]},
                        **(
                            {}
                            if baseline or reference_variant is not None
                            else {"expect": {"outcome": "success"}}
                        ),
                    },
                    {
                        "name": "write",
                        "tool": "write_note",
                        "arguments": {"content": "hello"},
                        **(
                            {}
                            if baseline or reference_variant is not None
                            else {"expect": {"outcome": "success"}}
                        ),
                    },
                    {
                        "name": "expected error",
                        "tool": "expected_failure",
                        "arguments": {},
                        **(
                            {}
                            if baseline or reference_variant is not None
                            else {"expect": {"outcome": "error"}}
                        ),
                    },
                ],
                "observers": [
                    {
                        "name": "note delta",
                        "kind": "file",
                        "root": ".",
                        "path": "note.txt",
                        "phase": "delta",
                        **(
                            {}
                            if baseline or reference_variant is not None
                            else {
                                "expect": {
                                    "contains": {
                                        "change": "created",
                                        "after": {"state": "present", "text": "hello"},
                                    }
                                }
                            }
                        ),
                    },
                    {
                        "name": "custom probe",
                        "kind": "command",
                        "command": [
                            sys.executable,
                            "-c",
                            (
                                "import json,sys; p=json.load(sys.stdin); "
                                "print(json.dumps({'phase':p['phase'],'scenario':p['scenario']}))"
                            ),
                        ],
                        **(
                            {}
                            if baseline or reference_variant is not None
                            else {
                                "expect": {
                                    "equals": {"phase": "after", "scenario": "echo and write"}
                                }
                            }
                        ),
                    },
                ],
            }
        ],
    }
    if baseline:
        document["baseline"] = "baseline.json"
    for workspace in (tmp_path / "candidate", tmp_path / "reference"):
        workspace.mkdir()
    contract = tmp_path / "behavior.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return contract


def test_expectations_mode_verifies_call_and_effect(tmp_path: Path) -> None:
    contract = _write_contract(tmp_path)
    report = verify(contract, tmp_path / "evidence")
    assert report.verdict is Verdict.MATCH
    assert report.exit_code == 0
    manifest = json.loads((tmp_path / "evidence" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["semantic_digest"] == report.semantic_digest
    assert main(["inspect", str(tmp_path / "evidence"), "--format", "json"]) == 0


def test_differential_mode_reports_a_real_behavior_change(tmp_path: Path) -> None:
    contract = _write_contract(tmp_path, variant="candidate", reference_variant="reference")
    report = verify(contract, tmp_path / "evidence")
    assert report.verdict is Verdict.DIVERGE
    assert any(
        "variant" in difference.path for difference in report.scenarios[0].calls[0].differences
    )


def test_recorded_baseline_detects_later_change(tmp_path: Path) -> None:
    contract = _write_contract(tmp_path, baseline=True, variant="alpha")
    digest = record(contract)
    assert len(digest) == 64
    original = contract.read_text(encoding="utf-8")
    contract.write_text(
        original.replace("FIXTURE_VARIANT: alpha", "FIXTURE_VARIANT: beta"), encoding="utf-8"
    )
    report = verify(contract, tmp_path / "evidence")
    assert report.verdict is Verdict.DIVERGE


def test_secret_environment_values_never_reach_evidence(
    tmp_path: Path, monkeypatch: object
) -> None:
    secret = "test-secret-value-that-must-not-persist"
    monkeypatch.setenv("MCP_BEHAVIOR_FIXTURE_SECRET", secret)  # type: ignore[attr-defined]
    document = {
        "version": 1,
        "name": "secret-redaction",
        "timeouts": {"connect": 30, "operation": 30, "total": 300},
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [sys.executable, str(FIXTURE_SERVER)],
                "cwd": str(tmp_path),
                "env": {"FIXTURE_SECRET": {"from_env": "MCP_BEHAVIOR_FIXTURE_SECRET"}},
            }
        },
        "scenarios": [
            {
                "name": "redact",
                "calls": [
                    {
                        "tool": "reveal_fixture_secret",
                        "expect": {"outcome": "success"},
                    }
                ],
            }
        ],
    }
    contract = tmp_path / "secret.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    evidence = tmp_path / "evidence"
    report = verify(contract, evidence)
    assert report.verdict is Verdict.MATCH
    persisted = "\n".join(
        path.read_text(encoding="utf-8") for path in evidence.rglob("*") if path.is_file()
    )
    assert secret not in persisted
    assert "<redacted>" in persisted


def test_streamable_http_target_uses_official_transport(tmp_path: Path) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    process = subprocess.Popen(
        [sys.executable, str(FIXTURE_SERVER), "--http", str(port)],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port, process)
        document = {
            "version": 1,
            "name": "http-fixture",
            "timeouts": {"connect": 30, "operation": 30, "total": 300},
            "targets": {
                "candidate": {
                    "transport": "http",
                    "url": f"http://127.0.0.1:{port}/mcp",
                    "workspace": str(tmp_path),
                }
            },
            "scenarios": [
                {
                    "name": "http echo",
                    "calls": [
                        {
                            "tool": "echo",
                            "arguments": {"message": "hello over http"},
                            "expect": {"outcome": "success"},
                        }
                    ],
                }
            ],
        }
        contract = tmp_path / "http.yaml"
        contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        report = verify(contract, tmp_path / "http-evidence")
        assert report.verdict is Verdict.MATCH
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _wait_for_port(port: int, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"HTTP fixture exited with {process.returncode}")
        with socket.socket() as connection:
            connection.settimeout(0.1)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise AssertionError("HTTP fixture did not start")


def test_cleanup_runs_after_target_connection_failure(tmp_path: Path) -> None:
    document = {
        "version": 1,
        "name": "cleanup-on-failure",
        "timeouts": {"connect": 2, "operation": 2, "total": 15},
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [str(tmp_path / "missing-server")],
                "cwd": str(tmp_path),
            }
        },
        "scenarios": [
            {
                "name": "cleanup",
                "setup": [
                    {
                        "command": [
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('active.txt').write_text('active')",
                        ]
                    }
                ],
                "calls": [{"tool": "never_called", "expect": {"outcome": "success"}}],
                "cleanup": [
                    {
                        "command": [
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('cleaned.txt').write_text('cleaned')",
                        ]
                    }
                ],
            }
        ],
    }
    contract = tmp_path / "cleanup.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    report = verify(contract, tmp_path / "cleanup-evidence")
    assert report.verdict is Verdict.INCONCLUSIVE
    assert (tmp_path / "cleaned.txt").read_text(encoding="utf-8") == "cleaned"
