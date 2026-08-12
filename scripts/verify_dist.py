"""Verify built archives and write deterministic SHA-256 checksums."""

from __future__ import annotations

import hashlib
import sys
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from audit_release import SECRET_PATTERNS

REQUIRED_WHEEL_FILES = {
    "mcp_behavior/__init__.py",
    "mcp_behavior/cli.py",
    "mcp_behavior/core.py",
    "mcp_behavior/py.typed",
}
REQUIRED_SDIST_FILES = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "ROADMAP.md",
    "SECURITY.md",
    "docs/ARCHITECTURE.md",
    "docs/CONTRACT.md",
    "docs/EVIDENCE.md",
    "docs/PROVENANCE.md",
    "examples/differential/mcp-behavior.yaml",
    "examples/nondeterminism/mcp-behavior.yaml",
    "examples/wrong-effect/mcp-behavior.yaml",
}
FORBIDDEN_SDIST_FILES = {"AGENTS.md", "CONTEXT.md", "STATUS.md"}
FORBIDDEN_TERMS = ("st" + "rust", "google" + "-internal", "private" + "-adk")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist").resolve()
    wheels = sorted(root.glob("mcp_behavior-*.whl"))
    sdists = sorted(root.glob("mcp_behavior-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one wheel and one source archive")
    _verify_wheel(wheels[0])
    _verify_sdist(sdists[0])
    lines = [f"{_sha256(path)}  {path.name}" for path in sorted((wheels[0], sdists[0]))]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("distribution archives verified")
    return 0


def _verify_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = REQUIRED_WHEEL_FILES - names
        if missing:
            raise SystemExit(f"wheel is missing: {', '.join(sorted(missing))}")
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise SystemExit("wheel must contain one METADATA file")
        metadata = archive.read(metadata_names[0]).decode("utf-8")
        for required in (
            "Name: mcp-behavior",
            "Version: 0.1.0",
            "License-Expression: Apache-2.0",
        ):
            if required not in metadata:
                raise SystemExit(f"wheel metadata is missing {required!r}")
        _scan_text_members((name, archive.read(name)) for name in names)


def _verify_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        relative_names: set[str] = set()
        for member in members:
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise SystemExit(f"unsafe source archive member: {member.name}")
            relative = PurePosixPath(*pure.parts[1:]).as_posix()
            relative_names.add(relative)
            if _credential_member(relative):
                raise SystemExit(f"credential-like source archive member: {relative}")
        missing = REQUIRED_SDIST_FILES - relative_names
        forbidden = FORBIDDEN_SDIST_FILES & relative_names
        if missing:
            raise SystemExit(f"source archive is missing: {', '.join(sorted(missing))}")
        if forbidden:
            raise SystemExit(
                f"source archive contains internal files: {', '.join(sorted(forbidden))}"
            )
        text_members = []
        for member in members:
            if member.isfile() and member.size <= 2_000_000:
                handle = archive.extractfile(member)
                if handle is not None:
                    text_members.append((member.name, handle.read()))
        _scan_text_members(text_members)


def _scan_text_members(members: Iterable[tuple[str, bytes]]) -> None:
    for name, data in members:
        text = data.decode("utf-8", errors="ignore").lower()
        for term in FORBIDDEN_TERMS:
            if term in text:
                raise SystemExit(f"forbidden private-project term {term!r} found in {name}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                raise SystemExit(f"possible {label} found in {name}")


def _credential_member(name: str) -> bool:
    path = PurePosixPath(name.lower())
    return path.name == ".env" or path.suffix in {".env", ".key", ".p12", ".pfx", ".pem"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1_048_576):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
