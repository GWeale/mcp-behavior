"""Run the authenticated fixture with a generated, memory-only credential."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yaml

from mcp_behavior import verify

TOKEN_ENV = "MCP_BEHAVIOR_EXAMPLE_TOKEN"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--missing-token", action="store_true")
    args = parser.parse_args()
    token = secrets.token_urlsafe(32)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    server_env = {**os.environ, TOKEN_ENV: token}
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("server.py")), str(port)],
        env=server_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    previous = os.environ.get(TOKEN_ENV)
    try:
        deadline = time.monotonic() + 15
        while True:
            if process.poll() is not None:
                raise RuntimeError("local fixture exited before it was ready")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("local fixture did not become ready") from None
                time.sleep(0.05)
        for headers in ({}, {"Authorization": "Bearer invalid"}):
            request = Request(f"http://127.0.0.1:{port}/mcp", data=b"{}", headers=headers)
            try:
                with urlopen(request, timeout=5):
                    raise RuntimeError("fixture accepted an unauthorized request")
            except HTTPError as exc:
                if exc.code != 401:
                    raise RuntimeError(
                        "fixture did not reject authorization with HTTP 401"
                    ) from None
        if args.missing_token:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = token
        with tempfile.TemporaryDirectory(prefix="mcp-auth-example-") as temporary:
            root = Path(temporary)
            contract = root / "contract.yaml"
            document = {
                "version": 1,
                "name": "authenticated loopback fixture",
                "timeouts": {"connect": 15, "operation": 15, "total": 60},
                "targets": {
                    "candidate": {
                        "transport": "http",
                        "url": f"http://127.0.0.1:{port}/mcp",
                        "workspace": str(root / "workspace"),
                        "headers": {
                            "Authorization": {"from_env": TOKEN_ENV, "template": "Bearer {value}"}
                        },
                    }
                },
                "scenarios": [
                    {
                        "name": "authorized call",
                        "calls": [{"tool": "inspect_fixture", "expect": {"outcome": "success"}}],
                    }
                ],
            }
            contract.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
            report = verify(contract, args.evidence.resolve())
        persisted = b"\n".join(
            path.read_bytes() for path in args.evidence.rglob("*") if path.is_file()
        )
        if token.encode() in persisted:
            raise RuntimeError("evidence redaction check failed")
        print(
            json.dumps(
                {
                    "verdict": report.verdict.value,
                    "redaction_checked": True,
                    "unauthorized_requests_rejected": True,
                    "redacted_value_present": b"<redacted>" in persisted,
                    "error": report.scenarios[0].error,
                }
            )
        )
        return report.exit_code
    finally:
        if previous is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
