"""Record the real CRLF reproduction's stdout as an asciinema v2 cast and transcript."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new recording directory")
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).resolve().parents[1] / "examples" / "filesystem-crlf" / "reproduce.py"
    command = [
        sys.executable,
        "-u",
        str(script),
        "--before",
        str(args.before.resolve()),
        "--after",
        str(args.after.resolve()),
        "--evidence",
        str(args.evidence.resolve()),
    ]
    started = time.monotonic()
    events: list[list[object]] = []
    transcript: list[str] = []
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True, encoding="utf-8") as child:
        assert child.stdout is not None
        for line in child.stdout:
            events.append([round(time.monotonic() - started, 6), "o", line.replace("\n", "\r\n")])
            transcript.append(line)
            print(line, end="", flush=True)
        code = child.wait()
    if code != 0:
        raise SystemExit(f"Reproduction failed with exit code {code}; recording is incomplete")
    header = {"version": 2, "width": 110, "height": 24, "title": "MCP filesystem CRLF regression"}
    with (output / "demo.cast").open("w", encoding="utf-8", newline="\n") as stream:
        for value in [header, *events]:
            stream.write(json.dumps(value) + "\n")
    (output / "transcript.txt").write_text("".join(transcript), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
