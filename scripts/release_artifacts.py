"""Original package storage and publication inventory."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import smoke_entry_points
from packaging.utils import parse_wheel_filename
from packaging.version import Version
from release_github import GitHub
from release_state import Release, ReleaseError, missing_uploads

# PyPI serves its JSON and simple indexes through a CDN that can lag a
# successful upload. Hash mismatches never wait; only absence does.
PYPI_PROPAGATION_TIMEOUT_S = 120
PYPI_POLL_INTERVAL_S = 10


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_manifest(directory: Path, version: str) -> dict[str, str]:
    wheels = smoke_entry_points.check_wheels(directory)
    for name in wheels:
        if parse_wheel_filename(name)[1] != Version(version):
            raise ReleaseError(f"Wheel {name!r} does not contain version {version!r}.")
    return {name: file_hash(directory / name) for name in sorted(wheels)}


def install_smoke(requirements: list[str]) -> None:
    """Install all packages in an empty environment and exercise installed entry points."""
    with tempfile.TemporaryDirectory(prefix="release-install-") as temporary:
        environment = Path(temporary) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        python = (
            environment / ("Scripts" if sys.platform == "win32" else "bin") / "python"
        )
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-cache-dir", *requirements],
            check=True,
        )
        subprocess.run(
            [str(python), str(Path(smoke_entry_points.__file__).resolve())], check=True
        )


def restore_originals(github: GitHub, release: Release, directory: Path) -> None:
    assets = github.pages(f"releases/{release.release_id}/assets")
    if {asset["name"] for asset in assets} != set(release.manifest) or len(
        assets
    ) != len(release.manifest):
        raise ReleaseError(
            "Original build files are missing or unexpected. Stop for review. Do not rebuild this version."
        )
    directory.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        path = directory / asset["name"]
        with path.open("wb") as output:
            subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{github.repo}/releases/assets/{asset['id']}",
                    "-H",
                    "Accept: application/octet-stream",
                ],
                stdout=output,
                check=True,
            )
        if file_hash(path) != release.manifest[asset["name"]]:
            raise ReleaseError(
                f"Original artifact {asset['name']!r} has a different hash. Stop for review."
            )


def save_originals(github: GitHub, release: Release, directory: Path) -> None:
    existing = github.pages(f"releases/{release.release_id}/assets")
    if existing:
        raise ReleaseError(
            "The draft already contains artifacts. Restore the original files before retrying."
        )
    subprocess.run(
        [
            "gh",
            "release",
            "upload",
            release.tag,
            "--repo",
            github.repo,
            *(str(directory / name) for name in release.manifest),
        ],
        check=True,
    )


def pypi_inventory(version: str) -> dict[str, str]:
    uploaded: dict[str, str] = {}
    for distribution in sorted(smoke_entry_points.PUBLISHED_DISTRIBUTIONS):
        try:
            with urlopen(
                f"https://pypi.org/pypi/{distribution}/{Version(version)}/json",
                timeout=30,
            ) as response:
                files = json.load(response)["urls"]
        except HTTPError as exc:
            if exc.code != 404:
                raise
            continue
        for wheel in files:
            if wheel["filename"] in uploaded:
                raise ReleaseError(
                    f"Duplicate published artifact: {wheel['filename']!r}"
                )
            if wheel.get("yanked"):
                raise ReleaseError(
                    f"Published artifact {wheel['filename']!r} is withdrawn. Stop for review."
                )
            uploaded[wheel["filename"]] = wheel["digests"]["sha256"]
    return uploaded


def stage_missing(
    release: Release, original: Path, destination: Path, uploaded: dict[str, str]
) -> list[str]:
    """Copy only absent uploads after checking every original file."""
    if original_manifest(original, release.version) != release.manifest:
        raise ReleaseError(
            "Local artifacts differ from the original manifest. Stop for review."
        )
    missing = missing_uploads(release.manifest, uploaded)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ReleaseError(f"Upload directory {str(destination)!r} must be empty.")
    for name in missing:
        shutil.copy2(original / name, destination / name)
    return missing


def wait_for_pypi(
    release: Release,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Wait for every original file to appear on PyPI, within the propagation window."""
    deadline = clock() + PYPI_PROPAGATION_TIMEOUT_S
    while True:
        missing = missing_uploads(release.manifest, pypi_inventory(release.version))
        if not missing:
            return
        if clock() >= deadline:
            raise ReleaseError(
                f"PyPI is incomplete after {PYPI_PROPAGATION_TIMEOUT_S}s: {missing!r}. "
                "Resume after the upload or propagation failure is resolved."
            )
        sleep(PYPI_POLL_INTERVAL_S)


def install_from_pypi(
    requirements: list[str],
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Install from the public index, retrying while the simple index catches up."""
    deadline = clock() + PYPI_PROPAGATION_TIMEOUT_S
    while True:
        try:
            install_smoke(requirements)
            return
        except subprocess.CalledProcessError as exc:
            if clock() >= deadline:
                raise ReleaseError(
                    f"Public PyPI installation failed after {PYPI_PROPAGATION_TIMEOUT_S}s: {requirements!r}"
                ) from exc
        sleep(PYPI_POLL_INTERVAL_S)


def public_install(github: GitHub, release: Release) -> None:
    """Exercise both public package channels with the recorded version."""
    wait_for_pypi(release)
    requirements = [
        f"{name}=={Version(release.version)}"
        for name in sorted(smoke_entry_points.PUBLISHED_DISTRIBUTIONS)
    ]
    install_from_pypi(requirements)
    published = github.api(f"releases/{release.release_id}")
    if published["draft"] or published["tag_name"] != release.tag:
        raise ReleaseError("The GitHub Release is not public at the recorded tag.")
    with tempfile.TemporaryDirectory(prefix="release-public-") as temporary:
        directory = Path(temporary)
        assets = github.pages(f"releases/{release.release_id}/assets")
        if {asset["name"] for asset in assets} != set(release.manifest):
            raise ReleaseError(
                "GitHub Release assets differ from the original manifest."
            )
        for asset in assets:
            with urlopen(asset["browser_download_url"], timeout=60) as response:
                (directory / asset["name"]).write_bytes(response.read())
        if original_manifest(directory, release.version) != release.manifest:
            raise ReleaseError("Public GitHub files differ from the original manifest.")
        install_smoke([str(directory / name) for name in release.manifest])
