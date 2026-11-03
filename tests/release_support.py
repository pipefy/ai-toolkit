"""GitHub fake for conditional release updates."""

from __future__ import annotations

import copy
import json

from release_github import PUBLISHED_CHECK, GitHub, GitHubError
from release_state import Release


def candidate(**overrides):
    return Release(
        **{
            "tag": "v1.1.0",
            "candidate": "a" * 40,
            "expected_main": "b" * 40,
            "previous_source": "b" * 40,
            "kind": "normal",
            "pr": 1,
            "release_id": 1,
            **overrides,
        }
    )


class FakeGitHub(GitHub):
    def __init__(self, tag="v1.1.0"):
        super().__init__("example/toolkit")
        self.tag = tag
        self.refs = {
            "heads/main": "b" * 40,
            f"heads/release/{self.tag}": "a" * 40,
            f"tags/{self.tag}": "a" * 40,
        }
        self.commits = {
            "b" * 40: {"sha": "b" * 40, "tree": {"sha": "e" * 40}, "parents": []},
            "a" * 40: {
                "sha": "a" * 40,
                "tree": {"sha": "f" * 40},
                "parents": [{"sha": "b" * 40}],
            },
            "c" * 40: {
                "sha": "c" * 40,
                "tree": {"sha": "f" * 40},
                "parents": [{"sha": "b" * 40}, {"sha": "a" * 40}],
            },
        }
        self.trees = {}
        self.counter = 10
        self.review = "APPROVED"
        self.review_sha = "a" * 40
        self.ci = "success"
        self.statuses = {}
        self.releases = {
            1: {"id": 1, "draft": True, "tag_name": self.tag, "assets": []}
        }
        self.run_status = "completed"
        self.writes = []
        self.fail_main_response = False
        self.change_main_before_update = ""
        self.main_updates = 0
        self.fail_latest_response = False
        self.mergeable = [True]

    def next_sha(self):
        self.counter += 1
        return f"{self.counter:040x}"

    def optional(self, path):
        if path.startswith("git/ref/"):
            sha = self.refs.get(path.removeprefix("git/ref/"))
            return {"object": {"sha": sha, "type": "commit"}} if sha else None
        raise AssertionError(path)

    def text_at(self, path, sha):
        assert path == "state.json"
        return self.trees[self.commits[sha]["tree"]["sha"]]

    def pages(self, path):
        if path.startswith("rulesets?"):
            return [
                {
                    "target": "tag",
                    "enforcement": "active",
                    "source": self.repo,
                    "source_type": "Repository",
                    "id": 1,
                }
            ]
        if path.endswith("/reviews"):
            return [
                {
                    "state": self.review,
                    "commit_id": self.review_sha,
                    "user": {"login": "reviewer"},
                }
            ]
        if path.endswith("/assets"):
            return copy.deepcopy(self.releases[int(path.split("/")[1])]["assets"])
        if path == "releases":
            return copy.deepcopy(list(self.releases.values()))
        raise AssertionError(path)

    def require_frozen_branch(self, branch):
        pass

    def require_main_gate(self):
        pass

    def pull(self, number):
        return {
            "state": "OPEN",
            "isDraft": False,
            "headRefOid": self.refs[f"heads/release/{self.tag}"],
            "baseRefOid": self.refs["heads/main"],
            "baseRefName": "main",
            "headRepository": {"nameWithOwner": self.repo},
            "reviewDecision": self.review,
        }

    def api(self, path, method="GET", payload=None):
        if method != "GET":
            self.writes.append((path, method, copy.deepcopy(payload)))
        if path == "":
            return {"node_id": "repository-id"}
        if path == "/user":
            return {
                "id": 1,
                "login": "maintainer",
                "name": "Release maintainer",
                "email": "release@example.test",
            }
        if path == "/users/github-actions%5Bbot%5D":
            return {
                "id": 2,
                "login": "github-actions[bot]",
                "name": None,
                "email": None,
            }
        if path == "/graphql":
            [update] = payload["variables"]["input"]["refUpdates"]
            ref = update["name"].removeprefix("refs/")
            assert update["force"] is False
            if ref == "heads/main" and self.change_main_before_update:
                self.refs[ref] = self.change_main_before_update
            if self.refs[ref] != update["beforeOid"]:
                raise GitHubError(
                    "Expected old SHA differs; refusing fast-forward", 422
                )
            self.refs[ref] = update["afterOid"]
            if ref == "heads/main":
                self.main_updates += 1
                if self.fail_main_response:
                    self.fail_main_response = False
                    raise GitHubError("Connection lost after promotion")
            return {"data": {"updateRefs": {"clientMutationId": None}}}
        if path == "git/trees":
            sha = self.next_sha()
            self.trees[sha] = payload["tree"][0]["content"]
            return {"sha": sha}
        if path == "git/commits":
            sha = self.next_sha()
            self.commits[sha] = {
                "sha": sha,
                "tree": {"sha": payload["tree"]},
                "parents": [{"sha": parent} for parent in payload["parents"]],
            }
            return {"sha": sha}
        if path == "git/refs":
            ref = payload["ref"].removeprefix("refs/")
            if ref in self.refs:
                raise GitHubError("Reference already exists", 422)
            self.refs[ref] = payload["sha"]
            return {}
        if path.startswith("git/ref/"):
            return self.optional(path)
        if path.startswith("git/commits/"):
            return copy.deepcopy(self.commits[path.split("/")[-1]])
        if path.startswith("/repos/") and "/rulesets/" in path:
            return {
                "conditions": {
                    "ref_name": {"include": ["refs/tags/v*"], "exclude": []}
                },
                "rules": [{"type": "update"}, {"type": "deletion"}],
                "bypass_actors": [],
                "current_user_can_bypass": "never",
            }
        if path.startswith("actions/workflows/ci.yml/runs"):
            return {
                "workflow_runs": [
                    {
                        "head_sha": "a" * 40,
                        "head_branch": f"release/{self.tag}",
                        "event": "push",
                        "conclusion": self.ci,
                    }
                ]
            }
        if path.startswith("actions/workflows/release.yml/runs"):
            return {
                "workflow_runs": [
                    {
                        "id": 17,
                        "head_branch": self.tag,
                        "head_sha": "a" * 40,
                        "event": "push",
                        "status": self.run_status,
                        "conclusion": "failure",
                    }
                ]
            }
        if path.startswith("statuses/"):
            self.statuses[path.split("/")[-1]] = payload["state"]
            return {}
        if path.startswith("commits/") and path.endswith("/status"):
            return {
                "statuses": [
                    {
                        "context": PUBLISHED_CHECK,
                        "state": self.statuses.get(path.split("/")[1], "pending"),
                    }
                ]
            }
        if path == "pulls/1":
            mergeable = (
                self.mergeable.pop(0) if len(self.mergeable) > 1 else self.mergeable[0]
            )
            return {
                "merge_commit_sha": "c" * 40,
                "mergeable": mergeable,
                "merged": self.refs["heads/main"] == "c" * 40,
            }
        if path.startswith("releases/"):
            release = self.releases[int(path.split("/")[1])]
            if (
                payload
                and payload.get("make_latest") == "true"
                and self.fail_latest_response
            ):
                self.fail_latest_response = False
                raise GitHubError("Latest metadata failed")
            if payload:
                release.update(payload)
            return copy.deepcopy(release)
        raise AssertionError((path, method, payload))

    def recorded(self, tag="v1.1.0"):
        sha = self.refs["heads/release-ledger"]
        return json.loads(self.text_at("state.json", sha))["releases"][tag]
