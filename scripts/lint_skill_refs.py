#!/usr/bin/env python3
"""Validate skill operations, their argument names, and ``pipefy`` CLI commands."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from pipefy_sdk.skills import parse_skill_surfaces

if TYPE_CHECKING:
    import click

REPO_ROOT = Path(__file__).resolve().parents[1]

# A command group maps subcommand names to subtrees; a command maps to its long options.
CliTree = dict[str, "CliTree | frozenset[str]"]

# ``pipefy`` used in prose (e.g. install instructions) — not a subcommand.
_SKIP_CLI_LINE_SUBSTRINGS = (
    "uvx --from",
    "uv tool install",
    "github.com",
    "pipefy-cli",
    "pipefy-mcp-server",
)

MCP_TOOL_CELL_RE = re.compile(
    r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|",
    re.IGNORECASE,
)
OPERATION_EXAMPLE_RE = re.compile(r"\bOperation:\s*`([a-z][a-z0-9_]*)\b([^`]*)")
FENCED_OPERATION_RE = re.compile(r"^([a-z][a-z0-9]*_[a-z0-9_]+)(?=\s|\()")
ARGUMENT_NAME_RE = re.compile(r"([a-z_][a-z0-9_]*)=")
CODE_SPAN_RE = re.compile(r"`([^`]*)`")
CLI_WORD_RE = re.compile(r"[a-z][a-z0-9-]*")
# Shell syntax that ends a ``pipefy`` invocation; a bare ``<`` too, but ``<PLACEHOLDER>`` is an argument.
_SHELL_STOP_PREFIXES = ("|", "&", ";", ">", "2>")

PIPEFY_INVOCATION_RE = re.compile(
    r"(?<![A-Za-z0-9])pipefy\s+([a-z][a-z0-9-]*)\b",
)


def _tool_names_from_ast_value(node: ast.expr) -> frozenset[str]:
    """Extract string tool names from ``frozenset({...})`` or ``set({...})``."""
    if not isinstance(node, ast.Call):
        msg = "PIPEFY_TOOL_NAMES value must be a frozenset(...) or set(...) call"
        raise RuntimeError(msg)
    if not isinstance(node.func, ast.Name) or node.func.id not in ("frozenset", "set"):
        msg = "PIPEFY_TOOL_NAMES must be assigned from frozenset(...) or set(...)"
        raise RuntimeError(msg)
    if len(node.args) != 1:
        msg = "PIPEFY_TOOL_NAMES frozenset/set must have exactly one argument"
        raise RuntimeError(msg)
    arg0 = node.args[0]
    if not isinstance(arg0, ast.Set):
        msg = "PIPEFY_TOOL_NAMES argument must be a set literal {...}"
        raise RuntimeError(msg)
    names: list[str] = []
    for elt in arg0.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            names.append(elt.value)
        else:
            msg = f"PIPEFY_TOOL_NAMES entries must be string literals, got {ast.dump(elt)}"
            raise RuntimeError(msg)
    return frozenset(names)


def _load_pipefy_tool_names() -> frozenset[str]:
    registry_path = REPO_ROOT / "packages/mcp/src/pipefy_mcp/tools/registry.py"
    tree = ast.parse(registry_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "PIPEFY_TOOL_NAMES":
                return _tool_names_from_ast_value(node.value)
    msg = "PIPEFY_TOOL_NAMES assignment not found in registry.py"
    raise RuntimeError(msg)


def _pipefy_client_methods() -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    client_path = REPO_ROOT / "packages/sdk/src/pipefy_sdk/client.py"
    tree = ast.parse(client_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "PipefyClient":
            return [
                method
                for method in node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not method.name.startswith("_")
                and method.name != "from_executors"
            ]
    msg = "PipefyClient class not found in client.py"
    raise RuntimeError(msg)


def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    args = node.args
    return frozenset(
        arg.arg
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)
        if arg.arg not in ("self", "ctx")
    )


def _load_pipefy_client_method_names() -> frozenset[str]:
    return frozenset(method.name for method in _pipefy_client_methods())


def _load_pipefy_client_method_params() -> dict[str, frozenset[str]]:
    return {
        method.name: _parameter_names(method) for method in _pipefy_client_methods()
    }


def _load_pipefy_tool_params() -> dict[str, frozenset[str]]:
    """Parameter names of each MCP tool, from the same-named functions in ``tools/``."""
    tool_names = _load_pipefy_tool_names()
    params: dict[str, frozenset[str]] = {}
    tools_dir = REPO_ROOT / "packages/mcp/src/pipefy_mcp/tools"
    for path in sorted(tools_dir.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            is_function = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if is_function and node.name in tool_names:
                params[node.name] = params.get(
                    node.name, frozenset()
                ) | _parameter_names(node)
    return params


def _cli_subtree(group: click.Group) -> CliTree:
    tree: CliTree = {}
    for name, command in group.commands.items():
        if hasattr(command, "commands"):
            tree[name] = _cli_subtree(command)
            continue
        options = {"--help"}
        for param in command.params:
            options.update(
                opt
                for opt in (*param.opts, *param.secondary_opts)
                if opt.startswith("--")
            )
        tree[name] = frozenset(options)
    return tree


def _load_pipefy_cli_tree() -> CliTree:
    """Command tree of the ``pipefy`` CLI, read from its Typer app."""
    import typer.main
    from pipefy_cli.main import app

    return _cli_subtree(typer.main.get_command(app))


class ReferenceCatalog(NamedTuple):
    """Names a skill may reference, loaded once per run."""

    mcp_names: frozenset[str]
    sdk_names: frozenset[str]
    mcp_params: dict[str, frozenset[str]]
    sdk_params: dict[str, frozenset[str]]
    cli_tree: CliTree


def _argument_names(arguments: str) -> list[str]:
    """Names of ``name=value`` arguments, ignoring text inside quoted or bracketed values."""
    names: list[str] = []
    depth, quote, at_token_start = 0, "", True
    for index, char in enumerate(arguments):
        if quote:
            quote = "" if char == quote else quote
        elif char in "\"'":
            quote = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth = max(depth - 1, 0)
        elif char.isspace():
            at_token_start = depth == 0
            continue
        elif at_token_start and depth == 0:
            match = ARGUMENT_NAME_RE.match(arguments, index)
            if match:
                names.append(match.group(1))
        at_token_start = False
    return names


def _cli_errors(invocation: str, tree: CliTree, *, walk: bool) -> list[str]:
    """Check the words after ``pipefy``: the root command always, the rest when ``walk``."""
    tokens = invocation.split()
    root = tokens[0]
    if root not in tree:
        return [f"unknown CLI subcommand `{root}` (from `pipefy {root}`)"]
    if not walk:
        return []
    node, path = tree[root], [root]
    rest = tokens[1:]
    while isinstance(node, dict) and rest and CLI_WORD_RE.fullmatch(rest[0]):
        if rest[0] not in node:
            return [f"unknown CLI subcommand `{' '.join([*path, rest[0]])}`"]
        node, path, rest = node[rest[0]], [*path, rest[0]], rest[1:]
    if isinstance(node, dict):
        return []
    errors: list[str] = []
    for token in rest:
        if token == "<" or token.startswith(_SHELL_STOP_PREFIXES):
            break
        option = token.split("=", 1)[0]
        if option.startswith("--") and option not in node:
            errors.append(f"unknown option `{option}` for `pipefy {' '.join(path)}`")
    return errors


def _code_segments(line: str, *, in_fence: bool) -> list[tuple[str, bool]]:
    """Split a line into (text, is_code) parts; fenced lines are code as a whole."""
    if in_fence:
        return [(line, True)]
    spans = CODE_SPAN_RE.findall(line)
    return [(CODE_SPAN_RE.sub(" ", line), False), *((span, True) for span in spans)]


def _lint_file(
    path: Path,
    catalog: ReferenceCatalog,
    surfaces: frozenset[str],
) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(REPO_ROOT)
    mcp_names, sdk_names = catalog.mcp_names, catalog.sdk_names

    def check_operation(tool: str, line_no: int) -> None:
        if path.name == "mcp.md" and tool not in mcp_names:
            errors.append(f"{rel}:{line_no}: unknown MCP tool `{tool}`")
        elif path.name == "SKILL.md":
            if tool not in mcp_names | sdk_names:
                errors.append(f"{rel}:{line_no}: unknown operation `{tool}`")
            elif "sdk" in surfaces and tool not in sdk_names:
                errors.append(f"{rel}:{line_no}: operation `{tool}` missing from SDK")
            elif "mcp" in surfaces and tool not in mcp_names:
                errors.append(f"{rel}:{line_no}: unknown MCP tool `{tool}`")
        elif tool not in mcp_names | sdk_names:
            errors.append(f"{rel}:{line_no}: unknown operation `{tool}`")

    def check_arguments(tool: str, arguments: str, line_no: int) -> None:
        if path.name == "mcp.md":
            allowed, label = catalog.mcp_params.get(tool), "MCP tool"
        elif path.name == "SKILL.md" and (
            tool in catalog.mcp_params or tool in catalog.sdk_params
        ):
            allowed = catalog.mcp_params.get(
                tool, frozenset()
            ) | catalog.sdk_params.get(tool, frozenset())
            label = "operation"
        else:
            return
        if allowed is None:
            return
        for name in _argument_names(arguments):
            if name not in allowed:
                errors.append(
                    f"{rel}:{line_no}: unknown argument `{name}` for {label} `{tool}`"
                )

    in_fence = False
    call_fence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if in_fence:
                in_fence = False
                call_fence = False
            else:
                in_fence = True
                call_fence = stripped[3:].strip() in ("", "text")
            continue
        if call_fence:
            fenced_operation = FENCED_OPERATION_RE.match(stripped)
            if fenced_operation:
                check_operation(fenced_operation.group(1), line_no)
                check_arguments(
                    fenced_operation.group(1),
                    stripped[fenced_operation.end() :],
                    line_no,
                )
        if stripped.startswith("|") and "`" in stripped:
            m = MCP_TOOL_CELL_RE.match(stripped)
            if m:
                tool = m.group(1)
                headerish = (
                    "tool (mcp)" in stripped.lower()
                    or stripped.lower().startswith("|------------")
                )
                if not headerish:
                    check_operation(tool, line_no)

        example = OPERATION_EXAMPLE_RE.search(line)
        if example:
            check_operation(example.group(1), line_no)
            check_arguments(example.group(1), example.group(2), line_no)

        if "pipefy" not in line.lower():
            continue
        if any(s in line for s in _SKIP_CLI_LINE_SUBSTRINGS):
            continue
        for segment, is_code in _code_segments(line, in_fence=in_fence):
            for m in PIPEFY_INVOCATION_RE.finditer(segment):
                if m.group(1).lower() == "pipefy":
                    continue
                for error in _cli_errors(
                    segment[m.start(1) :], catalog.cli_tree, walk=is_code
                ):
                    errors.append(f"{rel}:{line_no}: {error}")
    return errors


def main() -> int:
    """Lint all skills under ``skills/`` for MCP and CLI reference validity.

    Returns:
        0 if no issues, 1 otherwise.
    """
    skills_root = REPO_ROOT / "skills"
    if not skills_root.is_dir():
        print("No skills/ directory found.", file=sys.stderr)
        return 1

    catalog = ReferenceCatalog(
        mcp_names=_load_pipefy_tool_names(),
        sdk_names=_load_pipefy_client_method_names(),
        mcp_params=_load_pipefy_tool_params(),
        sdk_params=_load_pipefy_client_method_params(),
        cli_tree=_load_pipefy_cli_tree(),
    )
    all_errors: list[str] = []
    files_count = 0
    for skill_path in sorted(skills_root.rglob("SKILL.md")):
        try:
            surfaces = parse_skill_surfaces(
                skill_path.read_text(encoding="utf-8"), skill_path.parent.name
            )
        except ValueError as exc:
            all_errors.append(f"{skill_path.relative_to(REPO_ROOT)}: {exc}")
            continue
        paths = [skill_path, *sorted((skill_path.parent / "references").rglob("*.md"))]
        for path in paths:
            all_errors.extend(_lint_file(path, catalog, surfaces))
        files_count += len(paths)

    if all_errors:
        print("Skill reference validation FAILED:", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    print(f"Skill reference validation passed ({files_count} file(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
