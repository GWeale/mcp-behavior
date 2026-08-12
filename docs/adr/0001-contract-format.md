# ADR 0001: YAML scenario contracts

Status: accepted

## Context

Contracts contain targets, ordered scenarios, multiple calls, normalization rules, result assertions, and effect observers. They must be readable in pull requests and produce actionable validation paths.

## Alternatives

### JSON

Has a standard parser and excellent machine interoperability, but is noisy for hand-authored scenarios and has no comments.

### TOML

Has a Python 3.11 standard-library parser and works well for shallow configuration. Nested arrays of calls, observers, and assertions become difficult to scan and edit correctly.

### YAML

Best expresses the nested, ordered scenario model and supports comments. It adds one parser dependency and requires safe loading plus strict semantic validation.

## Decision

Use a small versioned YAML subset parsed with a hardened safe loader. Reject aliases, custom tags, duplicate keys, unknown keys, unsupported JSON paths, and ambiguous scalar shapes. Validation errors identify the source file and semantic field path; YAML syntax errors include line and column.

Allow `${name}` substitution only from top-level literal JSON variables. Do not resolve environment variables through this mechanism. Credential-bearing target and command values use `from_env`, which registers the resolved value with the sanitizer without adding it to the contract.

## Consequences

The compiler owns defaults, path resolution, literal substitution, environment references, and strictness. JSON may later be accepted as a YAML subset without a second public model.
