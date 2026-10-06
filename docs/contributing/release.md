# Release process

Every workspace distribution shares one version. The `members` list under `[tool.uv.workspace]` in the root `pyproject.toml` names the distributions. `scripts/bump_version.py` writes it to every version-bearing file, and CI fails when the files disagree.

`scripts/release.py` runs every step below and refuses a step that does not fit the version or the branch. `uv run python scripts/release.py --help` lists its subcommands, and its module docstring explains each guard. The Release workflow (`.github/workflows/release.yml`) publishes every distribution's wheel to PyPI on every `v*` tag. A tag push cannot be undone.

## Tracks

The version decides the branch a release ships from.

| Track | Ships from | Purpose |
| --- | --- | --- |
| alpha (`vX.Y.Z-alpha.N`) | `dev` | Staging. The hosted MCP deployment pins it. `install.sh` never resolves it. |
| beta (`vX.Y.Z-beta.N`) | `main` | The release that `install.sh` resolves. |
| stable (`vX.Y.Z`) | `main` | What a plain `pip install` resolves, from v1.0. |

An alpha and the beta that it becomes share `X.Y.Z`, so `0.5.0-alpha.2` promotes to `0.5.0-beta.1`. An alpha does not stamp `CHANGELOG.md`: its notes stay under `## [Unreleased]` until the beta stamps them. `pip install --pre` takes the highest pre-release, so it can resolve an alpha over a beta. Pin the exact version when you need the beta from PyPI.

## Cut an alpha

1. Open the release pull request into `dev`:

   ```bash
   uv run python scripts/release.py alpha-pr version=0.6.0-alpha.1   # a new alpha line
   uv run python scripts/release.py alpha-pr prerelease              # the next alpha in the line
   ```

2. After the pull request merges, publish from `dev`:

   ```bash
   git checkout dev && git pull
   uv run python scripts/release.py publish
   ```

## Cut a beta

1. Make sure that `CHANGELOG.md` holds every change under `## [Unreleased]` on `dev`.
2. Open the release pull request into `main`. Use `beta` to promote the current alpha, `prerelease` for the next beta in a line, or `version=X.Y.Z`:

   ```bash
   uv run python scripts/release.py release-pr beta
   ```

3. After the pull request merges, publish from `main`:

   ```bash
   git checkout main && git pull
   uv run python scripts/release.py publish
   ```

   `publish` builds the wheels and installs them in a throwaway virtualenv before it asks for confirmation. It then pushes the tag, watches the Release workflow, and verifies the release.

4. If the release changes `.cursor-plugin/plugin.json` or `.mcp.json`, submit the Cursor Marketplace listing from `main` at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish). Cursor reviews each update by hand.

To check a release again later, run `uv run python scripts/release.py verify vX.Y.Z`. To check the wheels on the other platform, install the PEP 440 version there, which differs from the tag (`v0.6.0-beta.1` is `0.6.0b1`):

```bash
uvx --from "pipefy-cli==0.6.0b1" pipefy --version
uvx "pipefy-mcp-server==0.6.0b1" --help
```

## Keep `dev` and `main` reconciled

`release-pr` refuses to run while `main` has commits that `dev` lacks. `.github/workflows/backmerge.yml` opens a back-merge pull request into `dev` whenever that happens.

- **Merge a back-merge pull request with a merge commit, never a squash or a rebase.** Both drop the second parent, so `dev` never gains `main`'s ancestry and `release-pr` stays blocked. If it happens anyway, the next run opens an ancestry repair pull request.
- When the merge conflicts, the workflow opens an issue labelled `back-merge` that names the paths and the commands to resolve them. Resolve the conflict by hand. `CHANGELOG.md` conflicts on every release.
- A red DCO check on a back-merge pull request is expected and blocks nothing. The pull request body names the commits that cause it.
- Checks run on a back-merge pull request only when the `BACKMERGE_TOKEN` secret is set. Use a GitHub App token or a fine-grained token scoped to this repository with `contents: write`, `pull-requests: write`, and `issues: write`.

## Packaging smoke failures

`.github/workflows/packaging-smoke.yml` installs the wheels from the index every day, outside `uv.lock`, and opens an issue labelled `packaging-smoke-failure` when an install breaks. Fix the dependency bound, then close the issue once a run is green.

## Repository setup

Each distribution needs a [Trusted Publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/) on PyPI, and a new distribution needs PyPI's pending-publisher flow for its first upload. The workflow uses OIDC, so no PyPI token is stored.
