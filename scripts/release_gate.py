"""Run the complete local release-candidate gate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dist = root / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    commands = [
        ["uv", "lock", "--check"],
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "mypy"],
        ["uv", "run", "python", "scripts/check_docs.py"],
        [
            "uv",
            "run",
            "pytest",
            "--cov=mcp_behavior",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
        ],
        ["uv", "run", "pip-audit"],
        ["uv", "run", "python", "-m", "build", "--outdir", str(dist)],
        ["uv", "run", "python", "scripts/verify_dist.py", str(dist)],
        ["uv", "run", "mcp-behavior", "--version"],
    ]
    for command in commands:
        print(f"+ {' '.join(command)}", flush=True)
        subprocess.run(command, cwd=root, check=True)
    print("release gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
