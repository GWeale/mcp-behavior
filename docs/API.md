# Python API

MCP Behavior exposes one verification operation in synchronous and asynchronous forms.

```python
from pathlib import Path

from mcp_behavior import Verdict, verify

report = verify(
    "mcp-behavior.yaml",
    Path(".mcp-behavior/evidence"),
)

if report.verdict is Verdict.DIVERGE:
    for scenario in report.scenarios:
        for call in scenario.calls:
            for difference in call.differences:
                print(difference.path, difference.message)
```

## Verification

```python
verify(
    contract_path,
    evidence_dir,
    target_overrides=None,
    *,
    names=(),
    tags=(),
) -> VerificationReport
```

`verify_async(...)` has the same parameters and returns an awaitable report. Call the async form when an event loop is already running. The synchronous form rejects nested event-loop use instead of hiding a thread or loop.

`target_overrides` maps an existing target name to a complete `TargetSpec`. It is intended for test harnesses that need an ephemeral URL, command, or workspace without rewriting the reviewed contract. Unknown target names fail before execution.

```python
from pathlib import Path

from mcp_behavior import TargetSpec, verify

report = verify(
    "mcp-behavior.yaml",
    ".mcp-behavior/evidence",
    target_overrides={
        "candidate": TargetSpec(
            name="candidate",
            transport="http",
            url="http://127.0.0.1:49152/mcp",
            workspace=Path(".mcp-behavior/candidate").resolve(),
        )
    },
)
```

An override replaces the complete compiled target. Construct it with the same transport invariants documented in [the contract reference](CONTRACT.md).

## Baseline recording

```python
record(
    contract_path,
    baseline_path=None,
    *,
    names=(),
    tags=(),
) -> str
```

`record(...)` returns the baseline's semantic SHA-256 digest. `record_async(...)` is the event-loop-safe form.

## Result types

The package exports these immutable result types:

| Type | Key fields |
|---|---|
| `VerificationReport` | mode, verdict, scenarios, semantic digest, evidence directory, exit code |
| `ScenarioReport` | name, verdict, calls, effects, error, duration |
| `CallReport` | name, tool, sanitized arguments, verdict, differences, candidate, reference, duration |
| `EffectReport` | name, kind, verdict, differences, candidate, reference, duration |
| `Difference` | path, message, reference value, candidate value |
| `Verdict` | `MATCH`, `DIVERGE`, `INCONCLUSIVE` |

Candidate and reference values in returned reports are normalized and sanitized. Raw secret-bearing values are not exposed as a second result channel.
