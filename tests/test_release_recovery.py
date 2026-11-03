"""Persistent release ownership, immutable bytes, and promotion recovery."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import release_artifacts
import release_checks
import release_pipeline
from release_artifacts import (
    file_hash,
    original_manifest,
    restore_originals,
    stage_missing,
    wait_for_pypi,
)
from release_commands import abandon
from release_gates import finish_promotion, prepare_promotion, require_candidate
from release_github import GitHubError, Journal
from release_state import ReleaseError
from release_support import FakeGitHub, candidate


@pytest.fixture
def github():
    return FakeGitHub()


def test_failed_release_retains_the_single_active_slot(github):
    Journal(github).save(candidate(build_started=True))
    with pytest.raises(ReleaseError, match="is active"):
        Journal(github).save(candidate(tag="v1.2.0"))
    assert Journal(github).contents["active"] == "v1.1.0"


def test_concurrent_release_starts_have_one_winner(github):
    first, second = Journal(github), Journal(github)
    first.save(candidate())
    with pytest.raises(GitHubError):
        second.save(candidate(tag="v1.2.0"))
    assert Journal(github).contents["active"] == "v1.1.0"


def test_stale_state_cannot_overwrite_new_progress(github):
    Journal(github).save(candidate())
    stale = Journal(github)
    Journal(github).save(candidate(build_started=True))
    with pytest.raises(GitHubError, match="fast-forward"):
        stale.save(candidate(phase="abandoned", reason="stale command"))
    assert github.recorded()["build_started"] is True


def test_manifest_cannot_change_after_sealing(github):
    Journal(github).save(candidate(manifest={"one.whl": "a" * 64}))
    with pytest.raises(ReleaseError, match="manifest cannot change"):
        Journal(github).save(candidate(manifest={"one.whl": "b" * 64}))


@pytest.mark.parametrize(
    "change", ["candidate", "tag", "base", "review", "review_sha", "ci"]
)
def test_changed_candidate_approval_or_base_blocks_progress(github, change):
    release = candidate()
    Journal(github).save(release)
    if change == "candidate":
        github.refs["heads/release/v1.1.0"] = "d" * 40
    elif change == "tag":
        github.refs["tags/v1.1.0"] = "d" * 40
    elif change == "base":
        github.refs["heads/main"] = "d" * 40
    elif change == "review":
        github.review = "REVIEW_REQUIRED"
    elif change == "review_sha":
        github.review_sha = "d" * 40
    else:
        github.ci = "failure"
    with pytest.raises(ReleaseError):
        require_candidate(github, release)
    assert not any(path.startswith("releases/") for path, _, _ in github.writes)


def test_partial_upload_uses_only_original_missing_wheels(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    for distribution in (
        "pipefy",
        "pipefy_auth",
        "pipefy_cli",
        "pipefy_infra",
        "pipefy_mcp_server",
    ):
        (original / f"{distribution}-1.1.0-py3-none-any.whl").write_bytes(
            distribution.encode()
        )
    manifest = original_manifest(original, "1.1.0")
    uploaded = dict(list(manifest.items())[:2])
    missing = stage_missing(
        candidate(manifest=manifest), original, tmp_path / "upload", uploaded
    )
    assert set(missing) == set(manifest) - set(uploaded)
    assert {file.name: file_hash(file) for file in (tmp_path / "upload").iterdir()} == {
        name: manifest[name] for name in missing
    }


def test_missing_original_files_stop_before_any_download(github, tmp_path):
    with pytest.raises(ReleaseError, match="Original build files are missing"):
        restore_originals(
            github, candidate(release_id=1, manifest={"one.whl": "a" * 64}), tmp_path
        )


def test_changed_original_hash_stops_recovery(github, tmp_path, monkeypatch):
    release = candidate(manifest={"one.whl": "a" * 64})
    github.releases[1]["assets"] = [{"id": 2, "name": "one.whl"}]

    def download(command, **kwargs):
        kwargs["stdout"].write(b"different original bytes")

    monkeypatch.setattr(release_pipeline.subprocess, "run", download)
    with pytest.raises(ReleaseError, match="different hash"):
        restore_originals(github, release, tmp_path)


def test_alpha_completion_does_not_advance_main(monkeypatch):
    release = candidate(tag="v1.2.0-alpha.1", kind="alpha", phase="publishing", pr=0)
    github = FakeGitHub(release.tag)
    Journal(github).save(release)
    checked_tags = []
    monkeypatch.setattr(release_pipeline, "public_install", lambda *args: None)
    monkeypatch.setattr(release_checks, "verify_installer_skips", checked_tags.append)
    release_pipeline.complete(github, Journal(github), release)
    assert checked_tags == [release.tag]
    assert github.refs["heads/main"] == release.expected_main
    assert Journal(github).contents["active"] is None
    assert github.recorded(release.tag)["phase"] == "complete"
    assert not github.statuses


def test_lost_original_build_does_not_rebuild(github, tmp_path, monkeypatch):
    release = candidate(release_id=1, build_started=True)
    Journal(github).save(release)
    monkeypatch.setattr(
        release_pipeline.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("rebuilt lost originals"),
    )
    with pytest.raises(ReleaseError, match="instead of rebuilding"):
        release_pipeline.build_or_restore(github, Journal(github), release, tmp_path)


def test_failed_installation_keeps_github_draft_and_main_unchanged(
    github, tmp_path, monkeypatch
):
    release = candidate(release_id=1, manifest={"one.whl": "a" * 64})
    Journal(github).save(release)
    monkeypatch.setenv("GITHUB_RUN_ID", "17")
    monkeypatch.setattr(release_pipeline, "build_or_restore", lambda *args: None)

    def fail_install(requirements):
        raise ReleaseError("packages do not start")

    monkeypatch.setattr(release_pipeline, "install_smoke", fail_install)
    with pytest.raises(ReleaseError, match="do not start"):
        release_pipeline.stage(github, Journal(github), release, tmp_path)
    assert github.releases[1]["draft"] is True
    assert github.refs["heads/main"] == "b" * 40


def test_promotion_retry_does_not_build_or_republish(github):
    release = candidate(phase="published", promotion="c" * 40)
    Journal(github).save(release)
    github.statuses[release.promotion] = "success"
    finish_promotion(github, Journal(github), release)
    assert github.refs["heads/main"] == release.promotion
    assert Journal(github).contents["active"] is None
    assert github.recorded()["phase"] == "complete"
    assert [
        payload for path, _, payload in github.writes if path.startswith("releases/")
    ] == [{"make_latest": "true"}]


def test_lost_promotion_response_recovers_the_already_merged_candidate(github):
    release = candidate(phase="published", promotion="c" * 40)
    Journal(github).save(release)
    github.statuses[release.promotion] = "success"
    github.fail_main_response = True
    with pytest.raises(GitHubError, match="Connection lost"):
        finish_promotion(github, Journal(github), release)
    assert github.recorded()["phase"] == "published"
    finish_promotion(github, Journal(github), Journal(github).get(release.tag))
    assert github.recorded()["phase"] == "complete"
    assert github.main_updates == 1


def test_latest_metadata_failure_keeps_completion_recoverable(github):
    release = candidate(phase="published", promotion="c" * 40)
    Journal(github).save(release)
    github.statuses[release.promotion] = "success"
    github.fail_latest_response = True
    with pytest.raises(GitHubError, match="Latest metadata"):
        finish_promotion(github, Journal(github), release)
    assert Journal(github).contents["active"] == release.tag
    finish_promotion(github, Journal(github), Journal(github).get(release.tag))
    assert github.releases[1]["make_latest"] == "true"
    assert github.recorded()["phase"] == "complete"
    assert github.main_updates == 1


@pytest.mark.parametrize(
    ("actions", "expected_author"),
    [
        (
            False,
            {"name": "Release maintainer", "email": "release@example.test"},
        ),
        (
            True,
            {
                "name": "github-actions[bot]",
                "email": "2+github-actions[bot]@users.noreply.github.com",
            },
        ),
    ],
    ids=["maintainer", "actions-bot"],
)
def test_journal_commits_sign_off_the_explicit_author(
    github, monkeypatch, actions, expected_author
):
    if actions:
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
    else:
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    Journal(github).save(candidate())
    commits = [payload for path, _, payload in github.writes if path == "git/commits"]
    assert commits
    for commit in commits:
        author = commit["author"]
        assert author == expected_author
        assert (
            f"Signed-off-by: {author['name']} <{author['email']}>" in commit["message"]
        )


@pytest.mark.parametrize("unexpected", ["a" * 40, "d" * 40])
def test_promotion_rejects_any_changed_main_even_candidate_ancestry(github, unexpected):
    release = candidate(phase="published", promotion="c" * 40)
    Journal(github).save(release)
    github.statuses[release.promotion] = "success"
    github.change_main_before_update = unexpected
    with pytest.raises(GitHubError, match="Expected old SHA"):
        finish_promotion(github, Journal(github), release)
    assert github.refs["heads/main"] == unexpected
    assert github.recorded()["phase"] == "published"


def test_abandon_waits_for_running_workflow(github):
    Journal(github).save(candidate())
    github.run_status = "in_progress"
    with pytest.raises(ReleaseError, match="wait for completion"):
        abandon(github, "v1.1.0", "candidate needs a correction")
    assert Journal(github).contents["active"] == "v1.1.0"


def test_abandon_preserves_files_and_consumes_the_version(github):
    Journal(github).save(candidate(release_id=1))
    abandon(github, "v1.1.0", "candidate needs a correction")
    assert Journal(github).contents["active"] is None
    assert github.recorded()["reason"] == "candidate needs a correction"
    assert github.refs["tags/v1.1.0"] == "a" * 40
    assert github.releases[1]["draft"] is True
    with pytest.raises(ReleaseError, match="already abandoned"):
        Journal(github).save(candidate())


def test_public_verification_waits_for_pypi_propagation(monkeypatch):
    manifest = {"one.whl": "a" * 64}
    inventories = iter([{}, {}, manifest])
    monkeypatch.setattr(
        release_artifacts, "pypi_inventory", lambda version: next(inventories)
    )
    ticks = iter(range(0, 1000, 10))
    slept = []
    wait_for_pypi(
        candidate(manifest=manifest), clock=lambda: next(ticks), sleep=slept.append
    )
    assert slept == [10, 10]


def test_pypi_propagation_timeout_stops_for_review(monkeypatch):
    monkeypatch.setattr(release_artifacts, "pypi_inventory", lambda version: {})
    ticks = iter([0, 200])
    with pytest.raises(ReleaseError, match="PyPI is incomplete"):
        wait_for_pypi(
            candidate(manifest={"one.whl": "a" * 64}),
            clock=lambda: next(ticks),
            sleep=lambda seconds: None,
        )


def test_mismatched_upload_never_waits_for_propagation(monkeypatch):
    monkeypatch.setattr(
        release_artifacts, "pypi_inventory", lambda version: {"one.whl": "b" * 64}
    )
    with pytest.raises(ReleaseError, match="differs from the original manifest"):
        wait_for_pypi(
            candidate(manifest={"one.whl": "a" * 64}),
            clock=lambda: 0,
            sleep=lambda seconds: pytest.fail("waited on a mismatch"),
        )


def test_promotion_waits_for_github_mergeability(github):
    github.mergeable = [None, None, True]
    ticks = iter(range(0, 100, 3))
    slept = []
    assert (
        prepare_promotion(
            github, candidate(), clock=lambda: next(ticks), sleep=slept.append
        )
        == "c" * 40
    )
    assert slept == [3, 3]
