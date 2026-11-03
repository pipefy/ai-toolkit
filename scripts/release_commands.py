"""Maintainer actions before and after the release workflow."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

from release_gates import (
    finish_promotion,
    release_notes,
    require_candidate,
    select_candidate,
)
from release_github import GitHub, Journal
from release_state import Release, ReleaseError


def github_client() -> GitHub:
    repo = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return GitHub(repo)


def ensure_candidate_pr(github: GitHub, journal: Journal, release: Release) -> None:
    branch = github.optional(f"git/ref/heads/{release.branch}")
    if branch is None:
        github.api(
            "git/refs",
            "POST",
            {"ref": f"refs/heads/{release.branch}", "sha": release.candidate},
        )
    elif branch["object"]["sha"] != release.candidate:
        raise ReleaseError("The recorded candidate branch changed. Stop for review.")
    if release.kind == "alpha" or release.pr:
        return
    owner = github.repo.split("/")[0]
    existing = github.pages(f"pulls?state=all&base=main&head={owner}:{release.branch}")
    if existing:
        if len(existing) != 1 or existing[0]["state"] != "open":
            raise ReleaseError(
                "The promotion PR was closed or is ambiguous. Stop for review."
            )
        pull = existing[0]
    else:
        notes = release_notes(
            github.text_at("CHANGELOG.md", release.candidate), release.version
        )
        body = (
            "## Summary\n\n"
            f"- Promote `{release.tag}` from the fixed candidate `{release.candidate}`.\n"
            "- Publication and public installation tests must pass before main advances.\n"
            "- The release command uses a merge commit whose files match the candidate.\n\n"
            "## Test plan\n\n"
            "- [ ] Candidate CI succeeds.\n"
            "- [ ] Original packages pass installation tests before publication.\n"
            "- [ ] Public packages pass installation tests before promotion.\n\n"
            "## Docs / skills\n\n"
            f"{notes}\n"
            "## Legal / contributions\n\n"
            "- [ ] Candidate commits satisfy the repository DCO check.\n\n"
            "Review this candidate. After approval, the initiating maintainer resumes the release command.\n"
            "Do not merge or update this branch manually.\n"
        )
        pull = github.api(
            "pulls",
            "POST",
            {
                "base": "main",
                "head": release.branch,
                "title": f"chore: promote {release.tag}",
                "body": body,
            },
        )
    release.pr = pull["number"]
    journal.save(release)
    print(f"Candidate review: https://github.com/{github.repo}/pull/{release.pr}")


def workflow_runs(github: GitHub, release: Release) -> list[dict[str, Any]]:
    result = github.api(
        f"actions/workflows/release.yml/runs?event=push&head_sha={release.candidate}&per_page=100"
    )
    return [
        run
        for run in result["workflow_runs"]
        if run["head_branch"] == release.tag and run["head_sha"] == release.candidate
    ]


def watch_workflow(github: GitHub, release: Release, *, retry: bool) -> None:
    deadline = time.monotonic() + 90
    runs = workflow_runs(github, release)
    while not runs and time.monotonic() < deadline:
        time.sleep(3)
        runs = workflow_runs(github, release)
    if not runs:
        raise ReleaseError(
            f"No Release workflow appeared for {release.tag}. Inspect Actions before retrying."
        )
    if len(runs) != 1:
        raise ReleaseError(
            f"Multiple publication runs exist for {release.tag}. Stop for review."
        )
    run = runs[0]
    if run["status"] == "completed" and run["conclusion"] != "success":
        if not retry:
            raise ReleaseError(
                f"Publication failed. Use 'release.py resume {release.tag}' to retry the original files."
            )
        github.api(f"actions/runs/{run['id']}/rerun", "POST")
        # GitHub can still report the previous attempt immediately after rerun.
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            fresh = github.api(f"actions/runs/{run['id']}")
            if fresh["run_attempt"] > run["run_attempt"]:
                break
            time.sleep(3)
        else:
            raise ReleaseError(
                "The workflow retry did not start. Inspect Actions before retrying."
            )
    watched = subprocess.run(
        ["gh", "run", "watch", str(run["id"]), "--repo", github.repo, "--exit-status"],
        check=False,
    )
    if watched.returncode:
        raise ReleaseError(
            f"Publication run {run['id']} failed. Inspect it, then use 'release.py resume {release.tag}' to retry the original files."
        )


def advance(
    github: GitHub, journal: Journal, release: Release, *, retry: bool = False
) -> None:
    if release.phase == "complete":
        print(f"Release {release.tag} is complete.")
        return
    if release.phase == "abandoned":
        raise ReleaseError(f"Release {release.tag} is abandoned. Select a new version.")
    if (
        release.phase == "published"
        and github.ref("heads/main") != release.expected_main
    ):
        finish_promotion(github, journal, release)
        return
    ensure_candidate_pr(github, journal, release)
    tagged = github.optional(f"git/ref/tags/{release.tag}")
    require_candidate(github, release, tagged=tagged is not None)
    if tagged is None:
        github.api(
            "git/refs",
            "POST",
            {"ref": f"refs/tags/{release.tag}", "sha": release.candidate},
        )
    watch_workflow(github, release, retry=retry)
    journal = Journal(github)
    release = journal.get(release.tag)
    if release.kind != "alpha":
        finish_promotion(github, journal, release)
    elif release.phase != "complete":
        raise ReleaseError("The alpha workflow did not record completion.")
    print(
        f"Release {release.tag} is complete: https://github.com/{github.repo}/releases/tag/{release.tag}"
    )


def start(github: GitHub, sha: str, *, hotfix: bool = False) -> None:
    journal = Journal(github)
    if journal.contents["active"]:
        raise ReleaseError(
            f"Release {journal.contents['active']} is active. Use resume or abandon first."
        )
    release = select_candidate(github, sha, hotfix=hotfix)
    if release.tag in journal.contents["releases"]:
        raise ReleaseError(
            f"Version {release.tag} was already used. Select a new version."
        )
    journal.save(release)
    advance(github, journal, release)


def resume(github: GitHub, tag: str) -> None:
    journal = Journal(github)
    advance(github, journal, journal.get(tag), retry=True)


def abandon(github: GitHub, tag: str, reason: str) -> None:
    journal = Journal(github)
    release = journal.get(tag)
    if release.terminal:
        raise ReleaseError(f"Release {tag} is already {release.phase}.")
    if not reason.strip():
        raise ReleaseError("Record a reason for abandoning this release.")
    pull = github.api(f"pulls/{release.pr}") if release.pr else None
    if (pull and pull["merged"]) or (
        release.promotion and github.ref("heads/main") == release.promotion
    ):
        raise ReleaseError(
            f"Release {tag} already reached main. Use resume to record completion."
        )
    runs = workflow_runs(github, release)
    if any(run["status"] != "completed" for run in runs):
        raise ReleaseError(
            "Cancel the active Release run and wait for completion before abandoning it."
        )
    if pull and pull["state"] == "open":
        github.api(f"pulls/{release.pr}", "PATCH", {"state": "closed"})
    github.status(release.candidate, "failure", "Release abandoned by a maintainer")
    if release.promotion:
        github.status(release.promotion, "failure", "Release abandoned by a maintainer")
    release.phase = "abandoned"
    release.reason = reason.strip()
    journal.save(release)
    print(
        f"Abandoned {tag}. Tags and package files remain intact. Review any published files for explicit withdrawal."
    )


def status(github: GitHub) -> None:
    print(json.dumps(Journal(github).contents, indent=2, sort_keys=True))
