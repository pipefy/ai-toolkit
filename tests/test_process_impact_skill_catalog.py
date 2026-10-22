"""Catalog contracts for the process-impact skill and its routing hooks."""

from __future__ import annotations

import re
from pathlib import Path

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "pipefy" / "skills"
_SKILL_MD = _SKILLS / "pipefy-process-impact" / "SKILL.md"
_DESIGN_MD = _SKILLS / "pipefy-process-design" / "SKILL.md"
_INTELLIGENCE_MD = _SKILLS / "pipefy-process-intelligence" / "SKILL.md"
_BUILDING_MD = _SKILLS / "pipefy-building" / "SKILL.md"
_CATALOG_MD = _SKILLS.parent / "README.md"

_IMPACT_GUIDANCE = (
    "Keep Impact to one line. Do not invent volume, hourly cost, or lead time; "
    "name every missing number and ask for all of them in one question. "
    "For a fuller justification, read `pipefy-process-impact`."
)
_HEADCOUNT_CUT_TERMS = re.compile(
    r"head[\s-]?counts?|lay[\s-]?offs?|laid[\s-]?off|upsell|\bftes?\b"
)


def _table_rows(path):
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("|")
    ]


def test_catalog_readme_lists_process_impact():
    assert "pipefy-process-impact" in _CATALOG_MD.read_text(encoding="utf-8")


def test_building_routing_table_has_a_process_impact_row():
    assert any("`pipefy-process-impact`" in row for row in _table_rows(_BUILDING_MD))


def test_design_and_intelligence_share_one_impact_guidance_sentence():
    for path in (_DESIGN_MD, _INTELLIGENCE_MD):
        assert _IMPACT_GUIDANCE in path.read_text(encoding="utf-8"), path


def test_skill_frames_impact_as_time_returned_not_headcount_cut():
    text = _SKILL_MD.read_text(encoding="utf-8").casefold()
    assert "time returned" in text
    assert _HEADCOUNT_CUT_TERMS.search(text) is None
