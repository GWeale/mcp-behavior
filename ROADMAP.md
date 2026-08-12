# Roadmap

v0.1 focuses on deterministic scenario execution, declared effects, and inspectable evidence. The following work is ranked by expected user value and design dependency.

## 1. Controlled repeat runs and flake detection

Run the same selected scenario under a fixed repetition policy. Report stable matches, stable divergences, and inconsistent observations separately. Preserve every attempt while keeping one deterministic summary manifest.

This comes first because it establishes the data model needed by minimization and performance work.

## 2. Docker-backed isolation

Add an opt-in runner that mounts declared workspaces and passes only declared environment values. Keep the local trusted-code runner as the default. This reduces accidental host access but does not claim to make arbitrary hostile programs safe.

## 3. Failure-input minimization

Given a deterministic divergence, reduce structured call arguments while preserving the same difference path and verdict. Store the original and reduced cases as evidence.

## 4. Generated and property-based scenarios

Generate bounded inputs from explicit strategies. Seeds, generated cases, and shrink history must be recorded so every failure can be replayed without the generator.

## 5. Protocol-version matrices

Run one scenario contract against declared MCP protocol modes and SDK combinations. Keep protocol conformance out of scope; the matrix should expose behavior changes after successful negotiation.

## 6. Additional state observers

Evaluate read-only Postgres probes and a mocked-HTTP recorder. Each observer needs deterministic ordering, hard output bounds, explicit credentials, and a useful local test stand-in before it joins the core package.

## 7. Third-party observer and comparator SDK

Publish an extension API only after at least two external implementations prove the seam. The SDK must version its input/output records and preserve sanitization and evidence invariants.

## 8. Performance and concurrency testing

Add bounded concurrency scenarios, latency budgets, warm-up policy, and reproducible summaries. Timing thresholds must stay out of semantic behavior digests unless a contract declares them as assertions.

## 9. Additional report formats

Add formats only when a real consumer cannot use JSON, Markdown, or JUnit. SARIF is the first candidate because it can attach field-level behavior differences to code-hosting interfaces.

## Deliberate exclusions

The project will not add a hosted dashboard, user authentication system, paid control plane, LLM judge, or generalized plugin marketplace. Those products require different security, privacy, and operating models.
