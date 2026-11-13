"""Public package and installer checks."""

from __future__ import annotations

import re
import subprocess
import time

import bump_version
import smoke_entry_points
from release_state import ReleaseError

REPO_ROOT = bump_version.REPO_ROOT
INSTALL_SH = REPO_ROOT / "install.sh"
EXPECTED_WHEEL_STEMS = tuple(
    smoke_entry_points.wheel_stem(name)
    for name in sorted(smoke_entry_points.PUBLISHED_DISTRIBUTIONS)
)


def capture(command: list[str]) -> str:
    return subprocess.run(
        command, cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def pep440(version: str) -> str:
    from packaging.version import Version

    return str(Version(version))


def verify_github_wheels(tag: str) -> None:
    """Require one GitHub wheel for each published distribution."""
    names = capture(
        ["gh", "release", "view", tag, "--json", "assets", "--jq", ".assets[].name"]
    ).splitlines()
    wheels = [n for n in names if n.endswith(".whl")]
    missing = [
        stem
        for stem in EXPECTED_WHEEL_STEMS
        if not any(w.startswith(stem) for w in wheels)
    ]
    if missing:
        raise ReleaseError(
            f"Release {tag} is missing wheels for: {', '.join(missing)}. Got: {wheels}"
        )
    if len(wheels) != len(EXPECTED_WHEEL_STEMS):
        raise ReleaseError(
            f"Release {tag} has {len(wheels)} wheels, expected "
            f"{len(EXPECTED_WHEEL_STEMS)}: {wheels}"
        )
    print(f"GitHub Release {tag} ships all {len(wheels)} wheels.")


# PyPI metadata can lag behind a successful upload.
_PYPI_APPEAR_TIMEOUT_S = 120
_PYPI_POLL_INTERVAL_S = 10


def verify_pypi_install(version: str) -> None:
    """Retry PyPI installation during its propagation delay.

    ``--refresh`` prevents uv from reusing a cached lookup failure.
    """
    spec = f"pipefy-cli=={pep440(version)}"
    print(f"Verifying PyPI install of {spec} ...")
    deadline = time.monotonic() + _PYPI_APPEAR_TIMEOUT_S
    while True:
        try:
            out = capture(["uvx", "--refresh", "--from", spec, "pipefy", "--version"])
            break
        except subprocess.CalledProcessError:
            if time.monotonic() >= deadline:
                raise ReleaseError(
                    f"{spec} did not become installable from PyPI within "
                    f"{_PYPI_APPEAR_TIMEOUT_S}s (still propagating, or the upload "
                    f"failed). Re-run `release.py verify v{version}` once it lands."
                ) from None
            print(f"  not on PyPI yet; retrying in {_PYPI_POLL_INTERVAL_S}s...")
            time.sleep(_PYPI_POLL_INTERVAL_S)
    if pep440(version) not in pep440_candidates(out):
        raise ReleaseError(
            f"`pipefy --version` from PyPI returned {out!r}, expected {version}"
        )
    print(f"PyPI install resolves: {out}")


def pep440_candidates(text: str) -> set[str]:
    """Normalized versions found in a ``--version`` output line."""
    from packaging.version import InvalidVersion, Version

    found: set[str] = set()
    for token in re.findall(r"\d[\w.\-+]*", text):
        try:
            found.add(str(Version(token)))
        except InvalidVersion:
            continue
    return found


def _installer_dry_run() -> str:
    result = subprocess.run(
        [
            "sh",
            str(INSTALL_SH),
            "--yes",
            "--no-skills",
            "--client",
            "none",
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode:
        raise ReleaseError(
            f"install.sh dry-run failed with exit code {result.returncode}. Output:\n{output}"
        )
    return output


def verify_installer_resolves(tag: str) -> None:
    """Require the default installer to select the requested tag."""
    print("Verifying install.sh resolves the latest release ...")
    output = _installer_dry_run()
    expected = f"Resolved tag: {tag}"
    if expected not in output:
        raise ReleaseError(
            f"install.sh dry-run did not report '{expected}'. Output:\n{output}"
        )
    print(f"install.sh resolves {tag}.")


def verify_installer_skips(tag: str) -> None:
    """Require the default installer to select a release outside the alpha channel."""
    print(f"Verifying install.sh skips the staging alpha {tag} ...")
    output = _installer_dry_run()
    if f"Resolved tag: {tag}" in output:
        raise ReleaseError(
            f"install.sh dry-run resolved the staging alpha {tag}; it must stay "
            f"on the newest non-alpha release. Output:\n{output}"
        )
    m = re.search(r"Resolved tag: (\S+)", output)
    if not m:
        raise ReleaseError(
            f"install.sh dry-run reported no resolved tag at all. Output:\n{output}"
        )
    resolved = m.group(1)
    from packaging.version import InvalidVersion

    try:
        track = bump_version.prerelease_track(version_from_tag(resolved))
    except InvalidVersion:
        raise ReleaseError(
            f"install.sh resolved {resolved!r}, which is not a version tag; "
            f"cannot confirm it is not an alpha. Output:\n{output}"
        ) from None
    if track == "alpha":
        raise ReleaseError(
            f"install.sh resolved {resolved}, which is also an alpha; the "
            f"installer must land on a non-alpha release. Output:\n{output}"
        )
    print(f"install.sh stays on {resolved}.")


def print_release_links(tag: str, version: str) -> None:
    """Derive links from the checkout's remote and workspace members."""
    repo_url = capture(["gh", "repo", "view", "--json", "url", "--jq", ".url"])
    pep = pep440(version)
    print("\nLinks:")
    print(f"  GitHub Release: {repo_url}/releases/tag/{tag}")
    for dist in sorted(bump_version.workspace_members()):
        print(f"  PyPI {dist}: https://pypi.org/project/{dist}/{pep}/")


def version_from_tag(tag: str) -> str:
    """Remove a leading ``v`` without changing the version spelling."""
    return tag[1:] if tag.startswith("v") else tag


def verify(tag: str) -> None:
    """Require package availability and installer selection for the release track.

    The default installer must select beta and stable tags and exclude alphas.
    Stop at the first failure.
    """
    version = version_from_tag(tag)
    verify_github_wheels(tag)
    verify_pypi_install(version)
    if bump_version.prerelease_track(version) == "alpha":
        verify_installer_skips(tag)
    else:
        verify_installer_resolves(tag)
    print(f"\nAll checks passed for {tag}.")
