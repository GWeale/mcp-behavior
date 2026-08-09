# GitHub publication checklist

Use this checklist when the local release candidate is approved for publication. It separates repository setup from package publication so either step can be reviewed independently.

## Repository identity

- Repository: `GWeale/mcp-behavior`
- Visibility: public
- Description: `Deterministic regression tests for what MCP tools actually do.`
- Website: leave empty until the documentation has a stable public URL
- Topics: `mcp`, `model-context-protocol`, `testing`, `regression-testing`, `python`, `developer-tools`, `ai-agents`
- Social preview: upload `docs/assets/social-preview.png`

Confirm the README logo, demo, badges, install command, examples, security boundary, and contribution links render correctly on the repository landing page.

## Repository settings

- Enable Issues and Discussions.
- Disable the wiki unless it has a maintained purpose.
- Enable private vulnerability reporting, Dependabot alerts, and automated security updates.
- Add a `pypi` environment with required reviewer approval.
- Protect `main`: require pull requests, the `CI / test` matrix, resolved conversations, and no force pushes or deletions.
- Preserve squash, rebase, or merge commits according to the maintainer's preference; automatically delete merged branches.

## Release plumbing

- Configure a PyPI trusted publisher for `.github/workflows/release.yml`, environment `pypi`.
- Push the reviewed `main` commit and wait for every CI job to pass.
- Run the composite action from a separate test repository before declaring it stable.
- Create a signed or annotated `v0.1.0` tag only after the repository and publisher settings are confirmed.
- Verify the GitHub Release, PyPI metadata, checksums, and clean-environment install using [the release process](RELEASING.md).

## First public issue set

Open issues only for work the maintainer intends to support. Useful first milestones are:

- Windows process-tree containment and CI coverage
- richer semantic matchers for unordered collections and numeric tolerances
- opt-in observer plugins with a stable extension interface
- an evidence schema compatibility policy before version 2
- published examples for authentication and long-lived HTTP sessions

Avoid a broad roadmap. Label concrete, reviewable work as `good first issue` only after the expected behavior and test seam are documented.

## Announcement readiness

- Publish release notes from `docs/releases/v0.1.0.md`.
- State the alpha stability level and supported Python versions plainly.
- Link one expectations example, one baseline example, and one differential example.
- Include the security boundary: contracts and observed programs are trusted code.
- Invite bug reports and evidence-backed compatibility cases, not stars or vanity metrics.
