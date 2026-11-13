#!/usr/bin/env python3
"""Prepare, publish, and recover releases through the procedure in RELEASE.md."""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bump_version  # noqa: E402
from release_checks import print_release_links, verify, version_from_tag  # noqa: E402
from release_commands import abandon, github_client, resume, start, status  # noqa: E402
from release_gates import select_candidate  # noqa: E402
from release_state import ReleaseError  # noqa: E402

REPO_ROOT = bump_version.REPO_ROOT
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
DEV_BRANCH = "dev"
MAIN_BRANCH = "main"
UNRELEASED_RE = re.compile(
    r"^(## \[Unreleased\][^\n]*\n)(.*?)(?=^## \[|\Z)", re.MULTILINE | re.DOTALL
)


def run(command: list[str]) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def capture(command: list[str]) -> str:
    return subprocess.run(
        command, cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def confirm(prompt: str, *, assume_yes: bool) -> None:
    if assume_yes:
        return
    if not sys.stdin.isatty():
        raise ReleaseError(
            f"{prompt} Use --yes only with the maintainer's authorization."
        )
    if input(f"{prompt} [y/N] ").strip().lower() not in {"y", "yes"}:
        raise ReleaseError("Aborted by operator.")


def working_tree_clean() -> bool:
    return not capture(["git", "status", "--porcelain"])


def current_branch() -> str:
    return capture(["git", "branch", "--show-current"])


def stamp_changelog(version: str) -> None:
    today = datetime.date.today().isoformat()
    text = CHANGELOG.read_text(encoding="utf-8")
    heading = f"## [Unreleased]\n\n## [{version}] - {today}\n"
    stamped, count = UNRELEASED_RE.subn(lambda match: heading + match[2], text, count=1)
    if count != 1:
        raise ReleaseError("Expected one Unreleased heading in CHANGELOG.md.")
    CHANGELOG.write_text(stamped, encoding="utf-8")


def target_for(bump_arg: str, current: str) -> str:
    bumpers = {
        "major": bump_version.bump_major,
        "minor": bump_version.bump_minor,
        "patch": bump_version.bump_patch,
        "prerelease": bump_version.bump_prerelease,
        "beta": bump_version.bump_beta,
    }
    try:
        if bump_arg.lower().startswith("version="):
            return bump_version.parse_explicit_version(bump_arg)
        if bump_arg not in bumpers:
            raise ValueError(
                f"Unknown bump {bump_arg!r}. Use major, minor, patch, prerelease, beta, or version=X.Y.Z."
            )
        return bumpers[bump_arg](current)
    except ValueError as exc:
        raise ReleaseError(str(exc)) from exc


def apply_prepare(bump_arg: str, target: str) -> None:
    run(["uv", "run", "python", "scripts/bump_version.py", bump_arg])
    if bump_version.read_sdk_version() != target:
        raise ReleaseError(
            "The version transform differs from the selected target. Stop before committing."
        )
    if bump_version.prerelease_track(target) != "alpha":
        stamp_changelog(target)
    run(["uv", "run", "python", "scripts/bump_version.py", "verify"])
    paths = {
        *bump_version.INIT_PATHS,
        *bump_version.PACKAGE_PYPROJECTS,
        *bump_version.JSON_MANIFESTS,
        bump_version.ROOT_PYPROJECT,
        REPO_ROOT / "uv.lock",
        CHANGELOG,
    }
    allowed = {str(path.relative_to(REPO_ROOT)) for path in paths}
    changed = set(capture(["git", "diff", "--name-only"]).splitlines())
    if changed - allowed:
        raise ReleaseError(
            f"Unexpected preparation changes: {sorted(changed - allowed)!r}. Review them before committing."
        )
    run(["git", "add", "--", *sorted(allowed)])
    run(["git", "commit", "-s", "-m", f"chore: prepare v{target}"])


def prepare(bump_arg: str, *, assume_yes: bool = False) -> str:
    if not working_tree_clean():
        raise ReleaseError(
            "The working tree is dirty. Commit or stash changes before preparation."
        )
    if current_branch() in {MAIN_BRANCH, DEV_BRANCH, ""}:
        raise ReleaseError(
            "Use a preparation branch. The release-pr command creates one from dev."
        )
    current = bump_version.read_sdk_version()
    target = target_for(bump_arg, current)
    from packaging.version import Version

    if Version(target) <= Version(current):
        raise ReleaseError(f"Target {target} must be newer than {current}.")
    match = UNRELEASED_RE.search(CHANGELOG.read_text())
    if not match or not match[2].strip():
        raise ReleaseError("Add release notes under Unreleased before preparation.")
    confirm(
        f"Prepare and commit version {target} on {current_branch()}?",
        assume_yes=assume_yes,
    )
    apply_prepare(bump_arg, target)
    return target


def preparation_body(previous: str, version: str, notes: str) -> str:
    changelog = (
        "Keep Unreleased notes for the alpha."
        if bump_version.prerelease_track(version) == "alpha"
        else "Stamp release notes and retain an empty Unreleased section."
    )
    return (
        "## Summary\n\n"
        f"- Prepare `{previous}` -> `{version}` in `dev`.\n"
        "- Update shared versions, exact dependency pins, manifests, and the lockfile.\n"
        f"- {changelog}\n\n"
        "## Test plan\n\n"
        "- [x] `uv run python scripts/bump_version.py verify`\n"
        "- [ ] Candidate CI and package installation tests pass before publication.\n\n"
        f"## Docs / skills\n\n{notes}\n\n"
        "## Legal / contributions\n\n"
        "- [x] The preparation commit includes DCO sign-off.\n\n"
        "After approval and merge into dev, follow RELEASE.md to select and publish the candidate.\n"
    )


def release_pr(bump_arg: str, *, alpha: bool = False, assume_yes: bool = False) -> None:
    if not working_tree_clean():
        raise ReleaseError(
            "The working tree is dirty. Commit or stash changes before preparation."
        )
    run(
        [
            "git",
            "fetch",
            "origin",
            "+refs/heads/dev:refs/remotes/origin/dev",
            "+refs/heads/main:refs/remotes/origin/main",
            "--tags",
        ]
    )
    import tomllib

    from packaging.version import Version

    current = tomllib.loads(capture(["git", "show", "origin/dev:pyproject.toml"]))[
        "project"
    ]["version"]
    main_version = tomllib.loads(
        capture(["git", "show", "origin/main:pyproject.toml"])
    )["project"]["version"]
    target = target_for(bump_arg, current)
    if (bump_version.prerelease_track(target) == "alpha") != alpha:
        raise ReleaseError(
            "Use alpha-pr for an alpha and release-pr for a beta or stable release."
        )
    if Version(target) <= max(Version(current), Version(main_version)):
        raise ReleaseError(
            f"Target {target} must be newer than dev {current} and main {main_version}."
        )
    previous = f"v{main_version}"
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", previous, "origin/dev"],
        cwd=REPO_ROOT,
        check=False,
    )
    if ancestor.returncode:
        raise ReleaseError(
            f"dev omits the published tag {previous}. Merge the correction branch into dev first."
        )
    previous_tree, main_tree = capture(
        ["git", "rev-parse", f"{previous}^{{tree}}", "origin/main^{tree}"]
    ).splitlines()
    if previous_tree != main_tree:
        raise ReleaseError(
            "main differs from its published tag. Reconcile source changes before preparation."
        )
    match = UNRELEASED_RE.search(capture(["git", "show", "origin/dev:CHANGELOG.md"]))
    if not match or not match[2].strip():
        raise ReleaseError(
            "Add release notes under Unreleased in dev before preparation."
        )
    branch = f"prepare/v{target}"
    if capture(["git", "branch", "--list", branch]) or capture(
        ["git", "ls-remote", "--heads", "origin", branch]
    ):
        raise ReleaseError(
            f"Preparation branch {branch!r} already exists. Continue its PR instead."
        )
    confirm(
        f"Create, commit, and push {branch}, then open its preparation PR into dev?",
        assume_yes=assume_yes,
    )
    run(["git", "switch", "-c", branch, "origin/dev"])
    apply_prepare(bump_arg, target)
    run(["git", "push", "-u", "origin", branch])
    with tempfile.TemporaryDirectory(prefix="release-pr-") as temporary:
        body = Path(temporary) / "body.md"
        body.write_text(preparation_body(current, target, match[2].strip()))
        run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                "dev",
                "--head",
                branch,
                "--title",
                f"chore: prepare v{target}",
                "--body-file",
                str(body),
            ]
        )
    print(
        "After review and merge, select the prepared commit with 'release.py publish --sha COMMIT'."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "release-pr", "alpha-pr"):
        command = sub.add_parser(name)
        command.add_argument(
            "bump", help="major | minor | patch | prerelease | beta | version=X.Y.Z"
        )
        command.add_argument("--yes", action="store_true")
    for name in ("publish", "doctor"):
        command = sub.add_parser(name)
        command.add_argument(
            "--sha",
            required=name == "publish",
            help="full prepared commit SHA (doctor defaults to origin/dev)",
        )
        command.add_argument("--hotfix", action="store_true")
        if name == "publish":
            command.add_argument("--yes", action="store_true")
    command = sub.add_parser("resume")
    command.add_argument("tag")
    command = sub.add_parser("abandon")
    command.add_argument("tag")
    command.add_argument("--reason", required=True)
    command.add_argument("--yes", action="store_true")
    sub.add_parser("status")
    command = sub.add_parser("verify")
    command.add_argument("tag")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.bump, assume_yes=args.yes)
        elif args.command in {"release-pr", "alpha-pr"}:
            release_pr(args.bump, alpha=args.command == "alpha-pr", assume_yes=args.yes)
        elif args.command == "verify":
            verify(args.tag)
            print_release_links(args.tag, version_from_tag(args.tag))
        else:
            github = github_client()
            if args.command in {"publish", "doctor"}:
                if not working_tree_clean():
                    raise ReleaseError(
                        "The working tree is dirty. Use a clean checkout of the release tooling."
                    )
                sha = args.sha or github.ref("heads/dev")
                selected = select_candidate(github, sha, hotfix=args.hotfix)
                if args.command == "doctor":
                    print(f"Release prerequisites passed for {selected.tag} at {sha}.")
                else:
                    confirm(
                        f"Authorize {selected.tag} at {sha}, including publication and promotion after review?",
                        assume_yes=args.yes,
                    )
                    start(github, sha, hotfix=args.hotfix)
            elif args.command == "resume":
                resume(github, args.tag)
            elif args.command == "status":
                status(github)
            else:
                confirm(
                    f"Abandon {args.tag}? Public package files will remain available.",
                    assume_yes=args.yes,
                )
                abandon(github, args.tag, args.reason)
    except (ReleaseError, subprocess.CalledProcessError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
