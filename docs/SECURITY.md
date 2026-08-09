# Security model

MCP Behavior runs developer-selected MCP servers and commands. It assumes that code is trusted.

## Controls

- Commands use argument vectors without a shell.
- Timeouts trigger process-tree termination for launched commands and stdio servers.
- Stdout, stderr, tool results, and observer results have byte limits.
- Server stderr is drained continuously while only a bounded prefix is retained.
- Relative observer paths cannot leave their declared root.
- Tree observers do not follow symlinks.
- SQLite observers open databases read-only, enable `query_only`, accept `SELECT` or `WITH`, and cap rows.
- Sensitive environment and header values are resolved at runtime and sanitized before persistence.
- Cleanup runs after partial scenario execution.

## Outside the boundary

These controls are not a sandbox. Trusted code can read any file and access any network resource allowed to the current process. Absolute observer roots are also allowed because some integration tests need them.

Use an OS sandbox, container, VM, or restricted CI runner for code you do not trust. Scope credentials to the test account and give the process only the permissions the scenario needs.

Report a vulnerability through GitHub's private security advisory flow. Do not open a public issue containing credentials, exploit details, or private evidence.
