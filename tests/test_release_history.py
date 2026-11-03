"""Real Git histories for freezes, consecutive releases, and hotfix integration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from release_gates import select_candidate
from release_state import ReleaseError


class Repository:
    repo = "example/toolkit"

    def __init__(self, root):
        self.root = root
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Release test")
        self.git("config", "user.email", "release@example.test")
        workflow = root / ".github/workflows/release.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(
            'env: {RELEASE_PROTOCOL: "1"}\njobs:\n  release:\n    steps:\n'
            + "".join(
                f"      - run: uv run python scripts/release_pipeline.py {step}\n"
                for step in ("stage", "guard", "complete")
            )
        )
        self.git("add", ".github/workflows/release.yml")
        self.commit("1.0.0", "initial")
        self.git("tag", "v1.0.0")
        self.git("switch", "-c", "dev")

    def git(self, *args, check=True):
        return subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=check
        ).stdout.strip()

    def commit(self, version, note):
        (self.root / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
        changelog = self.root / "CHANGELOG.md"
        prior = changelog.read_text() if changelog.exists() else ""
        changelog.write_text(f"## [{version}]\n\n- {note}\n\n{prior}")
        self.git("add", "pyproject.toml", "CHANGELOG.md")
        self.git("commit", "-qm", note)
        return self.git("rev-parse", "HEAD")

    def ref(self, ref):
        return self.git("rev-parse", f"refs/{ref}^{{commit}}")

    def text_at(self, path, sha):
        return self.git("show", f"{sha}:{path}")

    def tree(self, sha):
        return self.git("rev-parse", f"{sha}^{{tree}}")

    def ancestor(self, older, newer):
        return (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", older, newer],
                cwd=self.root,
                check=False,
            ).returncode
            == 0
        )

    def require_frozen_branch(self, branch):
        pass

    def require_main_gate(self):
        pass

    def pages(self, path):
        return [
            {
                "target": "tag",
                "enforcement": "active",
                "source": self.repo,
                "source_type": "Repository",
                "id": 1,
            }
        ]

    def api(self, path):
        return {
            "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
            "rules": [{"type": "update"}, {"type": "deletion"}],
            "bypass_actors": [],
            "current_user_can_bypass": "never",
        }

    def optional(self, path):
        ref = path.removeprefix("git/ref/")
        found = self.git("show-ref", "--verify", f"refs/{ref}", check=False)
        return {"object": {"sha": found.split()[0]}} if found else None

    def promote(self, candidate, version):
        self.git("tag", f"v{version}", candidate)
        self.git("switch", "main")
        self.git("merge", "--no-ff", candidate, "-m", f"Promote {version}")
        return self.git("rev-parse", "HEAD")


def test_two_consecutive_releases_preserve_source_without_backmerge(tmp_path):
    repo = Repository(tmp_path)
    first = repo.commit("1.1.0", "first")
    release = select_candidate(repo, first)
    repo.git("branch", release.branch, first)
    second = repo.commit("1.2.0", "later work")
    assert repo.ref(f"heads/{release.branch}") == first
    merge = repo.promote(first, "1.1.0")
    assert not repo.ancestor(merge, second)
    next_release = select_candidate(repo, second)
    assert next_release.previous_source == first
    assert next_release.expected_main == merge
    repo.promote(second, "1.2.0")
    assert repo.tree(repo.ref("heads/main")) == repo.tree(second)


def test_source_changes_only_on_main_stop_the_next_release(tmp_path):
    repo = Repository(tmp_path)
    candidate = repo.commit("1.1.0", "candidate")
    repo.git("switch", "main")
    (tmp_path / "unexpected.txt").write_text("unpublished source")
    repo.git("add", "unexpected.txt")
    repo.git("commit", "-qm", "unexpected main change")
    with pytest.raises(ReleaseError, match="differs from its published source"):
        select_candidate(repo, candidate)


def test_candidate_with_legacy_workflow_cannot_start_an_alpha(tmp_path):
    repo = Repository(tmp_path)
    repo.commit("1.1.0-alpha.1", "alpha")
    (tmp_path / ".github/workflows/release.yml").write_text("name: Legacy release\n")
    repo.git("add", ".github/workflows/release.yml")
    repo.git("commit", "-qm", "Restore legacy workflow")
    with pytest.raises(ReleaseError, match="supported promotion workflow"):
        select_candidate(repo, repo.ref("heads/dev"))


def test_hotfix_must_reach_dev_by_history_before_next_normal_release(tmp_path):
    repo = Repository(tmp_path)
    development = repo.commit("1.1.0", "unfinished development")
    repo.git("switch", "-c", "hotfix", "v1.0.0")
    correction = repo.commit("1.0.1", "urgent correction")
    assert select_candidate(repo, correction, hotfix=True).kind == "hotfix"
    repo.promote(correction, "1.0.1")
    with pytest.raises(ReleaseError, match="omits previous release history"):
        select_candidate(repo, development)
    repo.git("switch", "dev")
    repo.git("merge", "--no-ff", "--no-commit", correction, check=False)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.1.0"\n')
    (tmp_path / "CHANGELOG.md").write_text(
        "## [1.1.0]\n\n- unfinished development\n\n"
        + repo.text_at("CHANGELOG.md", correction)
    )
    repo.git("add", "pyproject.toml", "CHANGELOG.md")
    repo.git("commit", "-qm", "Integrate correction and retain development version")
    selected = select_candidate(repo, repo.ref("heads/dev"))
    assert selected.previous_source == correction
    assert selected.version == "1.1.0"


def test_merge_cannot_discard_the_previous_release_notes(tmp_path):
    repo = Repository(tmp_path)
    repo.commit("1.1.0", "candidate")
    (tmp_path / "CHANGELOG.md").write_text("## [1.1.0]\n\n- candidate\n")
    repo.git("add", "CHANGELOG.md")
    repo.git("commit", "-qm", "Discard previous release notes")
    with pytest.raises(ReleaseError, match="previous release notes"):
        select_candidate(repo, repo.ref("heads/dev"))


def test_fast_forward_rejects_a_concurrent_main_change(tmp_path):
    repo = Repository(tmp_path)
    candidate = repo.commit("1.1.0", "candidate")
    expected_main = repo.ref("heads/main")
    merge = repo.promote(candidate, "1.1.0")
    repo.git("branch", "target", expected_main)
    repo.git("push", ".", f"{merge}:refs/heads/target")
    assert repo.ref("heads/target") == merge
    repo.git("update-ref", "refs/heads/main", expected_main)
    repo.git("reset", "--hard", expected_main)
    concurrent = repo.commit("1.0.1", "concurrent change")
    repo.git("update-ref", "refs/heads/target", concurrent)
    result = subprocess.run(
        ["git", "push", ".", f"{merge}:refs/heads/target"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert repo.ref("heads/target") == concurrent
