"""Skill references survive consumers flattening the catalog by skill name."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "pipefy" / "skills"


def test_references_resolve_in_flat_installation(tmp_path):
    entrypoints = sorted(_SKILLS.glob("*/SKILL.md"))
    assert entrypoints
    for entrypoint in entrypoints:
        shutil.copytree(entrypoint.parent, tmp_path / entrypoint.parent.name)

    for document in tmp_path.rglob("*.md"):
        for target in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", document.read_text()):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            resolved = (document.parent / unquote(url.path)).resolve()
            assert resolved.is_relative_to(tmp_path), (document, target)
            assert resolved.is_file(), (document, target)


def test_plugin_readme_lists_every_skill():
    catalog = (_SKILLS.parent / "README.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"\]\(skills/([^/)]+)/SKILL\.md\)", catalog))
    assert listed == {entry.parent.name for entry in _SKILLS.glob("*/SKILL.md")}
