"""GitHub protection requirements and external request formats."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from release_github import GitHub, GitHubError
from release_state import ReleaseError


class RuleGitHub(GitHub):
    def __init__(self):
        super().__init__("example/toolkit")
        self.main = [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "dismiss_stale_reviews_on_push": True,
                    "allowed_merge_methods": ["merge"],
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": False,
                    "required_status_checks": [
                        {"context": "release/published", "integration_id": 123}
                    ],
                },
            },
        ]
        for rule in self.main:
            rule.update(
                {
                    "ruleset_source": self.repo,
                    "ruleset_source_type": "Repository",
                    "ruleset_id": 1,
                }
            )
        self.bypass = []

    def rules(self, branch):
        if branch == "main":
            return self.main
        return [
            {
                "type": kind,
                "ruleset_source": self.repo,
                "ruleset_source_type": "Repository",
                "ruleset_id": 1,
            }
            for kind in ("update", "deletion")
        ]

    def api(self, path, method="GET", payload=None):
        if path == "/apps/github-actions":
            return {"id": 123}
        return {"bypass_actors": self.bypass, "current_user_can_bypass": "never"}


def test_release_rules_allow_the_frozen_candidate_flow():
    github = RuleGitHub()
    github.require_main_gate()
    github.require_frozen_branch("release/v1.1.0")


@pytest.mark.parametrize(
    "change",
    ["missing", "wrong_app", "strict_additional_rule", "no_merge", "linear", "queue"],
)
def test_incompatible_main_rules_stop_before_publication(change):
    github = RuleGitHub()
    if change == "missing":
        github.main.pop()
    elif change == "wrong_app":
        github.main[1]["parameters"]["required_status_checks"][0]["integration_id"] = (
            456
        )
    elif change == "strict_additional_rule":
        strict = copy.deepcopy(github.main[1])
        strict["parameters"]["strict_required_status_checks_policy"] = True
        github.main.append(strict)
    elif change == "no_merge":
        github.main[0]["parameters"]["allowed_merge_methods"] = ["squash"]
    else:
        github.main.append(
            {"type": "required_linear_history" if change == "linear" else "merge_queue"}
        )
    with pytest.raises(ReleaseError):
        github.require_main_gate()


def test_candidate_rules_with_bypass_do_not_count_as_a_lock():
    github = RuleGitHub()
    github.bypass = [{"actor_id": 1}]
    with pytest.raises(ReleaseError, match="permits bypass"):
        github.require_frozen_branch("release/v1.1.0")


def test_main_gate_cannot_be_bypassed_by_the_release_actor():
    github = RuleGitHub()
    github.bypass = [{"actor_id": 1}]
    with pytest.raises(ReleaseError, match="without bypass"):
        github.require_main_gate()


def test_repository_lookup_and_cas_use_the_github_api_contract(monkeypatch):
    requests = []

    def respond(command, **kwargs):
        endpoint = command[2]
        payload = json.loads(kwargs["input"]) if kwargs.get("input") else None
        requests.append((endpoint, payload))
        if endpoint == "repos/example/toolkit":
            reply = {"node_id": "repository-id"}
        elif endpoint == "/graphql":
            reply = {"data": {"updateRefs": {"clientMutationId": None}}}
        else:
            pytest.fail(f"Invalid GitHub endpoint: {endpoint}")
        return subprocess.CompletedProcess(command, 0, json.dumps(reply), "")

    monkeypatch.setattr(subprocess, "run", respond)
    GitHub("example/toolkit").compare_and_update("main", "b" * 40, "c" * 40)
    update = requests[1][1]["variables"]["input"]["refUpdates"]
    assert update == [
        {
            "name": "refs/heads/main",
            "beforeOid": "b" * 40,
            "afterOid": "c" * 40,
            "force": False,
        }
    ]


def test_graphql_errors_stop_even_with_http_success(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, '{"errors":[{"message":"Protected branch"}]}', ""
        ),
    )
    with pytest.raises(GitHubError, match="Protected branch"):
        GitHub("example/toolkit").api("/graphql", "POST", {"query": "mutation"})
