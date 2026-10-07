#!/usr/bin/env python3
"""Generate ``docs/cli/reference.md`` from the ``pipefy`` command tree.

Run from the repository root:

    uv run python scripts/gen_cli_reference.py
"""

from __future__ import annotations

import importlib.util
import inspect
import re
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    import click

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = REPO_ROOT / "docs/cli/reference.md"

# Loaded by path, because a test loads this script by path and `scripts/` is not a package.
_footer_spec = importlib.util.spec_from_file_location(
    "doc_footer", Path(__file__).with_name("doc_footer.py")
)
if _footer_spec is None or _footer_spec.loader is None:
    raise ImportError("scripts/doc_footer.py not found")
_doc_footer = importlib.util.module_from_spec(_footer_spec)
_footer_spec.loader.exec_module(_doc_footer)

_RST_LITERAL_RE = re.compile(r"``([^`]+)``")
_RICH_MARKUP_RE = re.compile(r"\[/?[a-z ]+\]")


class Param(NamedTuple):
    name: str
    type: str
    default: str | None  # None means the parameter is required or has no default.
    required: bool
    description: str


class Command(NamedTuple):
    path: str
    summary: str
    params: tuple[Param, ...]


class Group(NamedTuple):
    path: str
    summary: str
    commands: tuple[Command, ...]


def summary_of(help_text: str | None) -> str:
    """The first paragraph of a help text, on one line, with RST literals as Markdown code."""
    if not help_text:
        return ""
    first_paragraph = inspect.cleandoc(help_text).split("\n\n", 1)[0]
    text = " ".join(line.strip() for line in first_paragraph.splitlines())
    text = _RICH_MARKUP_RE.sub("", text)
    return _RST_LITERAL_RE.sub(r"`\1`", text)


def _default_of(param: click.Parameter) -> str | None:
    default = param.default
    if param.required or default is None or callable(default):
        return None
    if isinstance(default, bool):
        return str(default).lower()
    if isinstance(default, (str, int, float)):
        return str(default)
    if isinstance(default, (list, tuple)) and not default:
        return None
    return None


def _param(param: click.Parameter) -> Param | None:
    import click

    if getattr(param, "hidden", False):
        return None
    if isinstance(param, click.Argument):
        name = param.human_readable_name.upper()
        kind = param.type.name.upper()
        description = getattr(param, "help", None) or ""
    else:
        options = [*param.opts, *param.secondary_opts]
        name = " / ".join(options)
        is_flag = getattr(param, "is_flag", False)
        kind = "flag" if is_flag else param.type.name.upper()
        description = getattr(param, "help", None) or ""
    return Param(
        name=name,
        type=kind,
        default=_default_of(param),
        required=param.required,
        description=summary_of(description),
    )


def _command(path: str, command: click.Command) -> Command:
    params = tuple(
        entry
        for entry in (_param(param) for param in command.params)
        if entry is not None and entry.name not in ("--help",)
    )
    return Command(path=path, summary=summary_of(command.help), params=params)


def collect_groups(root: click.Group) -> list[Group]:
    """One group per top-level command, holding every leaf command beneath it."""
    import click

    groups: list[Group] = []
    root_commands: list[Command] = []

    def leaves(path: str, command: click.Command) -> list[Command]:
        if isinstance(command, click.Group):
            return [
                leaf
                for name, child in sorted(command.commands.items())
                if not child.hidden
                for leaf in leaves(f"{path} {name}", child)
            ]
        return [_command(path, command)]

    for name, command in sorted(root.commands.items()):
        if command.hidden:
            continue
        if isinstance(command, click.Group):
            groups.append(
                Group(
                    path=f"pipefy {name}",
                    summary=summary_of(command.help),
                    commands=tuple(leaves(f"pipefy {name}", command)),
                )
            )
        else:
            root_commands.append(_command(f"pipefy {name}", command))
    if root_commands:
        groups.insert(
            0,
            Group(
                path="pipefy",
                summary="Top-level commands.",
                commands=tuple(root_commands),
            ),
        )
    return groups


def _cell(text: str) -> str:
    # A help text such as `"<slug>"` would otherwise render as an HTML tag.
    return text.replace("|", "\\|").replace("<", "&lt;")


def _render_command(command: Command) -> list[str]:
    lines = [f"### `{command.path}`", ""]
    if command.summary:
        lines += [command.summary, ""]
    if not command.params:
        return [*lines, "Takes no arguments or options.", ""]
    lines += [
        "| Argument or option | Type | Default | Description |",
        "|---|---|---|---|",
    ]
    for param in command.params:
        default = (
            "required"
            if param.required
            else (f"`{param.default}`" if param.default is not None else "")
        )
        lines.append(
            f"| `{_cell(param.name)}` | {_cell(param.type)} | {_cell(default)} "
            f"| {_cell(param.description)} |"
        )
    return [*lines, ""]


def render_reference(groups: list[Group], global_options: tuple[Param, ...]) -> str:
    lines = [
        "# CLI command reference",
        "",
        "<!-- Generated by scripts/gen_cli_reference.py from the command tree of the `pipefy` CLI. "
        "Do not edit by hand. -->",
        "",
        "Every command that `pipefy` registers, grouped by its top-level command. "
        "`pipefy <command> --help` prints the same text. "
        "[`README.md`](README.md) states the conventions every command shares, "
        "and [`../parity.md`](../parity.md) matches each command to its MCP tool.",
        "",
        "## Global options",
        "",
        "These options go before the command, as in `pipefy --token <token> pipe list`.",
        "",
        "| Option | Type | Default | Description |",
        "|---|---|---|---|",
    ]
    for param in global_options:
        default = f"`{param.default}`" if param.default is not None else ""
        lines.append(
            f"| `{_cell(param.name)}` | {_cell(param.type)} | {_cell(default)} "
            f"| {_cell(param.description)} |"
        )
    lines.append("")
    for group in groups:
        lines += [f"## `{group.path}`", ""]
        if group.summary:
            lines += [group.summary, ""]
        for command in group.commands:
            lines += _render_command(command)
    body = "\n".join(lines).rstrip("\n") + "\n"
    return _doc_footer.with_footer(body, str(REFERENCE.relative_to(REPO_ROOT)))


def collect() -> tuple[list[Group], tuple[Param, ...]]:
    """Read the registered command tree from the Typer app."""
    import typer.main
    from pipefy_cli.main import app

    root = typer.main.get_command(app)
    global_options = tuple(
        entry
        for entry in (_param(param) for param in root.params)
        if entry is not None
        and entry.name.split(" / ")[0]
        not in ("--help", "--install-completion", "--show-completion")
    )
    return collect_groups(root), global_options


def main() -> None:
    groups, global_options = collect()
    REFERENCE.write_text(render_reference(groups, global_options), encoding="utf-8")
    print(f"Wrote {REFERENCE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
