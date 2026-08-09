"""Official-SDK adapters for stdio and Streamable HTTP MCP targets."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any, TextIO

import httpx2
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from .contract import Contract, TargetSpec
from .models import JsonValue, Observation
from .normalization import enforce_serialized_limit, sanitize


class TargetError(RuntimeError):
    pass


class _StderrCapture:
    """Drain server stderr continuously while retaining only a bounded prefix."""

    def __init__(self, limit: int) -> None:
        read_fd, write_fd = os.pipe()
        self.writer: TextIO = os.fdopen(write_fd, "w", encoding="utf-8", newline="")
        self._read_fd = read_fd
        self._limit = limit
        self._buffer = bytearray()
        self._truncated = False
        self._task = asyncio.create_task(self._drain())

    async def _drain(self) -> None:
        try:
            while chunk := await asyncio.to_thread(os.read, self._read_fd, 65_536):
                remaining = self._limit - len(self._buffer)
                if remaining > 0:
                    self._buffer.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    self._truncated = True
        finally:
            os.close(self._read_fd)

    def close_writer(self) -> None:
        with suppress(OSError):
            self.writer.close()

    async def finish(self) -> None:
        self.close_writer()
        try:
            await asyncio.wait_for(self._task, timeout=5)
        except TimeoutError:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    def getvalue(self) -> str:
        value = self._buffer.decode("utf-8", errors="replace")
        return value + ("\n<stderr-truncated>\n" if self._truncated else "")


@dataclass(slots=True)
class ConnectedTarget:
    name: str
    client: Client
    operation_timeout: float
    output_limit: int
    secrets: tuple[str, ...]
    _stderr: _StderrCapture

    @property
    def protocol_version(self) -> str:
        return str(self.client.protocol_version)

    @property
    def logs(self) -> str:
        return self._stderr.getvalue()

    async def call_tool(self, tool: str, arguments: dict[str, JsonValue]) -> Observation:
        try:
            async with asyncio.timeout(self.operation_timeout):
                result = await self.client.call_tool(tool, arguments)
        except TimeoutError as exc:
            raise TargetError(
                f"target {self.name!r} tool {tool!r} timed out after "
                f"{self.operation_timeout:g} seconds"
            ) from exc
        except Exception as exc:
            safe_error = _safe_error(exc, self.secrets)
            raise TargetError(f"target {self.name!r} tool {tool!r} failed: {safe_error}") from exc
        value = _as_json(result.model_dump(mode="json", by_alias=True, exclude_none=True))
        enforce_serialized_limit(value, self.output_limit)
        return Observation(
            value=value,
            is_error=bool(result.is_error),
            metadata={"protocol_version": self.protocol_version},
        )


@asynccontextmanager
async def connect_target(spec: TargetSpec, contract: Contract) -> AsyncIterator[ConnectedTarget]:
    stack = AsyncExitStack()
    stderr = _StderrCapture(contract.limits.log_bytes)
    secrets: list[str] = []
    try:
        if spec.transport == "stdio":
            env = os.environ.copy()
            for name, value_source in spec.env.items():
                value, secret = value_source.resolve(
                    contract.source,
                    f"$.targets.{spec.name}.env.{name}",
                )
                env[name] = value
                if secret:
                    secrets.append(secret)
            assert spec.cwd is not None and spec.command
            parameters = StdioServerParameters(
                command=spec.command[0],
                args=list(spec.command[1:]),
                env=env,
                cwd=spec.cwd,
            )
            transport = stdio_client(parameters, errlog=stderr.writer)
        else:
            assert spec.url is not None
            headers: dict[str, str] = {}
            for name, value_source in spec.headers.items():
                value, secret = value_source.resolve(
                    contract.source,
                    f"$.targets.{spec.name}.headers.{name}",
                )
                headers[name] = value
                if secret:
                    secrets.append(secret)
            http_client = await stack.enter_async_context(
                httpx2.AsyncClient(headers=headers, follow_redirects=True)
            )
            transport = streamable_http_client(spec.url, http_client=http_client)

        mode = "legacy" if spec.mode == "legacy" else "auto"
        client = Client(
            transport,
            read_timeout_seconds=contract.timeouts.operation,
            mode=mode,
        )
        try:
            async with asyncio.timeout(contract.timeouts.connect):
                connected = await stack.enter_async_context(client)
        except TimeoutError as exc:
            raise TargetError(
                f"target {spec.name!r} did not connect within {contract.timeouts.connect:g} seconds"
            ) from exc
        except Exception as exc:
            safe_error = _safe_error(exc, secrets)
            raise TargetError(f"target {spec.name!r} could not connect: {safe_error}") from exc
        stderr.close_writer()
        if spec.mode == "modern" and str(connected.protocol_version) != "2026-07-28":
            raise TargetError(
                f"target {spec.name!r} negotiated {connected.protocol_version}; "
                "modern mode requires 2026-07-28"
            )
        yield ConnectedTarget(
            spec.name,
            connected,
            contract.timeouts.operation,
            contract.limits.output_bytes,
            tuple(secrets),
            stderr,
        )
    finally:
        try:
            async with asyncio.timeout(5):
                await stack.aclose()
        except TimeoutError as exc:
            raise TargetError(f"target {spec.name!r} did not shut down cleanly") from exc
        finally:
            await stderr.finish()


def _as_json(value: Any) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_as_json(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TargetError("MCP result object contains a non-string key")
        return {str(key): _as_json(item) for key, item in value.items()}
    raise TargetError(f"MCP result contains unsupported value {type(value).__name__}")


def _safe_error(error: Exception, secrets: list[str] | tuple[str, ...]) -> str:
    value = sanitize(str(error), secrets)
    assert isinstance(value, str)
    return value
