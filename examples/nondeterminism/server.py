from __future__ import annotations

import os
import random
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.mcpserver import MCPServer

server = MCPServer("nondeterminism-example")


@server.tool(structured_output=True)
def snapshot() -> dict[str, object]:
    run_id = str(uuid.uuid4())
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "run_uuid": run_id,
        "request_id": f"request-{uuid.uuid4()}",
        "callback": f"http://127.0.0.1:{random.randint(20000, 60000)}/result",
        "temp_path": str(Path(tempfile.gettempdir()) / f"mcp-behavior-{run_id}"),
    }


@server.tool()
def abort_connection() -> str:
    os._exit(17)


if __name__ == "__main__":
    server.run("stdio")
