# Evidence and reproducibility

Each verification writes a directory with this shape:

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

`manifest.json` is the semantic record. It contains the contract name, mode, verdicts, sanitized observations, and field-level differences. Its digest is SHA-256 over canonical JSON with sorted object keys and no insignificant whitespace.

`run.json` contains non-semantic execution details such as the contract path and durations. A machine taking longer to start a server does not change the semantic digest.

Scenario directories preserve contract order with numeric prefixes. Tree observations sort names. SQLite queries must define any ordering they need with `ORDER BY`.

## Baselines

A baseline records normalized and sanitized call and effect observations. The document includes its own semantic digest. Verification recalculates that digest before using the baseline and fails closed if it differs.

Commit baselines when they represent reviewed behavior. A changed digest is a compact identity, not a substitute for reviewing the JSON diff.

## Secret handling

Values resolved from `from_env` are registered as secrets. Before persistence, the sanitizer replaces those values in strings and redacts object keys that look like credentials, tokens, authorization fields, secrets, or passwords. Bearer credentials and OpenAI-style keys receive an additional pattern-based pass.

No sanitizer can infer every secret. Declare sensitive values through `from_env`, keep observed roots narrow, and inspect evidence before uploading it from CI.
