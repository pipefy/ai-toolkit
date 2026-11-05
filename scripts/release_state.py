"""Persistent identity and recovery decisions for one release."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from packaging.version import InvalidVersion, Version

RELEASE_PROTOCOL = "1"


class ReleaseError(RuntimeError):
    """A release condition requires operator attention."""


@dataclass
class Release:
    """The fixed source and saved progress of a manually authorized release."""

    tag: str
    candidate: str
    expected_main: str
    previous_source: str
    kind: str
    pr: int = 0
    phase: str = "candidate"
    build_started: bool = False
    release_id: int = 0
    run_id: int = 0
    manifest: dict[str, str] = field(default_factory=dict)
    promotion: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if not re.fullmatch(r"v[0-9][0-9A-Za-z.\-]*", self.tag):
            raise ReleaseError(f"Invalid release tag: {self.tag!r}")
        try:
            version = Version(self.version)
        except InvalidVersion as exc:
            raise ReleaseError(f"Invalid release version: {self.version!r}") from exc
        for sha in (self.candidate, self.expected_main, self.previous_source):
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise ReleaseError(f"Expected a full commit SHA, received {sha!r}")
        if self.kind not in {"normal", "alpha", "hotfix"}:
            raise ReleaseError(f"Unknown release kind: {self.kind!r}")
        if (self.kind == "alpha") != bool(version.pre and version.pre[0] == "a"):
            raise ReleaseError(
                f"Release kind {self.kind!r} does not match version {self.version!r}."
            )
        if self.phase not in {
            "candidate",
            "built",
            "publishing",
            "published",
            "complete",
            "abandoned",
        }:
            raise ReleaseError(f"Unknown release phase: {self.phase!r}")
        for name, digest in self.manifest.items():
            if not re.fullmatch(r"[A-Za-z0-9_.+\-]+\.whl", name) or not re.fullmatch(
                r"[0-9a-f]{64}", digest
            ):
                raise ReleaseError(f"Invalid original artifact: {name!r}")

    @property
    def version(self) -> str:
        return self.tag[1:]

    @property
    def branch(self) -> str:
        return f"release/{self.tag}"

    @property
    def terminal(self) -> bool:
        return self.phase in {"complete", "abandoned"}

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> Release:
        try:
            return cls(**value)
        except (TypeError, ValueError, AttributeError) as exc:
            raise ReleaseError(
                "Invalid release state. Restore the recorded state before recovery."
            ) from exc


def missing_uploads(original: dict[str, str], uploaded: dict[str, str]) -> list[str]:
    """Return absent files only when every existing upload matches its original."""
    for name, digest in uploaded.items():
        if original.get(name) != digest:
            raise ReleaseError(
                f"Upload {name!r} differs from the original manifest. Stop for review."
            )
    return sorted(original.keys() - uploaded.keys())


def promotion_commit(
    release: Release, commit: dict[str, Any], candidate_tree: str
) -> str:
    """Accept GitHub's merge commit only for the recorded base and candidate."""
    parents = [parent["sha"] for parent in commit["parents"]]
    if parents != [release.expected_main, release.candidate]:
        raise ReleaseError(f"Promotion parents changed: {parents!r}")
    if commit["tree"]["sha"] != candidate_tree:
        raise ReleaseError("Promotion tree differs from the published candidate.")
    return commit["sha"]
