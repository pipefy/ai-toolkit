"""Absolute links into this repository resolve against the checkout, so a PR that moves a file fails here.

A package README links to the docs by absolute URL, because PyPI cannot resolve a relative link.
The external link check skips these URLs, because the branch, not `main`, holds the target.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "test_doc_links", _ROOT / "tests/test_doc_links.py"
)
assert _spec and _spec.loader
_links = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_links)

_SELF_LINK_RE = re.compile(
    r"https://github\.com/pipefy/ai-toolkit/(?:blob|tree)/main/([^)\s#>`\"']+)(?:#([^)\s>`\"']+))?"
)


def _tracked_markdown() -> list[Path]:
    names = subprocess.check_output(
        ["git", "ls-files", "*.md"], cwd=_ROOT, text=True
    ).split()
    return [_ROOT / name for name in names]


def broken_self_links(markdown: str, root: Path) -> list[str]:
    """Self-links in ``markdown`` whose path or anchor is missing under ``root``."""
    broken = []
    for path, anchor in _SELF_LINK_RE.findall(markdown):
        target = root / path.rstrip("/")
        if not target.exists():
            broken.append(f"{path}: no such file")
        elif anchor and target.suffix == ".md":
            if anchor not in _links.anchors_in(target.read_text(encoding="utf-8")):
                broken.append(f"{path}#{anchor}: no such heading")
    return broken


def test_broken_self_links_reports_missing_file_and_heading(tmp_path: Path) -> None:
    (tmp_path / "guide.md").write_text("# Guide\n\n## Sign in\n", encoding="utf-8")
    base = "https://github.com/pipefy/ai-toolkit/blob/main/"
    markdown = (
        f"[a]({base}guide.md#sign-in) [b]({base}guide.md#log-in) [c]({base}gone.md)"
    )
    assert broken_self_links(markdown, tmp_path) == [
        "guide.md#log-in: no such heading",
        "gone.md: no such file",
    ]


@pytest.mark.parametrize(
    "path", _tracked_markdown(), ids=lambda path: str(path.relative_to(_ROOT))
)
def test_every_self_link_resolves_in_the_checkout(path: Path) -> None:
    broken = broken_self_links(path.read_text(encoding="utf-8"), _ROOT)
    assert not broken, "\n".join(broken)
