# ADR 0003: Deterministic semantic evidence

Status: accepted

## Context

Evidence must support code review and reproduction while still including useful run diagnostics such as duration. Wall-clock timestamps and timings make byte-for-byte output unstable.

## Decision

Write a versioned manifest and per-scenario files with canonical JSON: UTF-8, sorted keys, two-space indentation, and a trailing newline.

Separate semantic evidence from volatile run metadata. The semantic digest excludes timestamps, durations, absolute temporary paths, and other explicitly volatile fields. A repeated deterministic run must therefore have the same semantic digest even if diagnostic timing differs.

Raw MCP values may be retained only after recursive redaction and output-size enforcement. Authorization headers and environment values are never serialized. Normalization rules and every ignored path are included in evidence so omitted differences remain reviewable.

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
