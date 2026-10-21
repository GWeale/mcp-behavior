# ADR 0005: Controlled repeat runs

Status: accepted design; not implemented in the public CLI or contract parser

## Problem

One run cannot distinguish consistent behavior from a changing observation. Repeats
must preserve each attempt, reset state, and separate verified differences from
failures to execute. Retrying until a run passes would hide useful evidence.

## Interfaces considered

**A. A contract-level policy.** A proposed `repeat` field lets the existing command
request several attempts:

```yaml
# Proposed syntax; current version 1 contracts reject this field.
repeat:
  attempts: 3
  workspace: fresh
  total_seconds: 120
```

Caller: `mcp-behavior verify repeated.yaml`. This keeps the policy in reviewable YAML,
but changes what the existing API returns and what its evidence directory means.

**B. An explicit repeat coordinator.** A separate proposed command/API wraps the
existing single-run verifier:

```python
# Proposed API, not an import available in this release.
summary = verify_repeated(
    "mcp-behavior.yaml", "evidence", attempts=3, workspace_policy="fresh", total_seconds=120
)
```

Caller: `mcp-behavior repeat mcp-behavior.yaml --attempts 3 --total-seconds 120`.
The contract still describes one scenario execution. The coordinator owns repetition
and returns a distinct repeat report; `verify(...)` retains its current result type.

Choose B for an initial implementation. The extra entry point expresses a real
behavior change without silently changing existing callers. Neither interface is
shipped by this ADR. A later implementation needs schema and CLI compatibility tests.

## Execution policy

- Validate all contracts and bounds before starting: 1–100 attempts, one finite
  total budget, no concurrent attempts, and no success-based early stopping.
- Run attempts in ordinal order. Within each attempt retain scenario order and the
  current reference-before-candidate ordering. Both targets belong to the same
  attempt; do not compare different attempts as if they were reference/candidate.
- Require a fresh, separate workspace for each target and attempt. Resolve source
  paths relative to the original contract, not a temporary directory. Run declared
  setup and cleanup on every attempt, including cleanup after partial failure.
- Reject effects using absolute roots outside their declared workspace unless a
  future explicit external-state reset policy is provided. Fresh directories alone
  cannot reset a remote database or an external service; the caller must provision
  those resources deterministically or choose a different experiment.
- The total budget includes setup, connection, calls, observation and cleanup.
  Reserve cleanup time. If the budget stops the sequence, preserve completed
  attempts and record missing attempts as execution uncertainty, never a mismatch.

## Evidence and aggregation

Preserve the existing version 1 evidence under `attempts/001/`, `attempts/002/`, and
so on. A new `kind: repeat-summary`, `schema_version: 1` envelope contains the policy,
ordered `(ordinal, verdict, semantic_digest)` records, counts by verdict, aggregate
verdict, completeness and stability. Store timings and local paths in a separate
repeat `run.json`; they do not enter the summary digest.

| Observations | Aggregate verdict | Stability |
|---|---|---|
| All attempts complete, same digest and verdict | That verdict | stable |
| Complete attempts disagree on verdict | `DIVERGE` | variable-verdict |
| Complete attempts match but digests vary | `MATCH` | variable-observation |
| No verified divergence, at least one unknown or missing attempt | `INCONCLUSIVE` | unknown |
| A verified divergence and an unknown or missing attempt | `DIVERGE` | unknown |

This preserves the core's existing precedence: a verified failure is not erased by
an unrelated timeout. A timeout itself never supplies a verified difference. Counts
and completeness make the uncertainty visible even when a known failure determines
the exit code. All-`DIVERGE` attempts with different digests are variable-observation.

Different complete digests do not automatically mean a flaky test. A tolerance or
partial expectation may allow different observed values while every assertion still
passes. Report the variation and its paths; reserve a flaky-behavior description for
the changing assertion results, and never apply it to infrastructure timeouts.

Compute the digest from UTF-8 canonical JSON with sorted keys and compact separators,
excluding the digest field itself. Include policy, attempt order and counts. The same
deterministic observations under the same policy yield the same summary digest;
changing the number or order of attempts deliberately changes it. Do not hash timing,
absolute paths, raw exception strings, environment values or wall-clock timestamps.

## Executable design check

Run `uv run python prototypes/repeats/check_summary.py`. The dependency-free design
model checks stable identical attempts, observation variation, changing verdicts,
and uncertainty without changing the production runner. It consumes already sanitized
semantic digests, not raw MCP data. It is not a repeat-run implementation.

See [ADR 0003](0003-evidence.md), [workspace policy](0004-isolated-target-workspaces.md),
and [current verdict precedence](../../src/mcp_behavior/models.py).
