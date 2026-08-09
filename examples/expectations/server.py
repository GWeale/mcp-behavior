from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

server = MCPServer("expectations-example")


@server.tool(structured_output=True)
def echo(message: str) -> dict[str, str]:
    return {"message": message}


@server.tool(structured_output=True)
def save_receipt(total: float) -> dict[str, object]:
    Path("receipt.txt").write_text(
        f"total={total:.2f}\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"saved": True, "total": total}


if __name__ == "__main__":
    server.run("stdio")
