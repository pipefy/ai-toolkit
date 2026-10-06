"""Every relative Markdown link in the repository resolves to a file, and to a heading when it names one."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*$", re.MULTILINE)
_HTML_ANCHOR_RE = re.compile(r'<a (?:name|id)="([^"]+)"')
_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:")


def github_slug(heading):
    """The anchor GitHub derives from a heading: lower case, punctuation dropped, spaces to hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors_in(markdown):
    """The set of anchors a Markdown document defines, numbering repeats as GitHub does."""
    prose = _FENCE_RE.sub("", markdown)
    anchors = set(_HTML_ANCHOR_RE.findall(prose))
    for heading in _HEADING_RE.findall(prose):
        base = github_slug(heading)
        anchor, n = base, 0
        while anchor in anchors:
            n += 1
            anchor = f"{base}-{n}"
        anchors.add(anchor)
    return anchors


def broken_links(source, markdown, read):
    """Relative links in ``markdown`` that miss a file or an anchor. ``read`` returns a file's text."""
    broken = []
    for target in _LINK_RE.findall(_FENCE_RE.sub("", markdown)):
        if _SCHEME_RE.match(target):
            continue
        path, _, fragment = target.partition("#")
        resolved = (source.parent / path).resolve() if path else source.resolve()
        if not resolved.exists():
            broken.append(target)
        elif (
            fragment
            and resolved.suffix == ".md"
            and fragment not in anchors_in(read(resolved))
        ):
            broken.append(target)
    return broken


def _tracked_markdown():
    names = subprocess.check_output(
        ["git", "ls-files", "*.md"], cwd=_REPO_ROOT, text=True
    ).split()
    return [_REPO_ROOT / name for name in names]


@pytest.mark.parametrize(
    ("heading", "anchor"),
    [
        (
            "Field references: slug vs `internal_id`",
            "field-references-slug-vs-internal_id",
        ),
        ("MCP tool ↔ CLI", "mcp-tool--cli"),
        ("Step 2. Run it", "step-2-run-it"),
    ],
)
def test_github_slug_matches_github(heading, anchor):
    assert github_slug(heading) == anchor


def test_repeated_headings_get_numbered_anchors():
    assert anchors_in("# Notes\n## Notes\n") == {"notes", "notes-1"}


def test_every_relative_link_resolves():
    def read(path):
        return path.read_text(encoding="utf-8", errors="ignore")

    problems = [
        f"{source.relative_to(_REPO_ROOT)}: {target}"
        for source in _tracked_markdown()
        for target in broken_links(source, read(source), read)
    ]
    assert not problems, "Broken Markdown links:\n" + "\n".join(problems)
