"""Fail the release gate on private provenance, credential files, or secret shapes."""

from __future__ import annotations

import re
from pathlib import Path

SKIP_DIRECTORIES = {
    ".git",
    ".mcp-behavior",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "dist",
    "__pycache__",
}
FORBIDDEN_SUFFIXES = {".env", ".key", ".p12", ".pfx", ".pem"}
FORBIDDEN_TERMS = ("st" + "rust", "google" + "-internal", "private" + "-adk")
SECRET_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?" + rb"PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "OpenAI key": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    "bearer credential": re.compile(rb"(?i)\bBearer\s+(?!<redacted>)[A-Za-z0-9._~+/=-]{20,}"),
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    metadata = (root / "pyproject.toml").read_text(encoding="utf-8")
    if "Apache License" not in license_text or 'license = "Apache-2.0"' not in metadata:
        raise SystemExit("Apache-2.0 license files are inconsistent")

    checked = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        relative = path.relative_to(root)
        if _credential_filename(relative):
            raise SystemExit(f"credential-like file must not ship: {relative.as_posix()}")
        data = path.read_bytes()
        checked += 1
        lowered = data.lower()
        for term in FORBIDDEN_TERMS:
            if term.encode() in lowered:
                raise SystemExit(
                    f"private-project provenance term {term!r} found in {relative.as_posix()}"
                )
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                raise SystemExit(f"possible {label} found in {relative.as_posix()}")
    print(f"release provenance and secret audit passed: {checked} files")
    return 0


def _credential_filename(path: Path) -> bool:
    name = path.name.lower()
    if name == ".env.example":
        return False
    return name == ".env" or path.suffix.lower() in FORBIDDEN_SUFFIXES


if __name__ == "__main__":
    raise SystemExit(main())
