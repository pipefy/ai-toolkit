"""The user docs name only shipped MCP tools and ``pipefy`` commands and options."""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts/lint_skill_refs.py"
_spec = importlib.util.spec_from_file_location("lint_skill_refs", _SCRIPT)
assert _spec and _spec.loader
_lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lint)

# Contributor docs quote example names on purpose, and the generated reference has its own test.
_EXCLUDED = ("docs/contributing/", "docs/mcp/reference.md")
# `pipefy` here is a server name, a package name, or part of a quoted message, not the CLI.
_NOT_A_CLI_CALL = re.compile(r"pipefy\s+\S*://|uv add|pip install|uv pip")
# A snake_case code span, with an optional call such as `get_card(card_id=1)`.
_SNAKE_SPAN_RE = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?:\([^`]*\))?`")
# Names that start with a tool verb but name an API value or a parameter, not a tool.
_NOT_TOOLS = frozenset(
    {
        # Automation action IDs and input modes that the Pipefy API defines.
        "create_connected_card",
        "fill_with_ai",
        "move_card",
        "move_single_card",
        "send_a_task",
        "send_email_template",
        # Parameters and response fields.
        "export_id",
        "search_query",
    }
)


def _user_docs() -> list[Path]:
    listed = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "README.md",
            "docs/*.md",
            "packages/*/README.md",
        ],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [_ROOT / name for name in listed if not name.startswith(_EXCLUDED)]


def _meta_tool_names() -> frozenset[str]:
    """The catalog meta-tools, which the `power` keyword lists in place of the registry."""
    source = (_ROOT / "packages/mcp/src/pipefy_mcp/tools/meta_tools.py").read_text(
        encoding="utf-8"
    )
    return frozenset(
        node.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_")
    )


def _tool_names_in(line: str, verbs: frozenset[str]) -> list[str]:
    """Code spans shaped like a tool name: snake_case, opening with a verb that some tool opens with."""
    return [
        name
        for name in _SNAKE_SPAN_RE.findall(line)
        if name.split("_", 1)[0] in verbs and name not in _NOT_TOOLS
    ]


def unknown_references(
    markdown: str, tools: frozenset[str], cli_tree: dict
) -> list[str]:
    """Each tool or ``pipefy`` command in ``markdown`` that the toolkit does not ship.

    ``tools`` holds every name a doc may call a tool: MCP tools, meta-tools, and SDK methods.
    """
    verbs = frozenset(name.split("_", 1)[0] for name in tools)
    problems: list[str] = []
    in_fence = False
    for number, line in enumerate(markdown.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            problems.extend(
                f"line {number}: unknown tool `{name}`"
                for name in _tool_names_in(line, verbs)
                if name not in tools
            )
        if line.lstrip().startswith("#") and not in_fence:
            continue
        if "pipefy" not in line or _NOT_A_CLI_CALL.search(line):
            continue
        for segment, is_code in _lint._code_segments(line, in_fence=in_fence):
            for match in _lint.PIPEFY_INVOCATION_RE.finditer(segment):
                problems.extend(
                    f"line {number}: {error}"
                    for error in _lint._cli_errors(
                        segment[match.start(1) :], cli_tree, walk=is_code
                    )
                )
    return problems


_TREE = {"card": {"get": frozenset({"--help", "--json"})}}


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        ("Run `pipefy card get 1 --json`.", []),
        (
            "Run `pipefy card get 1 --yaml`.",
            ["line 1: unknown option `--yaml` for `pipefy card get`"],
        ),
        (
            "```sh\npipefy pipe list\n```",
            ["line 2: unknown CLI subcommand `pipe` (from `pipefy pipe`)"],
        ),
        ("The agent calls the `get_card` tool.", []),
        ("The agent calls `get_cards`.", ["line 1: unknown tool `get_cards`"]),
        ("Call `get_cards(pipe_id=1)` next.", ["line 1: unknown tool `get_cards`"]),
        ("Pass `card_id` and `move_single_card`.", []),
        ("claude mcp add pipefy https://mcp.pipefy.com/mcp", []),
        ("uv add pipefy pipefy-auth", []),
    ],
)
def test_unknown_references_flags_only_unshipped_names(markdown, expected):
    assert unknown_references(markdown, frozenset({"get_card"}), _TREE) == expected


@pytest.fixture(scope="module")
def shipped() -> tuple[frozenset[str], dict]:
    tools = (
        _lint._load_pipefy_tool_names()
        | _lint._load_pipefy_client_method_names()
        | _meta_tool_names()
    )
    return tools, _lint._load_pipefy_cli_tree()


@pytest.mark.parametrize(
    "path", _user_docs(), ids=lambda path: str(path.relative_to(_ROOT))
)
def test_user_docs_name_only_shipped_tools_and_commands(path, shipped):
    tools, cli_tree = shipped
    problems = unknown_references(path.read_text(encoding="utf-8"), tools, cli_tree)
    assert not problems, "\n".join(problems)
