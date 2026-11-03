"""Preparation transforms and public installer selection."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import release as _release
import release_checks as _checks


@pytest.fixture(autouse=True)
def forbid_release_subprocess(monkeypatch):
    def reject(command, **kwargs):
        raise AssertionError(f"Unexpected subprocess: {command}")

    monkeypatch.setattr(_release, "run", reject)
    monkeypatch.setattr(_release, "capture", reject)
    monkeypatch.setattr(_checks, "capture", reject)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0.2.0-beta.1", "0.2.0b1"),
        ("0.2.0-alpha.3", "0.2.0a3"),
        ("1.0.0rc2", "1.0.0rc2"),
        ("1.2.3", "1.2.3"),
    ],
)
def test_pep440_normalizes(raw: str, expected: str) -> None:
    assert _checks.pep440(raw) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("pipefy, version 0.2.0b1", {"0.2.0b1"}),
        ("pipefy-cli 1.2.3", {"1.2.3"}),
        ("no version here", set()),
        ("0.2.0-beta.1 build", {"0.2.0b1"}),
    ],
)
def test_pep440_candidates(text: str, expected: set[str]) -> None:
    assert _checks.pep440_candidates(text) == expected


def test_unreleased_re_captures_heading_and_body() -> None:
    text = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n- a thing\n\n"
        "## [1.0.0] - 2026-01-01\n\n- old\n"
    )
    m = _release.UNRELEASED_RE.search(text)
    assert m is not None
    assert m.group(1).startswith("## [Unreleased]")
    assert "a thing" in m.group(2)
    assert "old" not in m.group(2)


def test_stamp_changelog_renames_and_reseeds(tmp_path: Path, monkeypatch) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n- new feature\n\n"
        "## [1.0.0] - 2026-01-01\n\n- old\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_release, "CHANGELOG", changelog)

    _release.stamp_changelog("2.0.0")
    out = changelog.read_text(encoding="utf-8")

    # A fresh empty Unreleased is re-seeded above the dated version section.
    assert "## [Unreleased]\n\n## [2.0.0] - " in out
    # The accumulated notes moved under the new version, not lost.
    idx_version = out.index("## [2.0.0]")
    assert "new feature" in out[idx_version:]
    # The prior release section is untouched.
    assert "## [1.0.0] - 2026-01-01" in out


def test_stamp_changelog_requires_unreleased(tmp_path: Path, monkeypatch) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [1.0.0] - 2026-01-01\n", encoding="utf-8")
    monkeypatch.setattr(_release, "CHANGELOG", changelog)

    with pytest.raises(_release.ReleaseError):
        _release.stamp_changelog("2.0.0")


def test_beta_bump_is_reachable_through_target_for() -> None:
    # The promotion the dev->main flow needs every cycle must be a named bump,
    # not a hand-typed version= string.
    assert _release.target_for("beta", "0.5.0-alpha.3") == "0.5.0-beta.1"


def test_verify_installer_skips_accepts_a_different_tag(monkeypatch) -> None:
    monkeypatch.setattr(
        _checks, "_installer_dry_run", lambda: "Resolved tag: v0.4.0-beta.2\n"
    )
    _checks.verify_installer_skips("v0.5.0-alpha.1")


def test_verify_installer_skips_rejects_the_alpha(monkeypatch) -> None:
    # The regression this guards: publishing an alpha repoints the public
    # one-line install at an untested staging build.
    monkeypatch.setattr(
        _checks, "_installer_dry_run", lambda: "Resolved tag: v0.5.0-alpha.1\n"
    )
    with pytest.raises(_checks.ReleaseError, match="resolved the staging alpha"):
        _checks.verify_installer_skips("v0.5.0-alpha.1")


def test_verify_installer_skips_rejects_no_resolution(monkeypatch) -> None:
    monkeypatch.setattr(_checks, "_installer_dry_run", lambda: "boom\n")
    with pytest.raises(_checks.ReleaseError, match="no resolved tag"):
        _checks.verify_installer_skips("v0.5.0-alpha.1")


@pytest.mark.parametrize("alpha", [False, True])
def test_installer_failure_after_resolution_blocks_publication(monkeypatch, alpha):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            1,
            "Resolved tag: v0.4.0\n",
            "error: Release v0.4.0 has no wheel assets\n",
        ),
    )
    check = (
        _checks.verify_installer_skips if alpha else _checks.verify_installer_resolves
    )
    with pytest.raises(_checks.ReleaseError, match="dry-run failed"):
        check("v0.5.0-alpha.1" if alpha else "v0.4.0")


def test_verify_installer_skips_rejects_an_older_alpha(monkeypatch) -> None:
    # A filter that skipped only the newest alpha would leave the installer on an
    # older staging cut -- the same leak, so the check must reject any alpha.
    monkeypatch.setattr(
        _checks, "_installer_dry_run", lambda: "Resolved tag: v0.3.0-alpha.1\n"
    )
    with pytest.raises(_checks.ReleaseError, match="which is also an alpha"):
        _checks.verify_installer_skips("v0.5.0-alpha.1")


def test_verify_installer_skips_rejects_an_unparseable_tag(monkeypatch) -> None:
    monkeypatch.setattr(
        _checks, "_installer_dry_run", lambda: "Resolved tag: nightly\n"
    )
    with pytest.raises(_checks.ReleaseError, match="not a version tag"):
        _checks.verify_installer_skips("v0.5.0-alpha.1")


@pytest.mark.parametrize(
    ("bump", "current"),
    [
        # An unpromotable track and an unparseable explicit version both come back
        # from bump_version as ValueError; the CLI must report them as release
        # errors, not tracebacks. `release-pr beta` on a beta line is the case
        # that actually happens.
        ("beta", "0.4.0-beta.2"),
        ("prerelease", "0.2.0-dev.1"),
        ("version=not-a-version", "0.4.0-beta.2"),
    ],
)
def test_target_for_reports_bump_rejections_as_release_errors(
    bump: str, current: str
) -> None:
    with pytest.raises(_release.ReleaseError):
        _release.target_for(bump, current)


def test_expected_wheel_stems_are_derived_from_the_published_members() -> None:
    # The wheel set every release must attach is derived, not typed out again:
    # adding a published member updates it with no edit here. The literals pin
    # the escaping -- a wheel filename replaces the dashes a name carries.
    assert set(_checks.EXPECTED_WHEEL_STEMS) == {
        "pipefy-",
        "pipefy_auth-",
        "pipefy_cli-",
        "pipefy_infra-",
        "pipefy_mcp_server-",
    }
    assert len(_checks.EXPECTED_WHEEL_STEMS) == len(
        _checks.smoke_entry_points.PUBLISHED_DISTRIBUTIONS
    )
