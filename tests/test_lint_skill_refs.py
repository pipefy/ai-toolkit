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
    monkeypatch.setattr(
        _lint,
        "_load_pipefy_client_method_names",
        lambda: frozenset({"get_pipe", "sdk_only"}),
    )
    skill = tmp_path / "skills/pipes/pipefy-pipes"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: pipefy-pipes\ndescription: Read pipes.\n---\n"
        "# Pipes\n| `get_pipe` | Read pipe |\n"
    )
    return skill


def test_valid_operation_in_body_passes(catalog):
    assert _lint.main() == 0


def test_unknown_operation_in_body_fails(catalog, capsys):
    with (catalog / "SKILL.md").open("a") as skill:
        skill.write("| `get_piep` | Read pipe |\n")
    assert _lint.main() == 1
    assert "unknown operation `get_piep`" in capsys.readouterr().err


def test_sdk_only_operation_passes_for_sdk_skill(catalog):
    (catalog / "SKILL.md").write_text(
        "---\nname: pipefy-pipes\ndescription: Read pipes.\n"
        'metadata:\n  surfaces: "sdk"\n---\n'
        "| `sdk_only` | SDK operation |\n"
    )
    assert _lint.main() == 0


def test_mcp_only_operation_fails_for_shared_skill(catalog, capsys, monkeypatch):
    with (catalog / "SKILL.md").open("a") as skill:
        skill.write("| `mcp_only` | MCP operation |\n")
    monkeypatch.setattr(
        _lint, "_load_pipefy_tool_names", lambda: frozenset({"get_pipe", "mcp_only"})
    )
    assert _lint.main() == 1
    assert "operation `mcp_only` missing from SDK" in capsys.readouterr().err


def test_sdk_only_operation_fails_for_shared_skill(catalog, capsys):
    with (catalog / "SKILL.md").open("a") as skill:
        skill.write("| `sdk_only` | SDK operation |\n")
    assert _lint.main() == 1
    assert "unknown MCP tool `sdk_only`" in capsys.readouterr().err


def test_mcp_only_operation_passes_for_mcp_skill(catalog, monkeypatch):
    monkeypatch.setattr(
        _lint, "_load_pipefy_tool_names", lambda: frozenset({"get_pipe", "mcp_only"})
    )
    (catalog / "SKILL.md").write_text(
        "---\nname: pipefy-pipes\ndescription: Read pipes.\n"
        'metadata:\n  surfaces: "mcp"\n---\n'
        "| `mcp_only` | MCP operation |\n"
    )
    assert _lint.main() == 0


def test_sdk_only_operation_fails_in_mcp_reference(catalog, capsys):
    reference = catalog / "references/mcp.md"
    reference.parent.mkdir()
    reference.write_text("| `sdk_only` | SDK operation |\n")
    assert _lint.main() == 1
    assert "references/mcp.md:1: unknown MCP tool `sdk_only`" in capsys.readouterr().err


def test_unknown_operation_example_fails(catalog, capsys):
    with (catalog / "SKILL.md").open("a") as skill:
        skill.write("Operation: `get_piep pipe_id=123`\n")
    assert _lint.main() == 1
    assert "unknown operation `get_piep`" in capsys.readouterr().err


def test_unknown_fenced_mcp_operation_fails(catalog, capsys):
    reference = catalog / "references/mcp.md"
    reference.parent.mkdir()
    reference.write_text("```text\nget_piep pipe_id=123\n```\n")
    assert _lint.main() == 1
    assert "references/mcp.md:2: unknown MCP tool `get_piep`" in capsys.readouterr().err


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
    (refs / "mcp.md").write_text(
        "| `get_pipe` | Read pipe |\n```text\nget_pipe pipe_id=123\n```\n"
    )
    (catalog.parent / "README.md").write_text("pipefy unrelated prose\n")
    assert _lint.main() == 0


def test_missing_catalog_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(_lint, "REPO_ROOT", tmp_path)
    assert _lint.main() == 1
    assert "No skills/ directory found" in capsys.readouterr().err


def test_client_method_names_come_from_pipefy_client(tmp_path, monkeypatch):
    monkeypatch.setattr(_lint, "REPO_ROOT", tmp_path)
    client = tmp_path / "packages/sdk/src/pipefy_sdk/client.py"
    client.parent.mkdir(parents=True)
    client.write_text(
        "class Other:\n    def unrelated(self): ...\n"
        "class PipefyClient:\n    async def get_pipe(self): ...\n"
        "    def from_executors(self): ...\n"
    )
    assert _lint._load_pipefy_client_method_names() == {"get_pipe"}
