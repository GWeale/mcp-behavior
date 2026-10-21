from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mcp_behavior import execution
from mcp_behavior.contract import CommandSpec
from mcp_behavior.execution import ExecutionError, run_command


@pytest.mark.parametrize("group_state", ["gone", "alive", "denied", "leader-running"])
def test_output_limit_cleanup_distinguishes_exit_race_from_denial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, group_state: str
) -> None:
    async def scenario() -> None:
        stdout = asyncio.StreamReader()
        stdout.feed_data(b"x" * 100)
        stdout.feed_eof()
        stderr = asyncio.StreamReader()
        stderr.feed_eof()
        process = SimpleNamespace(pid=12345, returncode=None, stdout=stdout, stderr=stderr)
        waits = 0

        async def wait() -> int:
            nonlocal waits
            waits += 1
            # _communicate's first wait is cancelled by the real output-budget
            # failure. Only cleanup can observe this fixture's subsequent exit.
            if waits > 1 and group_state != "leader-running":
                process.returncode = 0
                return 0
            await asyncio.Future()
            raise AssertionError("pending process wait unexpectedly resumed")

        process.wait = wait

        def kill(pid: int, sig: int) -> None:
            assert pid == -process.pid
            if sig != 0:
                raise PermissionError("group signal denied")
            if group_state == "gone":
                raise ProcessLookupError("group no longer exists")
            if group_state == "denied":
                raise PermissionError("group probe denied")

        # Substitute the POSIX process boundary without changing global os.name
        # or depending on native macOS scheduling during a Windows test run.
        monkeypatch.setattr(execution, "os", SimpleNamespace(name="posix", environ={}, kill=kill))
        monkeypatch.setattr(
            execution.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)
        )
        monkeypatch.setattr(execution, "_PROCESS_EXIT_TIMEOUT", 0.01, raising=False)
        expected = ExecutionError if group_state == "gone" else PermissionError
        message = "output exceeded" if group_state == "gone" else "group signal denied"
        with pytest.raises(expected, match=message):
            await asyncio.wait_for(
                run_command(
                    CommandSpec(("noisy-fixture",), None),
                    source=tmp_path / "contract.yaml",
                    label="noisy fixture",
                    workspace=tmp_path,
                    default_timeout=2,
                    log_limit=50,
                ),
                timeout=0.5,
            )

    asyncio.run(scenario())
