# ADR 0003: Deterministic semantic evidence

Status: accepted

## Context

Evidence must support code review and reproduction while still including useful run diagnostics such as duration. Wall-clock timestamps and timings make byte-for-byte output unstable.

## Decision

Write a versioned manifest and per-scenario files with canonical JSON: UTF-8, sorted keys, two-space indentation, and a trailing newline.

Separate semantic evidence from volatile run metadata. The semantic digest excludes timestamps, durations, absolute temporary paths, and other explicitly volatile fields. A repeated deterministic run must therefore have the same semantic digest even if diagnostic timing differs.

Raw MCP values remain in memory only while normalization and sanitization run. Persistent evidence and public report models receive the normalized, sanitized values. Authorization headers and resolved environment values are never serialized.

Normalization rules remain explicit in the reviewed contract. `run.json` records the contract path used for an execution. Per-observation value hashes and a per-scenario semantic hash make persisted values easy to identify without allowing durations into the semantic manifest.

## Directory shape

```text
evidence/
  manifest.json
  run.json
  scenarios/
    001-scenario-name/
      observation.json
      comparison.json
      effects.json
      logs.txt
```
