"""Opt-in Linux Docker experiment using the existing public verifier."""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import yaml

from mcp_behavior import verify

ROOT = Path(__file__).resolve().parents[2]


def docker(*args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=True, timeout=90, env=env
    )
    return result.stdout.strip()


def command(image: str, name: str, workspace: Path) -> list[str]:
    return [
        "docker",
        "run",
        "--pull=never",
        "--rm",
        "-i",
        "--name",
        name,
        "--read-only",
        "--network=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory=256m",
        "--cpus=1",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=32m",
        "--mount",
        f"type=bind,source={workspace},target=/workspace",
        "--workdir=/workspace",
        "--env",
        "PROTOTYPE_MARKER",
        image,
    ]


def cleanup(name: str) -> bool:
    # Only the UUID-named container created by this invocation may be removed.
    assert name.startswith("mcp-prototype-") and len(name) == len("mcp-prototype-") + 32
    names = docker("ps", "--all", "--filter", f"name=^/{name}$", "--format", "{{.Names}}")
    if names:
        if names != name:
            raise RuntimeError("container identity mismatch")
        docker("rm", "--force", name)
    remaining = docker("ps", "--all", "--filter", f"name=^/{name}$", "--format", "{{.Names}}")
    return not remaining


def measure(image: str, report_path: Path) -> dict[str, object]:
    if os.name != "posix" or not shutil.which("docker"):
        raise RuntimeError("requires Linux with a running Docker daemon; see README.md")
    docker("info", "--format", "{{.ServerVersion}}")
    image_id = docker("image", "inspect", image, "--format", "{{.Id}}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    parent = report_path.parent.resolve()
    base = yaml.safe_load((ROOT / "examples/expectations/mcp-behavior.yaml").read_text())
    results: dict[str, object] = {"schema_version": 1, "image_id": image_id, "cases": {}}
    cases: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="docker-workspace-", dir=parent) as directory:
        workspace = Path(directory).resolve()
        assert workspace.is_relative_to(parent)
        probe_name = "mcp-prototype-" + uuid.uuid4().hex
        argv = command(image, probe_name, workspace)
        probe = (
            "import os; "
            "assert os.environ['PROTOTYPE_MARKER']=='demo'; "
            "assert 'MCP_PROTOTYPE_HOST_ONLY' not in os.environ; "
            "print('environment allowlist verified')"
        )
        started = time.perf_counter()
        try:
            output = subprocess.run(
                [*argv, "python", "-c", probe],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env={
                    **os.environ,
                    "PROTOTYPE_MARKER": "demo",
                    "MCP_PROTOTYPE_HOST_ONLY": "host-only",
                },
            )
            assert output.stdout.strip() == "environment allowlist verified"
            results["container_startup_probe_ms"] = round((time.perf_counter() - started) * 1000)
        finally:
            assert cleanup(probe_name)

        for case in ("success", "timeout"):
            name = "mcp-prototype-" + uuid.uuid4().hex
            contract = copy.deepcopy(base)
            contract["targets"]["candidate"] = {
                "transport": "stdio",
                "command": command(image, name, workspace),
                "workspace": str(workspace),
                "cwd": str(workspace),
                "env": {"PROTOTYPE_MARKER": "demo"},
            }
            if case == "timeout":
                contract["targets"]["candidate"]["command"] += [
                    "python",
                    "-c",
                    "import time; time.sleep(120)",
                ]
                contract["scenarios"] = contract["scenarios"][:1]
            contract["timeouts"] = {
                "connect": 2 if case == "timeout" else 20,
                "operation": 10,
                "total": 60,
            }
            path = workspace / f"{case}.yaml"
            path.write_text(yaml.safe_dump(contract), encoding="utf-8")
            started = time.perf_counter()
            try:
                result = verify(path, parent / f"{case}-evidence")
            finally:
                removed = cleanup(name)
            elapsed = round((time.perf_counter() - started) * 1000)
            expected = "MATCH" if case == "success" else "INCONCLUSIVE"
            assert result.verdict == expected, result.to_dict()
            assert removed, "prototype container remained after cleanup"
            cases[case] = {
                "verdict": str(result.verdict),
                "elapsed_ms": elapsed,
                "container_removed": removed,
            }
        results["cases"] = cases
    report_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="mcp-behavior-prototype:local")
    parser.add_argument(
        "--report", type=Path, default=ROOT / ".mcp-behavior/docker-prototype/report.json"
    )
    args = parser.parse_args()
    print(json.dumps(measure(args.image, args.report.resolve()), indent=2))


if __name__ == "__main__":
    main()
