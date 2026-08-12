# GitHub publication checklist

Use this checklist when the local release candidate is approved for publication. It separates repository setup from package publication so either step can be reviewed independently.

## Repository identity

- Repository: `GWeale/mcp-behavior`
- Visibility: public
- Description: `Parity tests for MCP migrations, including tool results and observable side effects.`
- Website: leave empty until the documentation has a stable public URL
- Topics: `mcp`, `model-context-protocol`, `testing`, `regression-testing`, `python`, `developer-tools`, `ai-agents`
- Social preview: upload `docs/assets/social-preview.png`

Confirm the README logo, demo, badges, install command, examples, security boundary, and contribution links render correctly on the repository landing page.

## Repository settings

- Enable Issues and Discussions.
- Apply the labels in `.github/labels.yml` and open the reviewed drafts from `docs/CONTRIBUTOR_ISSUES.md`.
- Disable the wiki unless it has a maintained purpose.
- Enable private vulnerability reporting, Dependabot alerts, and automated security updates.
- Protect `main`: require pull requests, the `CI / test` matrix, resolved conversations, and no force pushes or deletions.
- Preserve squash, rebase, or merge commits according to the maintainer's preference; automatically delete merged branches.

## Release plumbing

- GitHub-only source publication was approved on 2026-08-11. PyPI publishing, tags, and GitHub Releases require separate approval.
- Configure a PyPI trusted publisher for `.github/workflows/release.yml`, environment `pypi`.
- Push the reviewed `main` commit and wait for every CI job to pass.
- Confirm all twelve operating-system and Python matrix jobs pass.
- Run the composite action from a separate test repository before declaring it stable.
- Create a signed or annotated `v0.1.0` tag only after the repository and publisher settings are confirmed.
- Verify the GitHub Release, PyPI metadata, checksums, and clean-environment install using [the release process](RELEASING.md).

## First public issue set

Open issues only for work the maintainer intends to support. The reviewed drafts are in [CONTRIBUTOR_ISSUES.md](CONTRIBUTOR_ISSUES.md). The first set covers a binary comparison example, expected MCP errors, Unicode filenames, authenticated HTTP documentation, controlled repeat runs, Docker isolation, a Postgres observer design, and the future extension boundary.

Avoid a broad roadmap. Label concrete, reviewable work as `good first issue` only after the expected behavior and test seam are documented.

## Announcement readiness

- Publish release notes from `docs/releases/v0.1.0.md`.
- State the alpha stability level and supported Python versions plainly.
- Link the value-drift, wrong-effect, and nondeterminism examples.
- Include the security boundary: contracts and observed programs are trusted code.
- Invite bug reports and evidence-backed compatibility cases, not stars or vanity metrics.
