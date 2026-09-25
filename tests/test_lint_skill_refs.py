"""Keep skill commands checked after progressive disclosure into references."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1] / ".github/workflows/scripts/lint_skill_refs.py"
)
_spec = importlib.util.spec_from_file_location("lint_skill_refs", _SCRIPT)
assert _spec and _spec.loader
_lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lint)


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(_lint, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        _lint, "_load_pipefy_tool_names", lambda: frozenset({"get_pipe"})
    )
    skill = tmp_path / "skills/pipes/pipefy-pipes"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Pipes\n| `get_pipe` | Read pipe |\n")
    return skill


def test_valid_operation_in_body_passes(catalog):
    assert _lint.main() == 0


def test_unknown_operation_in_body_fails(catalog, capsys):
    (catalog / "SKILL.md").write_text("| `get_piep` | Read pipe |\n")
    assert _lint.main() == 1
    assert "SKILL.md:1: unknown MCP tool `get_piep`" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("filename", "content", "error"),
    [
        ("cli.md", "pipefy typo list\n", "unknown CLI subcommand `typo`"),
        ("mcp.md", "| `get_piep` | Read pipe |\n", "unknown MCP tool `get_piep`"),
        ("nested/example.md", "pipefy typo get\n", "unknown CLI subcommand `typo`"),
    ],
)
def test_invalid_reference_fails(catalog, capsys, filename, content, error):
    reference = catalog / "references" / filename
    reference.parent.mkdir(parents=True)
    reference.write_text(content)
    assert _lint.main() == 1
    assert f"references/{filename}:1: {error}" in capsys.readouterr().err


def test_valid_references_pass_without_linting_unrelated_docs(catalog):
    refs = catalog / "references"
    refs.mkdir()
    (refs / "cli.md").write_text("pipefy pipe get 123\n")
    (refs / "mcp.md").write_text("| `get_pipe` | Read pipe |\n")
    (catalog.parent / "README.md").write_text("pipefy unrelated prose\n")
    assert _lint.main() == 0


def test_missing_catalog_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(_lint, "REPO_ROOT", tmp_path)
    assert _lint.main() == 1
    assert "No skills/ directory found" in capsys.readouterr().err
