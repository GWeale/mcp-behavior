# ADR 0002: One verification core with narrow adapters

Status: accepted

## Context

The verifier coordinates contracts, MCP lifecycle, observations, comparison, verdicts, and evidence. Exposing those mechanics would force callers to reproduce policy and make refactors expensive.

## Decision

Expose `verify(contract_path, evidence_dir, target_overrides=None) -> VerificationReport` and immutable report models.

Keep these internal:

- Contract compilation and environment resolution
- MCP connection and process lifecycle
- Scenario execution and cleanup
- Normalization and redaction
- Comparison and verdict aggregation
- Evidence serialization

Use a target seam because stdio and Streamable HTTP are two real adapters. Use observer and comparator registries because v0.1 has multiple implementations of each. Do not create a general plugin API in v0.1. A custom probe is a deliberately narrow subprocess protocol, not an in-process plugin framework.

## Invariants

- Scenarios execute in declared order.
- Cleanup is attempted after setup begins, even after failures.
- Persistent evidence never receives unsanitized secrets.
- `DIVERGE` requires completed comparable observations.
- Execution/configuration uncertainty yields `INCONCLUSIVE`, never a false match.
- A target is only contacted when explicitly declared or overridden.
