# Release process

Releases use a signed or annotated `vX.Y.Z` tag, GitHub Actions, GitHub Releases, and PyPI trusted publishing.

For repository identity, settings, topics, and launch-page checks, follow the [GitHub publication checklist](PUBLICATION_CHECKLIST.md).

## One-time repository setup

1. Create a PyPI project and trusted publisher for `.github/workflows/release.yml` in the `pypi` environment.
2. Require approval on the GitHub `pypi` environment.
3. Protect `main` and require the CI workflow.
4. Enable private vulnerability reporting and Dependabot alerts.
5. Add `docs/assets/social-preview.png` as the repository social preview.

## Release candidate

1. Update `version` in `pyproject.toml`, `src/mcp_behavior/__init__.py`, `action.yml`, the changelog, and release notes.
2. Run `uv sync --all-groups --locked`.
3. Run `uv run python scripts/release_gate.py`.
4. Inspect `dist/SHA256SUMS`, wheel metadata, source archive contents, and the rendered README.
5. Install the wheel into a fresh Python 3.11 virtual environment and run `mcp-behavior --version` plus the expectations example.
6. Confirm the working tree is clean and CI passes on the candidate commit.

## Publish

```bash
git tag -s v0.1.0 -m "mcp-behavior 0.1.0"
git push origin v0.1.0
```

The tag workflow rebuilds from source, runs the release gate, publishes to PyPI with OIDC, and attaches the wheel, source archive, and checksums to a GitHub release.

## Verify the public release

Test from a clean environment rather than the repository checkout:

```bash
uvx --from mcp-behavior==0.1.0 mcp-behavior --version
pip index versions mcp-behavior
```

Open the GitHub release, download each artifact, and verify it against `SHA256SUMS`. Run the composite action from a separate repository before announcing the release.

If publication fails after PyPI accepts the version, do not reuse that version. Fix the problem and publish a patch release.
