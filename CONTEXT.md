# MCP Behavior context

## Thesis

MCP Behavior provides deterministic regression tests for what an MCP tool actually does, not merely what its schema claims.

## Product boundary

The project executes declared scenarios against one recorded baseline or two live MCP targets. It compares tool results and explicitly declared observable effects, then emits `MATCH`, `DIVERGE`, or `INCONCLUSIVE` with inspectable evidence.

It is not a protocol conformance suite, schema-only compatibility checker, package-integrity lockfile, Inspector replacement, model evaluation platform, hostile-code sandbox, or hosted observability service.

## Clean-room rule

All public implementation, fixtures, examples, documentation, and branding are independently authored in this repository. Private projects may motivate the problem but are not source material.

## Durable interface

```python
report = verify(contract_path, evidence_dir, target_overrides=None)
```

Callers provide paths and optional target overrides. The returned typed report is the primary test surface. Connection management, subprocess cleanup, scenario ordering, observations, normalization, comparison, verdict policy, redaction, and evidence writing stay internal.

## Technology

- Python 3.11+
- Official MCP Python SDK v2 stable line, because 2026-07-28 and legacy protocol-era negotiation are release requirements
- YAML contracts for human-authored scenarios
- Local-first, no telemetry, no model calls
