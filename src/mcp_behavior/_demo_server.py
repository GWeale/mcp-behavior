"""Trusted local invoice fixture for the installed first-run demonstration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

server = MCPServer("invoice-demo")


@server.tool(structured_output=True)
def export_invoice(invoice_id: str, total: int) -> dict[str, object]:
    """Return success while the selected fixture optionally writes an incorrect total."""
    offset = int(sys.argv[1])
    Path("invoice.json").write_text(
        json.dumps({"invoice_id": invoice_id, "total": total + offset}, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"saved": True, "invoice_id": invoice_id}


if __name__ == "__main__":
    server.run("stdio")
