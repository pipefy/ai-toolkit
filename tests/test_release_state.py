"""Release recovery contracts without network access."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from release_state import Release, ReleaseError, missing_uploads, promotion_commit


def candidate(**overrides):
    return Release(
        **{
            "tag": "v1.0.0",
            "candidate": "a" * 40,
            "expected_main": "b" * 40,
            "previous_source": "c" * 40,
            "kind": "normal",
            **overrides,
        }
    )


def test_partial_upload_retries_only_original_missing_files():
    manifest = {"one.whl": "a" * 64, "two.whl": "b" * 64}
    assert missing_uploads(manifest, {"one.whl": "a" * 64}) == ["two.whl"]
    assert missing_uploads(manifest, manifest) == []


@pytest.mark.parametrize("uploaded", [{"one.whl": "b" * 64}, {"other.whl": "a" * 64}])
def test_mismatched_or_unexpected_upload_stops_recovery(uploaded):
    with pytest.raises(ReleaseError):
        missing_uploads({"one.whl": "a" * 64}, uploaded)


def test_promotion_requires_exact_parents_and_candidate_tree():
    release = candidate()
    commit = {
        "sha": "d" * 40,
        "tree": {"sha": "e" * 40},
        "parents": [{"sha": "b" * 40}, {"sha": "a" * 40}],
    }
    assert promotion_commit(release, commit, "e" * 40) == "d" * 40
    with pytest.raises(ReleaseError, match="tree"):
        promotion_commit(release, commit, "f" * 40)
    commit["parents"][0]["sha"] = "f" * 40
    with pytest.raises(ReleaseError, match="parents"):
        promotion_commit(release, commit, "e" * 40)


def test_state_roundtrip_retains_recovery_identity():
    release = candidate(manifest={"one.whl": "a" * 64}, build_started=True)
    assert Release.from_json(release.to_json()) == release


@pytest.mark.parametrize(
    "overrides",
    [
        {"candidate": "dev"},
        {"tag": "v1/../../secret"},
        {"kind": "unknown"},
        {"manifest": {"../one.whl": "a" * 64}},
    ],
)
def test_untrusted_state_rejects_invalid_identity(overrides):
    with pytest.raises(ReleaseError):
        candidate(**overrides)
