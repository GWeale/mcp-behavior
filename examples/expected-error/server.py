"""Return an expected MCP tool error, or deliberately fail before connecting."""

from __future__ import annotations

import os
import sys

from mcp.server.mcpserver import MCPServer

server = MCPServer("expected-error-example")


@server.tool(structured_output=True)
def lookup_item(item_id: str) -> dict[str, str]:
    if item_id != "known":
        raise ValueError(f"unknown item: {item_id}")
    return {"id": item_id, "status": "active"}


if __name__ == "__main__":
    if sys.argv[1:] == ["--broken"]:
        os._exit(3)
    server.run("stdio")
