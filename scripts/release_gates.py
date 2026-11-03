"""Release gates shared by the maintainer command and Actions."""

from __future__ import annotations

import fnmatch
import re
import tomllib
from typing import Any
from urllib.parse import quote

import yaml
from packaging.version import Version
from release_github import PUBLISHED_CHECK, GitHub, Journal, rule_blocks_current_actor
from release_state import RELEASE_PROTOCOL, Release, ReleaseError, promotion_commit


def require_release_protocol(workflow: str) -> None:
    configuration = yaml.safe_load(workflow)
    commands = {
        step.get("run", "").strip()
        for step in configuration.get("jobs", {}).get("release", {}).get("steps", [])
    }
    expected = {
        f"uv run python scripts/release_pipeline.py {step}"
        for step in ("stage", "guard", "complete")
    }
    if (
        configuration.get("env", {}).get("RELEASE_PROTOCOL") != RELEASE_PROTOCOL
        or not expected <= commands
    ):
        raise ReleaseError(
            "The candidate lacks the supported promotion workflow. Include the release tooling before selecting this commit."
        )


def version_at(github: GitHub, sha: str) -> str:
    return tomllib.loads(github.text_at("pyproject.toml", sha))["project"]["version"]


def release_notes(changelog: str, version: str) -> str:
    heading = (
        "Unreleased"
        if Version(version).pre and Version(version).pre[0] == "a"
        else version
    )
    match = re.search(
        rf"(?ms)^## \[{re.escape(heading)}\][^\n]*\n(.*?)(?=^## \[|\Z)", changelog
    )
    if not match or not match[1].strip():
        raise ReleaseError(f"Release notes are empty or missing for {heading!r}.")
    return match[0].strip() + "\n"


def require_tag_rules(github: GitHub, tag: str) -> None:
    protected: set[str] = set()
    for summary in github.pages("rulesets?includes_parents=true"):
        if summary["target"] != "tag" or summary["enforcement"] != "active":
            continue
        source = summary["source"]
        prefix = (
            f"/repos/{source}"
            if summary["source_type"] == "Repository"
            else f"/orgs/{source}"
        )
        rule = github.api(f"{prefix}/rulesets/{summary['id']}")
        conditions = rule["conditions"]["ref_name"]
        ref = f"refs/tags/{tag}"
        includes = any(
            pattern == "~ALL" or fnmatch.fnmatchcase(ref, pattern)
            for pattern in conditions["include"]
        )
        excludes = any(
            pattern == "~ALL" or fnmatch.fnmatchcase(ref, pattern)
            for pattern in conditions["exclude"]
        )
        if includes and not excludes and rule_blocks_current_actor(rule):
            protected.update(item["type"] for item in rule["rules"])
    if not {"update", "deletion"} <= protected:
        raise ReleaseError(
            f"Protect {tag!r} against updates and deletion without bypass actors before publication."
        )


def require_configuration(github: GitHub, release: Release) -> None:
    github.require_frozen_branch(release.branch)
    require_tag_rules(github, release.tag)
    if release.kind != "alpha":
        github.require_main_gate()


def select_candidate(github: GitHub, sha: str, *, hotfix: bool = False) -> Release:
    main = github.ref("heads/main")
    previous_version = version_at(github, main)
    previous = github.ref(f"tags/v{previous_version}")
    if github.tree(previous) != github.tree(main):
        raise ReleaseError(
            "main differs from its published source. Reconcile it before selecting a candidate."
        )
    if not github.ancestor(previous, sha):
        raise ReleaseError(
            "The candidate omits previous release history. Merge the correction branch into dev first."
        )
    if not hotfix and not github.ancestor(sha, github.ref("heads/dev")):
        raise ReleaseError(
            "A normal candidate must belong to dev. Use --hotfix only for an urgent correction."
        )
    version = version_at(github, sha)
    if Version(version) <= Version(previous_version):
        raise ReleaseError(
            f"Candidate {version} must be newer than main version {previous_version}."
        )
    require_release_protocol(github.text_at(".github/workflows/release.yml", sha))
    kind = (
        "alpha"
        if Version(version).pre and Version(version).pre[0] == "a"
        else "hotfix"
        if hotfix
        else "normal"
    )
    if hotfix and kind == "alpha":
        raise ReleaseError("An alpha cannot promote an urgent correction to main.")
    changelog = github.text_at("CHANGELOG.md", sha)
    release_notes(changelog, version)
    previous_notes = release_notes(
        github.text_at("CHANGELOG.md", previous), previous_version
    )
    try:
        retained_notes = release_notes(changelog, previous_version)
    except ReleaseError as exc:
        raise ReleaseError(
            "The candidate must retain the previous release notes."
        ) from exc
    if retained_notes != previous_notes:
        raise ReleaseError(
            "The candidate changed the previous release notes. Preserve that published section."
        )
    release = Release(f"v{version}", sha, main, previous, kind)
    require_configuration(github, release)
    if github.optional(f"git/ref/tags/{release.tag}"):
        raise ReleaseError(
            f"Tag {release.tag} already exists. Use resume for a recorded release."
        )
    return release


def require_review(github: GitHub, release: Release) -> None:
    if release.kind == "alpha":
        return
    if not release.pr:
        raise ReleaseError(
            f"Create the promotion PR with 'release.py resume {release.tag}'."
        )
    pull = github.pull(release.pr)
    identity = (
        pull["headRefOid"],
        pull["baseRefOid"],
        pull["baseRefName"],
        pull["headRepository"]["nameWithOwner"],
    )
    if identity != (release.candidate, release.expected_main, "main", github.repo):
        raise ReleaseError(
            "The promotion PR no longer has the recorded candidate and base."
        )
    if (
        pull["state"] != "OPEN"
        or pull["isDraft"]
        or pull["reviewDecision"] != "APPROVED"
    ):
        raise ReleaseError(
            f"PR #{release.pr} needs approval. Resume {release.tag} after review."
        )
    latest: dict[str, dict[str, Any]] = {}
    for review in github.pages(f"pulls/{release.pr}/reviews"):
        if review["state"] != "COMMENTED":
            latest[review["user"]["login"]] = review
    if not any(
        review["state"] == "APPROVED" and review["commit_id"] == release.candidate
        for review in latest.values()
    ):
        raise ReleaseError("No current approval identifies the exact candidate SHA.")


def require_candidate(github: GitHub, release: Release, *, tagged: bool = True) -> None:
    journal = Journal(github)
    if (
        journal.contents["active"] != release.tag
        or journal.get(release.tag).candidate != release.candidate
    ):
        raise ReleaseError(
            f"Release {release.tag} no longer owns the active release slot."
        )
    if github.ref(f"heads/{release.branch}") != release.candidate:
        raise ReleaseError("The candidate branch changed. Stop for review.")
    if tagged and github.ref(f"tags/{release.tag}") != release.candidate:
        raise ReleaseError("The release tag changed. Stop for review.")
    if github.ref("heads/main") != release.expected_main:
        raise ReleaseError("main changed after candidate selection. Stop for review.")
    require_configuration(github, release)
    require_review(github, release)
    query = f"actions/workflows/ci.yml/runs?event=push&branch={quote(release.branch, safe='')}&head_sha={release.candidate}&per_page=100"
    runs = github.api(query)["workflow_runs"]
    matching = [
        run
        for run in runs
        if run["head_sha"] == release.candidate
        and run["head_branch"] == release.branch
        and run["event"] == "push"
    ]
    if not matching or matching[0]["conclusion"] != "success":
        raise ReleaseError(
            f"CI for {release.branch} at {release.candidate} must succeed before publication."
        )


def prepare_promotion(github: GitHub, release: Release) -> str:
    pull = github.api(f"pulls/{release.pr}")
    if not pull.get("merge_commit_sha") or pull.get("mergeable") is not True:
        raise ReleaseError(
            "GitHub did not produce a mergeable promotion commit. Resume after its merge calculation finishes."
        )
    commit = github.api(f"git/commits/{pull['merge_commit_sha']}")
    return promotion_commit(release, commit, github.tree(release.candidate))


def finish_promotion(github: GitHub, journal: Journal, release: Release) -> None:
    if release.kind == "alpha":
        raise ReleaseError("Alphas do not promote main.")
    if release.phase != "published" or not release.promotion:
        raise ReleaseError(
            "Publication and public installation tests must finish before promotion."
        )
    commit = github.api(f"git/commits/{release.promotion}")
    promotion_commit(release, commit, github.tree(release.candidate))
    current = github.ref("heads/main")
    if current != release.promotion:
        require_candidate(github, release)
        if prepare_promotion(github, release) != release.promotion:
            raise ReleaseError("GitHub changed the promotion commit. Stop for review.")
        status = github.api(f"commits/{release.promotion}/status")
        if not any(
            item["context"] == PUBLISHED_CHECK and item["state"] == "success"
            for item in status["statuses"]
        ):
            raise ReleaseError(
                "The promotion commit lacks a successful publication status."
            )
        github.compare_and_update("main", release.expected_main, release.promotion)
    if github.ref("heads/main") != release.promotion:
        raise ReleaseError("main does not match the recorded promotion commit.")
    if not github.api(f"pulls/{release.pr}")["merged"]:
        raise ReleaseError(
            "GitHub did not mark the promotion PR merged. Resume after the PR state updates."
        )
    github.api(f"releases/{release.release_id}", "PATCH", {"make_latest": "true"})
    release.phase = "complete"
    journal.save(release)
