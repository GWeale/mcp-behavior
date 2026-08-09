from __future__ import annotations

from mcp.server.mcpserver import MCPServer

server = MCPServer("baseline-example")


@server.tool(structured_output=True)
def price(subtotal: float, tax_rate: float) -> dict[str, float]:
    return {"subtotal": subtotal, "tax": round(subtotal * tax_rate, 2)}


if __name__ == "__main__":
    server.run("stdio")
