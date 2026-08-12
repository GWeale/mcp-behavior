"""Small clean-room MCP server used only by integration tests and examples."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

server = MCPServer("mcp-behavior-fixture")


@server.tool(structured_output=True)
def echo(message: str) -> dict[str, object]:
    """Echo a message with a configurable implementation variant."""

    return {
        "message": message,
        "variant": os.environ.get("FIXTURE_VARIANT", "stable"),
        "request_id": "123e4567-e89b-12d3-a456-426614174000",
    }


@server.tool(structured_output=True)
def write_note(content: str) -> dict[str, object]:
    """Write one declared fixture file relative to the server workspace."""

    path = Path.cwd() / "note.txt"
    path.write_text(content, encoding="utf-8", newline="\n")
    return {"written": path.name, "bytes": len(content.encode("utf-8"))}


@server.tool(structured_output=True)
def delete_note() -> dict[str, bool]:
    path = Path("note.txt")
    existed = path.exists()
    path.unlink(missing_ok=True)
    return {"deleted": existed}


@server.tool(structured_output=True)
def reveal_fixture_secret() -> dict[str, object]:
    """Return a test-only secret so persistence redaction can be verified."""

    return {"secret": os.environ.get("FIXTURE_SECRET", "unset")}


@server.tool(structured_output=True)
def expected_failure() -> dict[str, object]:
    """Raise a stable error for expected-error assertions."""

    raise ValueError("fixture failure")


@server.tool(structured_output=True)
def slow(seconds: float) -> dict[str, bool]:
    """Sleep long enough to exercise the client's operation timeout."""

    time.sleep(seconds)
    return {"completed": True}


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--http":
        server.run("streamable-http", host="127.0.0.1", port=int(sys.argv[2]), stateless_http=True)
    else:
        server.run("stdio")
