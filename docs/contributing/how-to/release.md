# Release procedure

A maintainer starts each release manually. Preparation enters `dev` through a PR. Publication uses a candidate, a fixed commit selected for release. The release command promotes that candidate to `main` after package publication and public installation tests succeed.

`main` contains the latest completed beta or stable release. Normal releases need no merge from `main` back into `dev`. Development continues in `dev` while a separate `release/vX` branch holds the candidate.

## Instructions for agents

When a maintainer asks you to follow `RELEASE.md`, perform the procedure below. Cursor, Claude Code, and Codex use the same commands. Read the repository instructions before executing them.

1. Determine the requested version or bump from the maintainer's request.
2. Ask for the version only if the request does not identify one.
3. Inspect the release status before creating a new preparation PR.
4. Execute the authorized preparation, publication, and recovery commands.
5. Wait for required human reviews before continuing past a review gate.
6. Report the version, candidate SHA, PRs, workflow result, and final state of `main`.

Respect the maintainer's permissions for commits, pushes, publication, and abandonment. The `--yes` flag skips a command prompt. It does not grant permission or approve a PR. Never approve your own candidate or bypass repository rules.

A missing review is a pause in the same release. After approval, resume the recorded candidate. Do not select the latest `dev` commit automatically when resuming.

## Prerequisites

Use a clone of `pipefy/ai-toolkit` with no uncommitted changes, with Python, `uv`, Git, and authenticated `gh`. A fork does not work, because the command reads the repository from `origin`. Run commands from the repository root. The command reads the release ledger through the GitHub API, not from a local branch. The maintainer needs repository write access and permission to publish tags and update workflow files. Keep credentials in the existing Git and `gh` authentication stores.

PyPI Trusted Publishers must cover all workspace distributions under `.github/workflows/release.yml`. The workflow uses OIDC, a short-lived publishing credential. It does not require a PyPI token in the clone.

An administrator must apply the repository rules in [Activation](#activation) before the first release. The command refuses publication when those rules are absent.

The files in `main` must equal the files of the tag that matches the version in `main`. `release-pr`, `doctor`, and `publish` refuse otherwise, with the message "main differs from its published source". After activation, the promotion merge keeps this true. If `main` received commits after its tag, for example a fix merged directly into `main`, reconcile it first. The one-time procedure is in [Activation](#activation).

Inspect existing progress:

```bash
uv run python scripts/release.py status
```

If a release is active, recover or explicitly abandon it before starting another. This rule includes alphas and failed runs. Actions concurrency alone does not preserve that restriction after a workflow stops.

## Prepare the release

Select a bump accepted by `scripts/bump_version.py`:

| Argument | Result |
| --- | --- |
| `major`, `minor`, `patch` | Increment the selected version component. |
| `prerelease` | Increment the current prerelease suffix. |
| `beta` | Convert an alpha into the first beta of the same version. |
| `version=X.Y.Z` | Use an explicit version, with a prerelease suffix if needed. |

`major`, `minor`, and `patch` drop a prerelease suffix: `0.5.5-beta.1` plus `patch` is `0.5.6`. `prerelease` on a stable version produces an alpha, which `release-pr` rejects. For the next beta of a beta line, use `prerelease`.

For a beta or stable release, run:

```bash
uv run python scripts/release.py release-pr prerelease
```

Replace `prerelease` with the agreed bump. The command creates a branch from `origin/dev`, updates shared versions and exact dependency pins, and refreshes `uv.lock`. It stamps the `Unreleased` notes, commits with DCO sign-off, pushes the preparation branch, and opens a PR into `dev`.

Review the version files, dependency pins, plugin manifests, changelog, and lockfile. Wait for CI and a human review. Merge the preparation PR into `dev` through the repository's normal review process.

For an alpha, use the separate preparation command:

```bash
uv run python scripts/release.py alpha-pr version=1.2.0-alpha.1
```

Replace the example version with the agreed target. Alphas retain `Unreleased` notes. Beta and stable preparation stamps those notes. Every new version requires its own build and tests.

For local preparation on an existing feature or hotfix branch, use `prepare <bump>`. It commits locally and refuses execution directly on `main` or `dev`. It does not push or open a PR.

## Select and publish the candidate

After the preparation PR merges, select its merge commit in `dev`. Use the full SHA, the exact commit identifier: `gh pr view NUMBER --json mergeCommit`. Later commits in `dev` can remain outside this release.

Inspect the selected candidate before authorizing publication:

```bash
uv run python scripts/release.py doctor --sha COMMIT_SHA
```

Replace `COMMIT_SHA` with the selected commit. The command makes sure that the version, notes, source history, and repository rules permit a release.

Start the release:

```bash
uv run python scripts/release.py publish --sha COMMIT_SHA
```

The maintainer's confirmation authorizes publication and promotion after review. The command records the candidate and expected `main` SHA in the `release-ledger` branch. It creates `release/vX` at the candidate and opens the promotion PR into `main`.

Repository rules reject updates and deletion of the candidate branch. CI runs on the candidate's exact commit. The promotion PR requires a current approval for that commit.

If CI or review is pending, the command stops before tagging. Share the promotion PR with the reviewer. After approval, continue with the recorded tag:

```bash
uv run python scripts/release.py resume vX
```

Replace `vX` with the tag printed by the command. There is no second publication confirmation. `resume` continues the authorization recorded when the maintainer started the release.

The command creates the immutable version tag. That tag starts the Release workflow. The workflow performs these steps:

1. Make sure that the candidate, tag, approval, CI, and expected `main` still match.
2. Build all workspace packages once.
3. Record each wheel's SHA-256 hash, which identifies its file contents.
4. Store the original wheels in a draft GitHub Release.
5. Install the original wheels in an empty environment and exercise their entry points.
6. Publish the GitHub Release.
7. Upload missing original wheels to PyPI.
8. Install the selected version from both public channels.
9. Exercise the installed entry points.
10. Make sure that the default installer selects a beta or stable release, or excludes an alpha.
11. Prepare the promotion commit.

The local command waits for the workflow. After success, the command makes sure that approval is current. It then promotes the GitHub-generated merge commit. The commit must have the recorded base and candidate as parents. Its files must equal the candidate's files.

The update to `main` requires its exact recorded SHA through GitHub's `updateRefs` operation. It also prohibits a forced update. If another commit reaches `main`, the update fails. The command does not overwrite that change or choose another base.

Keep the command running until it reports completion. If the agent or terminal disconnects after publication, run `resume vX` again. The command can recognize a completed promotion whose final response was lost.

## Publication and recovery

The `release-ledger` branch records identity, progress, original hashes, the GitHub Release ID, and the workflow ID. Each change appends a Git commit. Concurrent updates cannot overwrite each other. Do not edit or delete this branch manually.

Original wheels remain GitHub Release assets. They do not depend on the retention period for Actions artifacts. Do not replace or delete those assets while recovery remains necessary.

| Failure | Action |
| --- | --- |
| Review or candidate CI is pending | Wait for approval or CI, then run `resume vX`. |
| A candidate needs source corrections | Abandon it explicitly. Prepare a new version and candidate. |
| The build fails before originals reach storage | Inspect the failure. Abandon that version and prepare a new one. |
| Some PyPI uploads are missing | Run `resume vX`. The workflow uploads only the missing original files. |
| An existing upload differs from its recorded hash | Stop for maintainer review. Do not overwrite or rebuild the version. |
| Original files are missing | Stop for maintainer review. Do not replace them with a new build. |
| Public installation fails | The workflow waits up to two minutes for PyPI propagation. After that, fix the external failure, then resume. A package defect requires a new version or withdrawal. |
| The recorded promotion commit changed | Rerun the completed Release run from the Actions page. The `complete` step records the new commit and its status. Then run `resume vX`. |
| Publication succeeds but promotion fails | Run `resume vX`. Keep the same candidate, packages, and expected base. |
| Approval or `main` changes | Stop for review. Do not change the recorded identity to force progress. |

An initial build or storage failure consumes a version even if no package becomes public. This rule prevents a retry from replacing the original files with another build.

After a stop for review, the release keeps the active slot. Free it with `resume vX` once the condition no longer holds, for example after a renewed approval. If the recorded candidate or base can no longer apply, run `abandon vX` and prepare a new version.

To abandon a release, first cancel any running Release workflow. Wait until GitHub reports completion. Then record the reason:

```bash
uv run python scripts/release.py abandon vX --reason "The candidate requires a source correction"
```

Abandonment closes the promotion PR and releases the active slot. It preserves tags, original files, and the audit history. Published packages remain available. Explicit package withdrawal requires a separate maintainer decision. Do not move tags, reuse versions, or roll back `main` to hide a publication.

PyPI, GitHub Releases, and Git cannot update in one transaction. Packages can become public before `main` advances. During that interval, `main` retains the previous completed release. A failed release can leave partial public files until a maintainer recovers or withdraws them.

For additional checks of an existing public tag, run:

```bash
uv run python scripts/release.py verify vX
```

This command does not resume a release or update `main`.

## Alphas and urgent fixes

Alphas use a candidate from `dev`, the same frozen branch rules, and the same original-file recovery. They do not open a promotion PR or advance `main`, and they need no approval. The first `publish` stops until CI on `release/vX` succeeds. Then run `resume vX` to tag. Their source already enters `dev` through reviewed PRs. The default installer excludes alphas. An explicit `--version` can select one.

An urgent fix can start from the published tag when `dev` contains changes that cannot ship. Create a correction branch from that tag. Apply the correction and add its `Unreleased` notes. Prepare a newer version with `prepare <bump>`. Push the correction branch to `origin` with the maintainer's authorization. Then start the candidate:

```bash
uv run python scripts/release.py publish --sha CORRECTION_SHA --hotfix
```

Replace `CORRECTION_SHA` with the correction commit pushed to `origin`. The command creates the same frozen candidate and promotion PR. Its review authorizes the exact hotfix commit before publication.

After promotion, merge the correction branch into `dev` through a PR. Use a merge commit, because the next normal release requires the published correction in its ancestry. A squash or cherry-pick does not preserve that proof.

If `dev` already has a newer version, retain that version when resolving conflicts. Retain its unreleased work and the published hotfix section in `CHANGELOG.md`. The next candidate must keep the previous release notes unchanged and use a version newer than `main`.

Only these exceptions need source reintegration. Normal releases already contain preparation and source changes from `dev`. Their promotion merge commits do not need a backmerge.

## Package and skill compatibility

All distributions retain shared versions and exact sibling dependency pins. `install.sh` excludes draft GitHub Releases and installs packages and skills from the same selected tag. The skills command uses `https://github.com/pipefy/ai-toolkit/tree/TAG` as its source.

The skills installer records the repository as the source. The uninstaller can therefore identify the skills that belong to this toolkit. An explicit old tag or alpha also selects that tag's skills. Do not update those skills independently when a deployment requires a fixed package version.

Plugin catalogs that follow `main` advance after promotion. Client refresh delays remain possible. External consumers continue to select published versions independently.

The Cursor Marketplace listing does not follow `main`. After a release that changes `plugins/pipefy/.cursor-plugin/plugin.json` or `plugins/pipefy/.mcp.json`, submit or refresh the listing at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish). Cursor reviews each update by hand, so plan for a review round.

## Activation

An administrator must configure these rules before the first candidate starts:

1. For branches `release/**`, prohibit updates and deletion with no bypass actors. Permit branch creation.
2. For tags `v*`, prohibit updates and deletion with no bypass actors. Permit tag creation.
3. For `main`, require a PR approval and dismiss stale approvals after new commits, with no bypass actors.
4. For `main`, require the status check `release/published` with GitHub Actions selected as its source.
5. Keep required status checks on `main` loose, without requiring the candidate to merge the latest `main` history.
6. Permit merge commits on `main`. Do not require linear history or a merge queue.
7. Protect `release-ledger` against deletion and force pushes. Permit normal fast-forward updates by maintainers and Actions.
8. Allow the Release workflow to write repository contents and commit statuses. Keep PyPI Trusted Publishers active for `release.yml`.

Create every rule above as a repository ruleset. The workflow token cannot read organization ruleset details. The command reads the details of every active tag ruleset, so an organization ruleset stops the Release workflow.

Keep existing CI and review requirements. Do not configure bypass actors for the publication gate. Do not enable automatic merging of promotion PRs. The release command must perform the final update.

GitHub hides bypass actor lists from callers without ruleset administration access. An administrator must inspect those lists during activation. Runtime checks reject visible bypass actors and require the current caller's bypass state to be `never`. These checks do not prove that hidden actor lists are empty.

The first candidate requires `main` to equal its published tag. If `main` received commits after that tag, cut one release with the former procedure before this tooling merges into `dev`. Prepare the version from `dev`, merge the release PR into `main`, and tag it there. That release makes `main` equal its tag. The former back-merge returns the tag to `dev`. After this tooling merges into `dev`, the former procedure no longer works. A tag on `main` then starts the new `release.yml`, which requires a recorded candidate.

The first candidate carries the new `release.yml`. Its tag starts that workflow from the tagged commit, so activation does not depend on `workflow_dispatch` reaching the default branch.

The command requires release protocol `1` and the publication pipeline in the candidate workflow. An old alpha or hotfix branch must include that tooling before selection. This prevents the command from starting the former publication workflow.

Before the first run, disable the obsolete Back-merge workflow in GitHub Actions. Its file, script, and tests disappear from `main` when the implementation release completes. Do not use the former release command during this transition. The new publication gate blocks early promotion through `main`.

Before enabling production publication, rehearse the protected promotion in a disposable repository with the same rules. Exercise consecutive releases, changed candidate or approval, a concurrent `main` update, partial uploads, missing originals, alphas, and hotfix reintegration. Use test package destinations for upload experiments. Do not use production package versions for a rehearsal.

The rehearsal must also answer three questions that GitHub does not document. Does GitHub mark the promotion PR merged after the `updateRefs` update? Does a status posted with the workflow token satisfy a required check whose source is GitHub Actions? Does the test-merge commit keep its SHA while the promotion PR waits for more than a day?

Local tests cover Git history and simulated GitHub and package boundaries. They do not prove repository permissions, PyPI publisher configuration, or GitHub's protected-reference update behavior. If a rule rejects the exact promotion commit, stop and inspect it. Do not bypass it or substitute an unconstrained merge call.

## Maintainer checks

The shared version checker covers package versions, exact dependency pins, plugin manifests, and `uv.lock`. The package smoke test installs all published distributions in an empty environment. It exercises console entry points and an authenticated request against a local stub endpoint.

CI runs the packaging smoke before release publication. The scheduled packaging workflow also tests current wheels and published packages against fresh dependency resolution. Its schedule starts only when the workflow exists on the default branch.

A successful smoke test proves installation, startup, and the stub request. It does not prove every live API behavior. Use the affected feature's separate validation requirements when its behavior changes.
