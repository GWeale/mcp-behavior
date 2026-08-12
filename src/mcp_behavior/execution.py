"""Bounded execution of user-declared trusted setup, cleanup, and probe commands."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import CommandSpec
from .models import JsonValue


class ExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    secrets: tuple[str, ...] = ()


@dataclass(slots=True)
class _ByteBudget:
    limit: int
    used: int = 0

    def add(self, amount: int) -> None:
        self.used += amount
        if self.used > self.limit:
            raise ExecutionError(f"command output exceeded configured {self.limit}-byte log limit")


async def run_command(
    spec: CommandSpec,
    *,
    source: Path,
    label: str,
    workspace: Path,
    default_timeout: float,
    log_limit: int,
    stdin_value: JsonValue | None = None,
) -> CommandResult:
    env = os.environ.copy()
    secrets: list[str] = []
    for name, value_source in spec.env.items():
        value, secret = value_source.resolve(source, f"command.env.{name}")
        env[name] = value
        if secret:
            secrets.append(secret)

    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.__dict__["CREATE_NEW_PROCESS_GROUP"]
    else:
        kwargs["start_new_session"] = True

    started = time.perf_counter()
    try:
        process = await asyncio.create_subprocess_exec(
            *spec.command,
            cwd=spec.cwd or workspace,
            env=env,
            stdin=asyncio.subprocess.PIPE
            if stdin_value is not None
            else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs,
        )
    except (OSError, ValueError) as exc:
        raise ExecutionError(f"could not start {label}: {exc}") from exc

    budget = _ByteBudget(log_limit)
    timeout = spec.timeout or default_timeout
    payload = (
        json.dumps(stdin_value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if stdin_value is not None
        else None
    )
    try:
        stdout, stderr, returncode = await asyncio.wait_for(
            _communicate(process, payload, budget),
            timeout=timeout,
        )
    except TimeoutError as exc:
        await _kill_process_tree(process)
        raise ExecutionError(f"{label} timed out after {timeout:g} seconds") from exc
    except BaseException:
        await _kill_process_tree(process)
        raise

    duration_ms = round((time.perf_counter() - started) * 1000)
    return CommandResult(
        returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        duration_ms,
        tuple(secrets),
    )


async def _communicate(
    process: asyncio.subprocess.Process,
    payload: bytes | None,
    budget: _ByteBudget,
) -> tuple[bytes, bytes, int]:
    assert process.stdout is not None
    assert process.stderr is not None
    if payload is not None:
        assert process.stdin is not None
        process.stdin.write(payload)
        await process.stdin.drain()
        process.stdin.close()
        await process.stdin.wait_closed()

    stdout_task = asyncio.create_task(_read_limited(process.stdout, budget))
    stderr_task = asyncio.create_task(_read_limited(process.stderr, budget))
    wait_task = asyncio.create_task(process.wait())
    tasks = (stdout_task, stderr_task, wait_task)
    try:
        stdout, stderr, returncode = await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    return stdout, stderr, returncode


async def _read_limited(
    stream: asyncio.StreamReader,
    budget: _ByteBudget,
) -> bytes:
    chunks: list[bytes] = []
    while chunk := await stream.read(65_536):
        budget.add(len(chunk))
        chunks.append(chunk)
    return b"".join(chunks)


async def _kill_process_tree(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    if os.name == "nt":
        killer = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(process.pid),
            "/T",
            "/F",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await killer.wait()
    else:
        with suppress(ProcessLookupError):
            os.kill(-process.pid, getattr(signal, "SIGKILL", 9))
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except TimeoutError:
        process.kill()
        await process.wait()
