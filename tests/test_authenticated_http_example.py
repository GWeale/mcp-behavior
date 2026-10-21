from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parents[1] / "examples" / "authenticated-http" / "run.py"


@pytest.mark.parametrize("missing", [False, True])
def test_authenticated_http_example(tmp_path: Path, missing: bool) -> None:
    evidence = tmp_path / "evidence"
    command = [sys.executable, str(RUNNER), "--evidence", str(evidence)]
    if missing:
        command.append("--missing-token")
    result = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False)
    assert result.returncode == (2 if missing else 0), result.stderr
    output = json.loads(result.stdout)
    assert output["verdict"] == ("INCONCLUSIVE" if missing else "MATCH")
    assert output["redaction_checked"] is True
    assert output["unauthorized_requests_rejected"] is True
    if missing:
        assert "MCP_BEHAVIOR_EXAMPLE_TOKEN" in output["error"]
        assert "not set" in output["error"]
    else:
        assert output["redacted_value_present"] is True
        assert output["error"] is None
    assert (evidence / "manifest.json").is_file()
