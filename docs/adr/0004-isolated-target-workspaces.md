# ADR 0004: Target workspaces isolate observable effects

- Status: Accepted
- Date: 2026-08-08

## Context

Differential verification can run the same setup and call sequence against two targets. If both targets share a directory, the first run can change the state seen by the second. File and database effects then depend on execution order instead of implementation behavior.

## Decision

Every target has an explicit workspace. Relative observer roots and commands without their own `cwd` resolve there. Differential scenarios that use setup, cleanup, or observers must give candidate and reference different workspace paths.

Targets still run sequentially. This keeps evidence order stable and avoids concurrent mutations from two servers.

## Consequences

Simple call-only differential contracts can share a workspace. Stateful contracts must provision two directories. MCP Behavior provides path containment, but the workspace is not an OS sandbox.
