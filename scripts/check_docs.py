"""Check local Markdown links and publishing placeholders."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)|<img\s+[^>]*src=[\"']([^\"']+)[\"']", re.I)
PLACEHOLDER = re.compile(r"\[(?:your|insert|add|enter|describe|specify|choose)\b[^\]]*\]", re.I)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures: list[str] = []
    markdown_files = sorted(root.glob("*.md")) + sorted((root / "docs").rglob("*.md"))
    for document in markdown_files:
        text = document.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if PLACEHOLDER.search(line) and document.name != "LICENSE":
                failures.append(f"{document.relative_to(root)}:{line_number}: placeholder text")
            for match in LINK.finditer(line):
                raw_target = match.group(1) or match.group(2)
                target = raw_target.strip().strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path_text = unquote(target.split("#", 1)[0])
                if not path_text:
                    continue
                resolved = (document.parent / path_text).resolve()
                if not resolved.exists():
                    failures.append(
                        f"{document.relative_to(root)}:{line_number}: missing link {target!r}"
                    )
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"documentation checked: {len(markdown_files)} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
