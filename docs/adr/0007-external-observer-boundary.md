# ADR 0007: Keep extensions at the versioned subprocess boundary

- Status: accepted for the alpha; no general extension SDK published
- Date: 2026-10-20

## Two implemented cases

[json_probe.py](../../examples/external-observers/json_probe.py) reads a JSON
invoice document, excludes storage metadata, and sorts invoice rows by ID.
[sqlite_probe.py](../../examples/external-observers/sqlite_probe.py) reads the same
projection from a read-only SQLite connection. Both return the same versioned
JSON shape and run as separate processes without importing `mcp_behavior`.
Their [runnable contract generator](../../examples/external-observers/run.py)
uses ordinary command observers and existing JSON equality assertions.

These are clean-room repository examples of external processes, not third-party
adoption or independent integrations. Their
[behavior tests](../../tests/test_external_observer_examples.py) establish the
shared interface with concrete input and stored state.

## Alternatives

An importable Python observer/comparator base class would expose internal
contracts, async lifecycle, exception classes, and dependency versions. Neither
case needs those details. A registry of plugin names would also need discovery,
installation, version negotiation, and trust rules without a demonstrated caller.

The existing subprocess seam handles both cases. Projection belongs in the
observer; comparison remains the existing JSON comparison and assertion engine.
No example requires executing an external comparator or accepting an external
verdict, so this change does not invent that interface.

## Decision

Document the version 1 JSON subprocess boundary in [EXTENSIONS.md](../EXTENSIONS.md).
Core owns invocation without a shell, input construction, time and output limits,
normalization, registered-secret sanitization, comparison, evidence, and verdicts.
Probes own source access, source-specific limits, domain validation, and projection
into JSON. They cannot mark their own result `MATCH`, `DIVERGE`, or `INCONCLUSIVE`.

`probe_protocol.py` is shared example code, not an installed SDK or a public
import path. The output's `version` is a domain payload field checked by the
examples and pinned by expectations; core currently accepts any JSON value and
does not negotiate payload versions. Keep these two version layers distinct.

The alpha's compatibility policy still applies. A future protocol change needs a
new input version and explicit consumer migration; a future payload change needs
a new payload version and reviewed expectations/baselines. Do not silently reuse
version 1 with incompatible meanings.

## Consequences and reconsideration gate

Consumers can use another language or a private driver without adding project
runtime dependencies. An observation failure maps to `INCONCLUSIVE`; only a
completed comparable value mismatch maps to `DIVERGE`. A semantic projection
intentionally omits information, so contracts must describe what they stop testing.

Reconsider a general SDK only when two actual consumer integrations need a shared
capability this protocol cannot express. Capture their code and failure behavior
first. Generalizing these two invoice fixtures into an in-process plugin API
would add surface area without resolving a demonstrated limitation.

This preserves [ADR 0002](0002-core-and-adapters.md) and
[ADR 0003](0003-evidence.md); it adds no core public symbol, registry, dependency,
or new contract kind.
