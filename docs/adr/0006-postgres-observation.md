# ADR 0006: Prove Postgres observation through a custom probe first

- Status: accepted design; Postgres observer not implemented
- Date: 2026-10-20

## Context

The built-in SQLite observer already provides read-only, ordered table snapshots.
Postgres requires a driver or client executable, credential handling, server-side
limits, and a database role whose permissions are independent of the MCP server's
writer role. Adding a `kind: postgres` field would make all of those choices part
of the contract before there is a working adapter to review.

## Alternatives

| Option | Benefit | Cost and boundary |
| --- | --- | --- |
| Built-in observer backed by a Python driver | One documented contract surface; direct streaming and cancellation | Adds a runtime dependency and commits to connection, SQL, value-encoding, and version support |
| External custom command using a driver or `psql` | Uses the existing version 1 probe protocol; consumer controls client and database versions | Consumer must implement safe connection setup, JSON encoding, timeouts, and query review |
| Built-in shell wrapper around `psql` | No Python driver | Still requires an executable, inherits CLI/version differences, and does not remove the safety or encoding work |

## Decision

Use the existing custom-command observer for a first Postgres implementation.
Follow the [implementation specification](../POSTGRES_OBSERVER.md). Add no driver,
`psql` requirement, contract field, or runtime dependency to MCP Behavior now.
This ADR specifies an implementation gate; it does not advertise a shipped
Postgres adapter or a tested database integration.

A built-in adapter needs a real consumer case and the spec's integration checks
before reconsideration. Its output must remain ordinary JSON accepted by today's
normalization, assertions, comparisons, and evidence writer. Do not introduce a
database-specific verdict or evidence format.

## Consequences

An external probe may own a private driver dependency. The core continues to own
process time and output limits, registered-secret redaction, and verdict mapping.
Database-side read-only enforcement and query review remain the probe/operator's
responsibility. Core process bounds are not a database permission system.

The proposal follows the narrow subprocess seam in
[ADR 0002](0002-core-and-adapters.md) and preserves
[sanitized evidence](0003-evidence.md). A future dependency proposal must explain
why the custom-command approach failed for the demonstrated workload.
