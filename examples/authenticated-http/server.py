"""Loopback-only header fixture; not an OAuth authorization server."""

from __future__ import annotations

import hmac
import os
import sys
from typing import Any

import uvicorn
from mcp.server.mcpserver import MCPServer

server = MCPServer("authenticated-http-example")


@server.tool(structured_output=True)
def inspect_fixture() -> dict[str, str]:
    """Deliberately echo the ephemeral test value to exercise evidence redaction."""
    return {"status": "authorized", "fixture_value": os.environ["MCP_BEHAVIOR_EXAMPLE_TOKEN"]}


application = server.streamable_http_app(stateless_http=True)


async def require_header(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] == "http":
        headers = dict(scope.get("headers", ()))
        expected = ("Bearer " + os.environ["MCP_BEHAVIOR_EXAMPLE_TOKEN"]).encode("ascii")
        if not hmac.compare_digest(headers.get(b"authorization", b""), expected):
            await send({"type": "http.response.start", "status": 401, "headers": []})
            await send({"type": "http.response.body", "body": b"authorization required"})
            return
    await application(scope, receive, send)


if __name__ == "__main__":
    uvicorn.run(require_header, host="127.0.0.1", port=int(sys.argv[1]), log_level="error")
