"""Publish a recorded candidate in Actions without rebuilding on recovery."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from release_artifacts import (
    install_smoke,
    original_manifest,
    public_install,
    pypi_inventory,
    restore_originals,
    save_originals,
    stage_missing,
)
from release_gates import prepare_promotion, release_notes, require_candidate
from release_github import GitHub, Journal
from release_state import RELEASE_PROTOCOL, Release, ReleaseError


def draft_release(github: GitHub, journal: Journal, release: Release) -> None:
    if release.release_id:
        return
    matches = [
        item for item in github.pages("releases") if item["tag_name"] == release.tag
    ]
    if matches:
        draft = matches[0]
        if not draft["draft"] or draft["assets"]:
            raise ReleaseError(
                "An unrecorded release already contains public or stored files. Stop for review."
            )
    else:
        notes = release_notes(
            github.text_at("CHANGELOG.md", release.candidate), release.version
        )
        draft = github.api(
            "releases",
            "POST",
            {
                "tag_name": release.tag,
                "name": release.tag,
                "draft": True,
                "prerelease": release.kind == "alpha",
                "body": notes,
            },
        )
    release.release_id = draft["id"]
    journal.save(release)


def build_or_restore(
    github: GitHub, journal: Journal, release: Release, directory: Path
) -> None:
    draft_release(github, journal, release)
    if release.manifest:
        restore_originals(github, release, directory)
        return
    if release.build_started:
        raise ReleaseError(
            "The original build did not reach durable storage. Abandon this version instead of rebuilding it."
        )
    release.build_started = True
    journal.save(release)
    build = directory.parent / "build-dist"
    if build.exists() or directory.exists():
        raise ReleaseError("Build directories must be empty on a fresh runner.")
    subprocess.run(
        ["uv", "run", "python", "scripts/bump_version.py", "verify"], check=True
    )
    subprocess.run(
        ["uv", "build", "--all-packages", "--wheel", "--sdist", "-o", str(build)],
        check=True,
    )
    directory.mkdir()
    for wheel in build.glob("*.whl"):
        shutil.copy2(wheel, directory / wheel.name)
    release.manifest = original_manifest(directory, release.version)
    journal.save(release)
    save_originals(github, release, directory)


def stage(github: GitHub, journal: Journal, release: Release, root: Path) -> bool:
    if release.phase == "complete":
        return False
    require_candidate(github, release)
    if release.phase == "published":
        return False
    release.run_id = int(os.environ["GITHUB_RUN_ID"])
    journal.save(release)
    original = root / "dist-original"
    build_or_restore(github, journal, release, original)
    install_smoke([str(original / name) for name in release.manifest])
    release.phase = "built"
    journal.save(release)
    missing = stage_missing(
        release, original, root / "dist-pypi", pypi_inventory(release.version)
    )
    require_candidate(github, release)
    release.phase = "publishing"
    journal.save(release)
    github.api(
        f"releases/{release.release_id}",
        "PATCH",
        {"draft": False, "make_latest": "false"},
    )
    return bool(missing)


def complete(github: GitHub, journal: Journal, release: Release) -> None:
    if release.phase == "complete":
        return
    if release.phase not in {"publishing", "published"}:
        raise ReleaseError(
            "The original artifacts must pass the build and installation gate before public verification."
        )
    require_candidate(github, release)
    public_install(github, release)
    from release_checks import verify_installer_resolves, verify_installer_skips

    if release.kind == "alpha":
        verify_installer_skips(release.tag)
        release.phase = "complete"
    else:
        verify_installer_resolves(release.tag)
        require_candidate(github, release)
        release.promotion = prepare_promotion(github, release)
        release.phase = "published"
    journal.save(release)
    if release.kind != "alpha":
        for sha in (release.candidate, release.promotion):
            github.status(
                sha,
                "success",
                "Original packages published and public installations passed",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("stage", "guard", "complete"))
    args = parser.parse_args()
    if os.environ.get("RELEASE_PROTOCOL") != RELEASE_PROTOCOL:
        raise ReleaseError("The workflow uses an unsupported release protocol.")
    github = GitHub(os.environ["GITHUB_REPOSITORY"])
    journal = Journal(github)
    release = journal.get(os.environ["GITHUB_REF_NAME"])
    if release.candidate != os.environ["GITHUB_SHA"]:
        raise ReleaseError("The workflow does not run at the recorded candidate SHA.")
    if args.command == "stage":
        required = stage(github, journal, release, Path.cwd())
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            output.write(f"upload_required={'true' if required else 'false'}\n")
    elif args.command == "guard":
        require_candidate(github, release)
    else:
        complete(github, journal, release)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
