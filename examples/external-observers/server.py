"""Write both fixture representations; probes remain separate processes."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from mcp.server.mcpserver import MCPServer

server = MCPServer("external-observer-fixture")


@server.tool(structured_output=True)
def save_invoice(total_cents: int) -> dict[str, bool]:
    stored = total_cents + int(os.environ.get("EXAMPLE_DRIFT", "0"))
    Path("invoices.json").write_text(
        json.dumps(
            {
                "storage_metadata": "ignored by this projection",
                "invoices": [{"invoice_id": "inv-42", "total_cents": stored}],
            }
        ),
        encoding="utf-8",
    )
    with closing(sqlite3.connect("invoices.sqlite")) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS invoices (invoice_id TEXT PRIMARY KEY, total_cents INTEGER)"
        )
        connection.execute("DELETE FROM invoices")
        connection.execute("INSERT INTO invoices VALUES (?, ?)", ("inv-42", stored))
        connection.commit()
    return {"saved": True}


if __name__ == "__main__":
    server.run("stdio")
