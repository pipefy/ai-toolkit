"""Catalog contracts for the pipefy-building router."""

from __future__ import annotations

import re
from pathlib import Path

from test_process_impact_skill_catalog import _table_rows

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "pipefy" / "skills"
_ROUTER_MD = _SKILLS / "pipefy-building" / "SKILL.md"

_SKILL_NAME = re.compile(r"`(pipefy-[a-z0-9-]+)`")


def _body_lines() -> list[str]:
    lines = _ROUTER_MD.read_text(encoding="utf-8").splitlines()
    return lines[lines.index("---", 1) + 1 :]


def _routed_skills() -> set[str]:
    return {
        name for row in _table_rows(_ROUTER_MD) for name in _SKILL_NAME.findall(row)
    }


def _catalog_skills() -> set[str]:
    return {entry.parent.name for entry in _SKILLS.glob("*/SKILL.md")}


def test_every_skill_the_router_names_exists():
    named = set(_SKILL_NAME.findall("\n".join(_body_lines())))
    assert named <= _catalog_skills(), named - _catalog_skills()


def test_every_other_catalog_skill_has_a_routing_row():
    missing = _catalog_skills() - {"pipefy-building"} - _routed_skills()
    assert not missing, missing


def test_router_keeps_the_delivery_playbook_notice():
    assert "Do not use this skill as a delivery playbook" in "\n".join(_body_lines())
