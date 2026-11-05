"""GitHub transport and an append-only release journal."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from functools import cached_property
from typing import Any
from urllib.parse import quote

from release_state import Release, ReleaseError

LEDGER_BRANCH = "release-ledger"
PUBLISHED_CHECK = "release/published"


def rule_blocks_current_actor(rule: dict[str, Any]) -> bool:
    """Reject known bypass actors and require a restriction on the current caller."""
    return rule.get("current_user_can_bypass") == "never" and not rule.get(
        "bypass_actors"
    )


class GitHubError(ReleaseError):
    """A GitHub request failed or returned an error."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


class GitHub:
    """Use the current gh authentication without exposing its credentials."""

    def __init__(self, repo: str) -> None:
        self.repo = repo

    @cached_property
    def author(self) -> dict[str, str]:
        profile = self.api(
            "/users/github-actions%5Bbot%5D"
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else "/user"
        )
        return {
            "name": profile.get("name") or profile["login"],
            "email": profile.get("email")
            or f"{profile['id']}+{profile['login']}@users.noreply.github.com",
        }

    def api(self, path: str, method: str = "GET", payload: Any = None) -> Any:
        endpoint = (
            path if path.startswith("/") else f"repos/{self.repo}/{path}".rstrip("/")
        )
        command = ["gh", "api", endpoint, "--method", method]
        if payload is not None:
            command += ["--input", "-"]
        result = subprocess.run(
            command,
            input=json.dumps(payload) if payload is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            match = re.search(r"HTTP (\d+)", result.stderr)
            raise GitHubError(result.stderr.strip(), int(match[1]) if match else 0)
        value = json.loads(result.stdout) if result.stdout.strip() else None
        if isinstance(value, dict) and value.get("errors"):
            raise GitHubError("; ".join(error["message"] for error in value["errors"]))
        return value

    def optional(self, path: str) -> Any:
        try:
            return self.api(path)
        except GitHubError as exc:
            if exc.status != 404:
                raise
            return None

    def pages(self, path: str) -> list[Any]:
        values: list[Any] = []
        separator = "&" if "?" in path else "?"
        for page in range(1, 1001):
            batch = self.api(f"{path}{separator}per_page=100&page={page}")
            values.extend(batch)
            if len(batch) < 100:
                return values
        raise ReleaseError(f"Pagination limit reached for {path!r}")

    def ref(self, ref: str) -> str:
        value = self.api(f"git/ref/{ref}")["object"]
        while value["type"] == "tag":
            value = self.api(f"git/tags/{value['sha']}")["object"]
        if value["type"] != "commit":
            raise ReleaseError(f"Reference {ref!r} does not identify a commit.")
        return value["sha"]

    def text_at(self, path: str, sha: str) -> str:
        value = self.api(f"contents/{path}?ref={sha}")
        return base64.b64decode(value["content"]).decode()

    def tree(self, sha: str) -> str:
        return self.api(f"git/commits/{sha}")["tree"]["sha"]

    def ancestor(self, older: str, newer: str) -> bool:
        return self.api(f"compare/{older}...{newer}")["status"] in {
            "ahead",
            "identical",
        }

    def compare_and_update(self, branch: str, before: str, after: str) -> None:
        repository_id = self.api("")["node_id"]
        query = """mutation($input:UpdateRefsInput!) {
          updateRefs(input:$input) { clientMutationId }
        }"""
        self.api(
            "/graphql",
            "POST",
            {
                "query": query,
                "variables": {
                    "input": {
                        "repositoryId": repository_id,
                        "refUpdates": [
                            {
                                "name": f"refs/heads/{branch}",
                                "beforeOid": before,
                                "afterOid": after,
                                "force": False,
                            }
                        ],
                    }
                },
            },
        )

    def status(self, sha: str, state: str, description: str) -> None:
        self.api(
            f"statuses/{sha}",
            "POST",
            {"state": state, "context": PUBLISHED_CHECK, "description": description},
        )

    def pull(self, number: int) -> dict[str, Any]:
        owner, name = self.repo.split("/")
        query = """query($owner:String!, $name:String!, $number:Int!) {
          repository(owner:$owner, name:$name) { pullRequest(number:$number) {
            state isDraft headRefOid baseRefOid baseRefName reviewDecision
            headRepository { nameWithOwner }
          } }
        }"""
        return self.api(
            "/graphql",
            "POST",
            {
                "query": query,
                "variables": {"owner": owner, "name": name, "number": number},
            },
        )["data"]["repository"]["pullRequest"]

    def rules(self, branch: str) -> list[dict[str, Any]]:
        return self.pages(f"rules/branches/{quote(branch, safe='')}")

    def rule_detail(self, rule: dict[str, Any]) -> dict[str, Any]:
        source = rule["ruleset_source"]
        prefix = (
            f"/repos/{source}"
            if rule["ruleset_source_type"] == "Repository"
            else f"/orgs/{source}"
        )
        return self.api(f"{prefix}/rulesets/{rule['ruleset_id']}")

    def require_frozen_branch(self, branch: str) -> None:
        rules = self.rules(branch)
        for kind in ("update", "deletion"):
            matching = [rule for rule in rules if rule["type"] == kind]
            if not matching:
                raise ReleaseError(
                    f"Configure a {kind!r} rule without bypass actors for {branch!r}."
                )
            for rule in matching:
                if rule_blocks_current_actor(self.rule_detail(rule)):
                    break
            else:
                raise ReleaseError(
                    f"The {kind!r} rule for {branch!r} permits bypass or hides the caller's bypass state. Review its configuration."
                )

    def require_main_gate(self) -> None:
        rules = self.rules("main")
        kinds = {rule["type"] for rule in rules}
        if kinds & {"required_linear_history", "merge_queue"}:
            raise ReleaseError(
                "Promotion requires merge commits without a merge queue on main."
            )
        reviews = [rule for rule in rules if rule["type"] == "pull_request"]
        if any(
            "merge" not in rule["parameters"].get("allowed_merge_methods", ["merge"])
            for rule in reviews
        ):
            raise ReleaseError(
                "Permit merge commits in every pull request rule on main."
            )
        if not any(
            rule["parameters"]["required_approving_review_count"] >= 1
            and rule["parameters"]["dismiss_stale_reviews_on_push"]
            and rule_blocks_current_actor(self.rule_detail(rule))
            for rule in reviews
        ):
            raise ReleaseError(
                "Require an approving review and dismiss stale reviews on main without bypass permission."
            )
        app_id = self.api("/apps/github-actions")["id"]
        publication_required = False
        for rule in rules:
            if rule["type"] != "required_status_checks":
                continue
            parameters = rule["parameters"]
            if parameters["strict_required_status_checks_policy"]:
                raise ReleaseError(
                    "Disable strict status checks on main. The candidate must remain frozen."
                )
            if any(
                check["context"] == PUBLISHED_CHECK
                and check.get("integration_id") == app_id
                for check in parameters["required_status_checks"]
            ):
                publication_required |= rule_blocks_current_actor(
                    self.rule_detail(rule)
                )
        if not publication_required:
            raise ReleaseError(
                f"Require {PUBLISHED_CHECK!r} from GitHub Actions on main before publication."
            )


class Journal:
    """Serialize releases through updates that require the exact previous state."""

    def __init__(self, github: GitHub) -> None:
        self.github = github
        ref = github.optional(f"git/ref/heads/{LEDGER_BRANCH}")
        self.sha = ref["object"]["sha"] if ref else ""
        self.contents = (
            json.loads(github.text_at("state.json", self.sha))
            if self.sha
            else {"schema": 1, "active": None, "releases": {}}
        )
        if self.contents.get("schema") != 1:
            raise ReleaseError("Unsupported release journal schema. Stop for review.")

    def get(self, tag: str) -> Release:
        if tag not in self.contents["releases"]:
            raise ReleaseError(f"No recorded release for {tag!r}.")
        return Release.from_json(self.contents["releases"][tag])

    def save(self, release: Release) -> None:
        active = self.contents["active"]
        if active and active != release.tag:
            raise ReleaseError(
                f"Release {active} is active. Recover or abandon it first."
            )
        old = self.contents["releases"].get(release.tag)
        if old:
            identity = ("candidate", "expected_main", "previous_source", "kind", "tag")
            if any(old[key] != getattr(release, key) for key in identity):
                raise ReleaseError(
                    "The release identity cannot change. Select a new version."
                )
            if old["manifest"] and old["manifest"] != release.manifest:
                raise ReleaseError("The original artifact manifest cannot change.")
            if old["phase"] in {"complete", "abandoned"} and old != release.to_json():
                raise ReleaseError(f"Release {release.tag} is already {old['phase']}.")
        self.contents["active"] = None if release.terminal else release.tag
        self.contents["releases"][release.tag] = release.to_json()
        tree = self.github.api(
            "git/trees",
            "POST",
            {
                "tree": [
                    {
                        "path": "state.json",
                        "mode": "100644",
                        "type": "blob",
                        "content": json.dumps(self.contents, sort_keys=True, indent=2)
                        + "\n",
                    }
                ]
            },
        )
        commit = self.github.api(
            "git/commits",
            "POST",
            {
                "message": f"chore: record {release.tag} {release.phase}\n\nSigned-off-by: {self.github.author['name']} <{self.github.author['email']}>",
                "author": self.github.author,
                "tree": tree["sha"],
                "parents": [self.sha] if self.sha else [],
            },
        )
        if self.sha:
            self.github.compare_and_update(LEDGER_BRANCH, self.sha, commit["sha"])
        else:
            self.github.api(
                "git/refs",
                "POST",
                {"ref": f"refs/heads/{LEDGER_BRANCH}", "sha": commit["sha"]},
            )
        self.sha = commit["sha"]
