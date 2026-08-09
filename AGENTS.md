# Repository working agreements

- This is a clean-room public project. Do not copy code, fixtures, branding, or confidential details from any private repository.
- Read `CONTEXT.md`, `STATUS.md`, and relevant ADRs before changing architecture or public interfaces.
- Keep the public API centered on `verify(...)`; hide transport, lifecycle, normalization, comparison, and evidence coordination behind it.
- Add an interface only when behavior genuinely varies. Test observable outcomes through public interfaces.
- Runtime dependencies require a written justification in `docs/DEPENDENCIES.md`.
- Never persist credentials, authorization headers, or raw environment values in contracts, logs, snapshots, or evidence.
- Treat configured MCP servers and custom probes as trusted code. Do not describe process or path controls as a hostile-code sandbox.
- Use `uv` for environments and commands.
- Before handoff, run the smallest relevant test. Before a release candidate, run `uv run python scripts/release_gate.py`.
- Maintain `STATUS.md` after material work.
- Do not create a remote repository, push, publish, or change remote settings without George's explicit approval.
