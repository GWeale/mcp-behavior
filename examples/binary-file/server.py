"""Write generated binary bytes with an optional deliberate one-byte error."""

from __future__ import annotations

import sys
from pathlib import Path


def write_binary(changed: bool = False) -> dict[str, object]:
    payload = bytearray(range(16))
    payload.extend((255, 128))
    if changed:
        payload[7] = 8
    Path("generated.bin").write_bytes(payload)
    return {"written": True, "bytes": len(payload)}


if __name__ == "__main__":
    if sys.argv[1:] == ["--cleanup"]:
        Path("generated.bin").unlink(missing_ok=True)
    else:
        from mcp.server.mcpserver import MCPServer

        server = MCPServer("binary-file-example")
        server.tool(structured_output=True)(write_binary)
        server.run("stdio")
