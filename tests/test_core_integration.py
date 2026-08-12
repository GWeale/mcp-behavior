from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
import yaml

from mcp_behavior import Verdict, record, verify
from mcp_behavior.cli import main
from mcp_behavior.contract import ContractError

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
    effects = json.loads(
        next((tmp_path / "evidence").glob("scenarios/*/effects.json")).read_text(encoding="utf-8")
    )
    assert all("duration_ms" not in effect for effect in effects["effects"])
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
                    },
                    {
                        "name": "secret request",
                        "tool": "echo",
                        "arguments": {"message": secret},
                        "expect": {"outcome": "success"},
                    },
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
    observation = json.loads(
        next(evidence.glob("scenarios/*/observation.json")).read_text(encoding="utf-8")
    )
    assert observation["calls"][1]["request"] == {"message": "<redacted>"}


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


def test_streamable_http_does_not_follow_redirects_to_undeclared_targets(
    tmp_path: Path,
) -> None:
    redirected_requests = [0]

    class RedirectedHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            redirected_requests[0] += 1
            self.send_response(500)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    redirected = ThreadingHTTPServer(("127.0.0.1", 0), RedirectedHandler)
    redirected_port = int(redirected.server_address[1])

    class ConfiguredHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.send_response(307)
            self.send_header("Location", f"http://127.0.0.1:{redirected_port}/mcp")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    configured = ThreadingHTTPServer(("127.0.0.1", 0), ConfiguredHandler)
    configured_port = int(configured.server_address[1])
    threads = [
        Thread(target=redirected.serve_forever, daemon=True),
        Thread(target=configured.serve_forever, daemon=True),
    ]
    for thread in threads:
        thread.start()
    try:
        document = {
            "version": 1,
            "name": "redirect-boundary",
            "timeouts": {"connect": 5, "operation": 5, "total": 15},
            "targets": {
                "candidate": {
                    "transport": "http",
                    "url": f"http://127.0.0.1:{configured_port}/mcp",
                    "workspace": str(tmp_path),
                }
            },
            "scenarios": [
                {
                    "name": "redirect",
                    "calls": [{"tool": "status", "expect": {"outcome": "success"}}],
                }
            ],
        }
        contract = tmp_path / "redirect.yaml"
        contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

        report = verify(contract, tmp_path / "redirect-evidence")

        assert report.verdict is Verdict.INCONCLUSIVE
        assert redirected_requests == [0]
    finally:
        configured.shutdown()
        redirected.shutdown()
        configured.server_close()
        redirected.server_close()


def test_public_api_selects_scenarios_by_exact_name_and_tag(tmp_path: Path) -> None:
    document = {
        "version": 1,
        "name": "selection",
        "timeouts": {"connect": 30, "operation": 30, "total": 120},
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [sys.executable, str(FIXTURE_SERVER)],
                "cwd": str(tmp_path),
            }
        },
        "scenarios": [
            {
                "name": "alpha",
                "tags": ["smoke"],
                "calls": [
                    {
                        "tool": "echo",
                        "arguments": {"message": "alpha"},
                        "expect": {"outcome": "success"},
                    }
                ],
            },
            {
                "name": "beta",
                "tags": ["slow"],
                "calls": [
                    {
                        "tool": "echo",
                        "arguments": {"message": "beta"},
                        "expect": {"outcome": "success"},
                    }
                ],
            },
        ],
    }
    contract = tmp_path / "selection.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    by_name = verify(contract, tmp_path / "name-evidence", names=("beta",))
    by_tag = verify(contract, tmp_path / "tag-evidence", tags=("smoke",))

    assert [scenario.name for scenario in by_name.scenarios] == ["beta"]
    assert [scenario.name for scenario in by_tag.scenarios] == ["alpha"]
    with pytest.raises(ContractError, match="unknown selected scenarios"):
        verify(contract, tmp_path / "unknown-evidence", names=("missing",))


def test_public_api_asserts_modified_and_deleted_file_deltas(tmp_path: Path) -> None:
    prepare = (
        "from pathlib import Path; "
        "Path('note.txt').write_text('before', encoding='utf-8', newline='\\n')"
    )
    cleanup = "from pathlib import Path; Path('note.txt').unlink(missing_ok=True)"
    document = {
        "version": 1,
        "name": "file-transitions",
        "timeouts": {"connect": 30, "operation": 30, "total": 120},
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [sys.executable, str(FIXTURE_SERVER)],
                "cwd": str(tmp_path),
                "workspace": str(tmp_path),
            }
        },
        "scenarios": [
            {
                "name": "modified file",
                "setup": [{"command": [sys.executable, "-c", prepare]}],
                "calls": [
                    {
                        "tool": "write_note",
                        "arguments": {"content": "after"},
                        "expect": {"outcome": "success"},
                    }
                ],
                "observers": [
                    {
                        "name": "note",
                        "kind": "file",
                        "path": "note.txt",
                        "phase": "delta",
                        "expect": {
                            "contains": {
                                "change": "modified",
                                "before": {"text": "before"},
                                "after": {"text": "after"},
                            }
                        },
                    }
                ],
                "cleanup": [{"command": [sys.executable, "-c", cleanup]}],
            },
            {
                "name": "deleted file",
                "setup": [{"command": [sys.executable, "-c", prepare]}],
                "calls": [
                    {
                        "tool": "delete_note",
                        "expect": {"outcome": "success"},
                    }
                ],
                "observers": [
                    {
                        "name": "note",
                        "kind": "file",
                        "path": "note.txt",
                        "phase": "delta",
                        "expect": {
                            "contains": {
                                "change": "deleted",
                                "before": {"state": "present", "text": "before"},
                                "after": {"state": "missing"},
                            }
                        },
                    }
                ],
                "cleanup": [{"command": [sys.executable, "-c", cleanup]}],
            },
        ],
    }
    contract = tmp_path / "file-transitions.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    report = verify(contract, tmp_path / "file-transition-evidence")

    assert report.verdict is Verdict.MATCH
    assert [scenario.verdict for scenario in report.scenarios] == [Verdict.MATCH, Verdict.MATCH]


def test_stdio_commands_and_observers_support_workspace_paths_with_spaces(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace with spaces"
    workspace.mkdir()
    document = {
        "version": 1,
        "name": "spaced-paths",
        "timeouts": {"connect": 30, "operation": 30, "total": 120},
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [sys.executable, str(FIXTURE_SERVER)],
                "cwd": str(workspace),
                "workspace": str(workspace),
            }
        },
        "scenarios": [
            {
                "name": "path-safe write",
                "setup": [
                    {
                        "command": [
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('note.txt').unlink(missing_ok=True)",
                        ]
                    }
                ],
                "calls": [
                    {
                        "tool": "write_note",
                        "arguments": {"content": "spaces are ordinary"},
                        "expect": {"outcome": "success"},
                    }
                ],
                "observers": [
                    {
                        "name": "note",
                        "kind": "file",
                        "path": "note.txt",
                        "expect": {"contains": {"text": "spaces are ordinary"}},
                    }
                ],
                "cleanup": [
                    {
                        "command": [
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('note.txt').unlink(missing_ok=True)",
                        ]
                    }
                ],
            }
        ],
    }
    contract = tmp_path / "spaces.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    report = verify(contract, tmp_path / "spaced-evidence")

    assert report.verdict is Verdict.MATCH
    assert not (workspace / "note.txt").exists()


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


def test_malformed_stdio_protocol_is_inconclusive_and_bounded(tmp_path: Path) -> None:
    document = {
        "version": 1,
        "name": "malformed-protocol",
        "timeouts": {"connect": 2, "operation": 2, "total": 10},
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": [
                    sys.executable,
                    "-c",
                    "import sys; sys.stdout.write('not-json\\n'); sys.stdout.flush()",
                ],
                "cwd": str(tmp_path),
            }
        },
        "scenarios": [
            {
                "name": "malformed response",
                "calls": [{"tool": "status", "expect": {"outcome": "success"}}],
            }
        ],
    }
    contract = tmp_path / "malformed.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    started = time.monotonic()
    report = verify(contract, tmp_path / "malformed-evidence")

    assert time.monotonic() - started < 8
    assert report.verdict is Verdict.INCONCLUSIVE
    assert report.scenarios[0].error is not None
    assert report.exit_code == 2


@pytest.mark.parametrize("timeout_kind", ["connect", "operation", "total"])
def test_public_api_enforces_each_timeout_budget(tmp_path: Path, timeout_kind: str) -> None:
    timeouts = {"connect": 5.0, "operation": 5.0, "total": 10.0}
    if timeout_kind == "connect":
        timeouts["connect"] = 0.2
        command = [sys.executable, "-c", "import time; time.sleep(10)"]
        setup: list[dict[str, object]] = []
        calls = [{"tool": "echo", "arguments": {"message": "hello"}}]
    elif timeout_kind == "operation":
        timeouts["operation"] = 0.2
        command = [sys.executable, str(FIXTURE_SERVER)]
        setup = []
        calls = [{"tool": "slow", "arguments": {"seconds": 10}}]
    else:
        timeouts["total"] = 0.2
        command = [sys.executable, str(FIXTURE_SERVER)]
        setup = [{"command": [sys.executable, "-c", "import time; time.sleep(10)"]}]
        calls = [{"tool": "echo", "arguments": {"message": "hello"}}]
    document = {
        "version": 1,
        "name": f"{timeout_kind}-timeout",
        "timeouts": timeouts,
        "targets": {
            "candidate": {
                "transport": "stdio",
                "command": command,
                "cwd": str(tmp_path),
            }
        },
        "scenarios": [
            {
                "name": f"{timeout_kind} is bounded",
                "setup": setup,
                "calls": [{**calls[0], "expect": {"outcome": "success"}}],
            }
        ],
    }
    contract = tmp_path / f"{timeout_kind}.yaml"
    contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    started = time.monotonic()
    report = verify(contract, tmp_path / f"{timeout_kind}-evidence")

    assert time.monotonic() - started < 8
    assert report.verdict is Verdict.INCONCLUSIVE
    assert report.exit_code == 2
    assert report.scenarios[0].error is not None
    error = report.scenarios[0].error.lower()
    assert any(marker in error for marker in ("did not connect", "timed out", "total timeout"))
