"""Install the built wheel and dogfood every public example in a fresh environment."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EXAMPLES = (
    ("expectations", "verify", 0),
    ("baseline", "verify", 0),
    ("differential", "diff", 1),
    ("wrong-effect", "verify", 1),
    ("nondeterminism", "verify", 2),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", nargs="?", default="dist", type=Path)
    parser.add_argument("--python", default=sys.executable, help="Python interpreter or version")
    parser.add_argument("--quiet", action="store_true", help="print only failures and summary")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    dist = arguments.dist.resolve()
    wheels = sorted(dist.glob("mcp_behavior-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected one wheel in {dist}, found {len(wheels)}")

    with tempfile.TemporaryDirectory(prefix="mcp-behavior-smoke-") as temporary:
        smoke_root = Path(temporary)
        environment = smoke_root / "venv"
        _run(
            ["uv", "venv", str(environment), "--python", arguments.python],
            root,
            quiet=arguments.quiet,
        )
        python = _venv_executable(environment, "python")
        cli = _venv_executable(environment, "mcp-behavior")
        _run(
            ["uv", "pip", "install", "--python", str(python), str(wheels[0])],
            root,
            quiet=arguments.quiet,
        )

        child_env = os.environ.copy()
        child_env["PATH"] = str(python.parent) + os.pathsep + child_env.get("PATH", "")
        _run([str(cli), "--version"], root, env=child_env, quiet=arguments.quiet)
        _run([str(cli), "--help"], root, env=child_env, quiet=arguments.quiet)
        for command in ("init", "record", "verify", "diff", "inspect"):
            _run(
                [str(cli), command, "--help"],
                root,
                env=child_env,
                quiet=arguments.quiet,
            )

        for name, command, expected in EXAMPLES:
            example = root / "examples" / name
            evidence = smoke_root / "evidence" / name
            _run_expected(
                [
                    str(cli),
                    command,
                    "mcp-behavior.yaml",
                    "--evidence",
                    str(evidence),
                    "--diff-detail",
                    "full",
                ],
                example,
                expected,
                child_env,
                emit=not arguments.quiet,
            )

        _verify_repeatability(cli, root, smoke_root, child_env, emit=not arguments.quiet)

    print(f"clean-wheel smoke passed: {len(EXAMPLES)} examples")
    return 0


def _verify_repeatability(
    cli: Path,
    root: Path,
    smoke_root: Path,
    env: dict[str, str],
    *,
    emit: bool,
) -> None:
    example = root / "examples" / "nondeterminism"
    digests: list[str] = []
    for run in (1, 2):
        evidence = smoke_root / "evidence" / f"repeat-{run}"
        _run_expected(
            [
                str(cli),
                "verify",
                "mcp-behavior.yaml",
                "--name",
                "declared runtime noise normalizes",
                "--evidence",
                str(evidence),
                "--quiet",
            ],
            example,
            0,
            env,
            emit=emit,
        )
        manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        digest = manifest.get("semantic_digest")
        if not isinstance(digest, str):
            raise SystemExit("repeatability evidence has no semantic digest")
        digests.append(digest)
    if len(set(digests)) != 1:
        raise SystemExit(f"normalized example produced different semantic digests: {digests}")


def _venv_executable(environment: Path, name: str) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / f"{name}.exe"
    return environment / "bin" / name


def _run(
    command: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    quiet: bool = False,
) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if not quiet or completed.returncode != 0:
        print(completed.stdout, end="")
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)


def _run_expected(
    command: list[str],
    cwd: Path,
    expected: int,
    env: dict[str, str],
    *,
    emit: bool,
) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if emit or completed.returncode != expected:
        print(completed.stdout, end="")
    if completed.returncode != expected:
        raise SystemExit(
            f"{' '.join(command)} returned {completed.returncode}; expected {expected}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
