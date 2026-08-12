from __future__ import annotations

from mcp.server.mcpserver import MCPServer

server = MCPServer("candidate-server")


@server.tool(structured_output=True)
def lookup(user_id: str) -> dict[str, str]:
    return {"id": user_id, "status": "suspended"}


if __name__ == "__main__":
    server.run("stdio")
