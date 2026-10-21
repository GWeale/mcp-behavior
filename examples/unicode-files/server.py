"""Generate small UTF-8 files with mixed ASCII and Unicode names."""

from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

server = MCPServer("unicode-files-example")
NAMES = ("猫.txt", "z.txt", "π.txt", "café-猫.txt", "A.txt")
CONTENT = "Hello, 世界!\n"


@server.tool(structured_output=True)
def write_files() -> dict[str, int]:
    root = Path("unicode-files")
    root.mkdir(exist_ok=True)
    for name in NAMES:
        (root / name).write_text(CONTENT, encoding="utf-8", newline="\n")
    return {"written": len(NAMES)}


def cleanup() -> None:
    root = Path("unicode-files")
    for name in NAMES:
        (root / name).unlink(missing_ok=True)
    if root.exists():
        root.rmdir()


if __name__ == "__main__":
    if sys.argv[1:] == ["--cleanup"]:
        cleanup()
    else:
        server.run("stdio")
