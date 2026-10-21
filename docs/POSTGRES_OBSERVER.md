# Read-only Postgres observer specification

Status: implementation specification, 2026-10-20. No Postgres observer is shipped
or exercised by the test suite. [ADR 0006](adr/0006-postgres-observation.md) chooses
an external custom probe first; this document defines its acceptance boundary.

## One concrete observation

After the MCP target has closed, inspect a dedicated invoice projection with
`invoice_id` as a unique key and `total_cents` as an integer. Return explicit
columns and rows in key order. Candidate and reference must use different test
databases or schemas provisioned by the fixture owner. A shared live database
would let the first target change what the second observes.

The probe consumes the existing [command input](EFFECTS.md) and returns one value:

```json
{"version":1,"state":"present","columns":["invoice_id","total_cents"],"rows":[["inv-42",10000]]}
```

This shape works with existing JSON `equals`/`contains`, recorded baselines, and
differential comparisons. The version belongs to this probe's payload, not a new
core schema. Column order is fixed. Empty results mean `rows: []`; failed queries
must exit nonzero rather than return an empty success value.

## Nonmutating query and role

Use a dedicated non-owner login with no superuser, role-creation, database-creation,
replication, bypass-RLS, or privileged inherited role. Grant only database CONNECT,
schema USAGE, and SELECT on the specific projection. The probe must not receive
the MCP target's writer credential. An operator must audit effective permissions,
including PUBLIC grants and role membership; revoking a direct grant alone does
not remove access inherited elsewhere. PostgreSQL documents ownership and these
privilege paths in its [privilege reference](https://www.postgresql.org/docs/18/ddl-priv.html).

The initial implementation accepts a reviewed, fixed query in the probe source,
not arbitrary contract SQL. Read only ordinary tables and approved views with
known definitions. Do not invoke application functions, extension functions,
security-definer routines, FDWs, or unreviewed row-security expressions. Reject
multi-statement input, DML/DDL, data-modifying CTEs, `SELECT INTO`, locking clauses,
`COPY`, `CALL`, sequence updates, and session/role changes. A SELECT/WITH prefix
check is insufficient: the
[SELECT grammar](https://www.postgresql.org/docs/18/sql-select.html) includes
locking and data-modifying CTE forms.

Open a fresh connection and start this transaction before reading any data:

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL search_path = pg_catalog;
SET LOCAL statement_timeout = '2000ms';
SET LOCAL lock_timeout = '500ms';
SET LOCAL idle_in_transaction_session_timeout = '3000ms';
SELECT invoice_id, total_cents
FROM behavior_fixture.invoice_projection
ORDER BY invoice_id COLLATE "C"
LIMIT 1001;
ROLLBACK;
```

Use an explicitly qualified table/view. `invoice_id` must be non-null and unique,
so ordering has a deterministic tie-breaker. The row cap is 1000; fetching the
1001st row detects overflow and fails instead of silently comparing a prefix.
The transaction must always roll back and the connection must close, including
on serialization, timeout, or encoding failure.

Postgres [read-only transaction mode](https://www.postgresql.org/docs/18/sql-set-transaction.html)
blocks writes to persistent tables, but permits some temporary-object operations.
It is not a sandbox for arbitrary function execution or external effects. The
restricted role, fixed reviewed projection, and explicit read-only transaction
together define this spec's nonmutation boundary; do not promise that arbitrary
user SQL is harmless. No database/schema/role/grant creation belongs in the probe.
Those are explicit local fixture provisioning steps performed separately by an
operator, using a credential the probe never sees.

## Isolation and deterministic values

Repeatable Read keeps multiple queries in one capture on a consistent snapshot.
It does not freeze an actively changing database across before/after captures or
across target runs. Each phase opens a new read-only transaction. Pause unrelated
writers or provision an isolated disposable dataset. If quiescence cannot be
established, do not interpret concurrent changes as migration divergence. See
[Postgres isolation semantics](https://www.postgresql.org/docs/18/transaction-iso.html).

Version 1 accepts only the projection's text identifiers, integer cents, and nulls.
A later projection must document exact encodings before adding decimals,
timestamps, binary values, arrays, JSON, or non-finite numbers. Do not stringify
unknown driver objects, convert exact decimals to floats, or include connection
IDs, wall-clock timestamps, database names, or host paths in semantic output.

## Bounds and credentials

Set connection timeout to 2 seconds and the probe's contract timeout to 8 seconds;
keep both inside the scenario's total budget. Client fetches must be bounded even
if server-side settings are misconfigured. Read at most 1001 rows, encode at most
64 KiB of JSON, and fail on overflow. Do not truncate a successful observation.
Core additionally enforces the contract's `limits.output_bytes`, combined command
stdout/stderr `limits.log_bytes`, operation timeout, and total timeout. Database
[statement, lock, and idle transaction timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html)
limit server work; subprocess termination alone is not a server cancellation
guarantee. Confirm the session disappears after timeout in integration tests.

Pass credentials through the command's `env` with `from_env`, for example an
`OBSERVER_DSN` mapping to the operator-supplied `MCP_BEHAVIOR_PG_DSN`. The probe
reads this value only from its environment; no DSN or password appears in argv,
YAML literals, output, exceptions, or logs. A DSN registered with core does not
automatically register every substring inside it. Suppress driver error text
that might expose individual password, username, host, or query values. Prefer
separately referenced credential variables when those values need independent
redaction. Use generic error codes on stderr and no credentials on stdout.

The core receives only successful JSON, sanitizes registered values, and stores
normal effect evidence. A completed comparable value mismatch is `DIVERGE`.
Missing variables, denied access, unavailable database, query/encoding failure,
timeout, and row/byte overflow are `INCONCLUSIVE` via nonzero probe exit or core
execution failure. They must not become an empty observation or `DIVERGE`.

## Implementation gate and local test dependency

The eventual integration job needs an explicitly enabled disposable Postgres 18
service and a separately provisioned observer role. A driver may be installed in
the probe's own environment; it is not a project runtime dependency. Never auto
connect to a developer's default database or start Docker from ordinary tests.
An opt-in test flag and fake fixture connection references must be documented.

Before claiming support, demonstrate:

- Ordered identical captures compare `MATCH`; a changed invoice total produces
  `DIVERGE` through public `verify` and normal evidence files.
- Direct writes fail with the observer role even outside the read-only capture;
  writes, modifying CTEs, locking, and unapproved function calls are unavailable
  through the probe's fixed interface. Verify persisted rows remain unchanged.
- Missing credentials, revoked SELECT, absent relations, 1001 rows, excess bytes,
  blocked/slow queries, and connection loss yield `INCONCLUSIVE` with bounded exit.
- Two reads inside one capture see the intended snapshot; later phases see a new
  snapshot. Candidate and reference fixtures do not share mutable state.
- A generated fake credential, including its separately handled password component,
  is absent from evidence and diagnostics; sessions close after success/failure.

These are required future checks, not results obtained by this documentation
change. Primary documentation above was checked 2026-10-20.
