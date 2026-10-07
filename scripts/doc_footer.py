#!/usr/bin/env python3
"""Check or write the feedback footer that ends every page under ``docs/``.

Run with ``--fix`` to add or repair the footer on every page.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_REPO_URL = "https://github.com/pipefy/ai-toolkit"
_FOOTER_RE = re.compile(r"\n---\n\nFound a problem on this page\?[^\n]*\n*\Z")
# An accepted decision record is immutable, so it carries no footer.
_IMMUTABLE_RE = re.compile(r"^docs/contributing/adr/\d{4}-")


def footer(rel_path: str) -> str:
    return (
        "\n---\n\n"
        "Found a problem on this page? "
        f"[Open an issue]({_REPO_URL}/issues/new?template=docs_problem.yml&page={rel_path}), "
        f"or [edit the page]({_REPO_URL}/edit/main/{rel_path}).\n"
    )


def with_footer(markdown: str, rel_path: str) -> str:
    body = _FOOTER_RE.sub("", markdown).rstrip("\n") + "\n"
    return body + footer(rel_path)


def pages() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "docs/*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [name for name in listed if not _IMMUTABLE_RE.match(name)]


def main(argv: list[str]) -> int:
    fix = "--fix" in argv
    stale: list[str] = []
    for rel_path in pages():
        path = REPO_ROOT / rel_path
        text = path.read_text(encoding="utf-8")
        expected = with_footer(text, rel_path)
        if text == expected:
            continue
        stale.append(rel_path)
        if fix:
            path.write_text(expected, encoding="utf-8")
    if stale and not fix:
        print("Pages without the feedback footer (run with --fix):", file=sys.stderr)
        print("\n".join(f"  {name}" for name in stale), file=sys.stderr)
        return 1
    if stale:
        print(f"Wrote the footer on {len(stale)} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
