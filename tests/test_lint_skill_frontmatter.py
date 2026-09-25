"""Frontmatter contracts for surface-aware skill discovery."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/workflows/scripts/lint_skill_frontmatter.py"
spec = importlib.util.spec_from_file_location("lint_skill_frontmatter", SCRIPT)
assert spec and spec.loader
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


def skill(extra=""):
    return f"---\nname: pipefy-example\ndescription: >\n  Example workflow.\n{extra}---\n# Body\n"


def test_existing_skill_defaults_to_all_surfaces():
    assert lint.parse_skill_surfaces(skill(), "pipefy-example") == {"sdk", "mcp", "cli"}


@pytest.mark.parametrize("value", ['"mcp cli"', '"sdk"', '"cli sdk mcp"'])
def test_explicit_surfaces(value):
    assert lint.parse_skill_surfaces(
        skill(f"metadata:\n  surfaces: {value}\n"), "pipefy-example"
    ) == frozenset(value.strip('"').split())


def test_unrelated_metadata_keeps_default():
    assert lint.parse_skill_surfaces(
        skill("metadata:\n  author: Pipefy\n"), "pipefy-example"
    ) == {"sdk", "mcp", "cli"}


@pytest.mark.parametrize(
    "value",
    ['""', '"  "', "null", "[mcp, cli]", "42", '"MCP"', '"mcp web"', '"mcp mcp"'],
)
def test_invalid_surfaces_are_rejected(value):
    with pytest.raises(ValueError, match="surfaces"):
        lint.parse_skill_surfaces(
            skill(f"metadata:\n  surfaces: {value}\n"), "pipefy-example"
        )


@pytest.mark.parametrize(
    "extra", ["metadata: null\n", "metadata: [mcp]\n", "metadata: mcp\n"]
)
def test_invalid_metadata_is_rejected(extra):
    with pytest.raises(ValueError, match="metadata"):
        lint.parse_skill_surfaces(skill(extra), "pipefy-example")


@pytest.mark.parametrize(
    "text",
    [
        "# No frontmatter",
        "---\nname: example\n",
        "---\n[invalid\n---\n",
        "---\n- item\n---\n",
        skill().replace("name: pipefy-example", "name: wrong"),
        skill().replace("description: >\n  Example workflow.", "description: ''"),
        skill().replace("name: pipefy-example\n", ""),
    ],
)
def test_invalid_base_frontmatter_is_rejected(text):
    with pytest.raises(ValueError):
        lint.parse_skill_surfaces(text, "pipefy-example")


def test_command_reports_file_and_nonzero_exit(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "no SKILL.md" in result.stderr
    directory = tmp_path / "pipefy-example"
    directory.mkdir()
    path = directory / "SKILL.md"
    path.write_text(skill("metadata:\n  surfaces: web\n"))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert str(path) in result.stderr
    assert "surfaces" in result.stderr
    path.write_text(skill())
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True
    )
    assert result.returncode == 0


def test_catalog_surface_exceptions():
    exceptions = {
        "pipefy-toolkit-setup": {"mcp", "cli"},
        "pipefy-attachments": {"mcp", "cli"},
        "pipefy-ipaas": {"mcp"},
    }
    paths = list((ROOT / "skills").rglob("SKILL.md"))
    assert exceptions.keys() <= {path.parent.name for path in paths}
    for path in paths:
        assert lint.parse_skill_surfaces(
            path.read_text(), path.parent.name
        ) == exceptions.get(path.parent.name, {"sdk", "mcp", "cli"})


@pytest.mark.parametrize(
    "extra",
    [
        "metadata:\n  surfaces: sdk\n  surfaces: mcp\n",
        "metadata: {surfaces: sdk}\nmetadata: {surfaces: mcp}\n",
        "name: pipefy-example\n",
    ],
)
def test_duplicate_keys_are_rejected(extra):
    with pytest.raises(ValueError, match="duplicate"):
        lint.parse_skill_surfaces(skill(extra), "pipefy-example")


@pytest.mark.parametrize(
    "value", ["true", "{mcp: true}", "!!python/object:builtins.object {}"]
)
def test_unexpected_yaml_types_are_rejected(value):
    with pytest.raises(ValueError):
        lint.parse_skill_surfaces(
            skill(f"metadata:\n  surfaces: {value}\n"), "pipefy-example"
        )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_folded_surfaces_and_body_delimiters(newline):
    text = (
        skill("metadata:\n  surfaces: >\n    mcp\n    cli\n")
        + "\n---\nmetadata: ignored body text\n"
    )
    assert lint.parse_skill_surfaces(text.replace("\n", newline), "pipefy-example") == {
        "mcp",
        "cli",
    }


def test_command_checks_copied_catalog_and_reports_all_errors(tmp_path):
    catalog = tmp_path / "skills"
    shutil.copytree(ROOT / "skills", catalog)
    command = [sys.executable, str(SCRIPT), str(catalog)]
    assert subprocess.run(command, capture_output=True, text=True).returncode == 0
    paths = sorted(catalog.rglob("SKILL.md"))[:3]
    originals = {path: path.read_text() for path in paths}
    for path in paths:
        text = originals[path]
        end = text.index("\n---", 3)
        path.write_text(text[:end] + "\nmetadata:\n  surfaces: web\n" + text[end:])
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1
    assert all(str(path) in result.stderr for path in paths)
    assert "Traceback" not in result.stderr
    for path, text in originals.items():
        path.write_text(text)
    assert subprocess.run(command, capture_output=True, text=True).returncode == 0
