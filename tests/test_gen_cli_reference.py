"""``docs/cli/reference.md`` is generated from the ``pipefy`` command tree and stays current."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import click

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts/gen_cli_reference.py"
_spec = importlib.util.spec_from_file_location("gen_cli_reference", _SCRIPT)
assert _spec and _spec.loader
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)


@click.group(help="Cards in a pipe.")
def _card():
    pass


@_card.command("get", help="Fetch one card (``get_card``).\n\nLonger text.")
@click.argument("card_id")
@click.option("--json", "-j", "as_json", is_flag=True, help="Print JSON.")
def _card_get(card_id, as_json):
    pass


@_card.command("ping", hidden=True)
def _card_ping():
    pass


@click.group()
def _root():
    pass


_root.add_command(_card, "card")


@_root.command("version", help="Print the version.")
def _version():
    pass


def test_summary_is_the_first_paragraph_with_literals_as_code():
    assert (
        _gen.summary_of("Fetch one (``get_card``).\n\nMore.")
        == "Fetch one (`get_card`)."
    )


def test_collect_groups_puts_root_commands_first_and_skips_hidden_ones():
    groups = _gen.collect_groups(_root)
    assert [group.path for group in groups] == ["pipefy", "pipefy card"]
    assert [command.path for command in groups[1].commands] == ["pipefy card get"]


def test_render_reference_writes_each_command_with_its_arguments_and_options():
    page = _gen.render_reference(_gen.collect_groups(_root), ())
    assert "### `pipefy card get`\n\nFetch one card (`get_card`).\n" in page
    assert "| `CARD_ID` | TEXT | required |  |" in page
    assert "| `--json / -j` | flag | `false` | Print JSON. |" in page
    assert (
        "### `pipefy version`\n\nPrint the version.\n\nTakes no arguments or options.\n"
        in page
    )


def test_committed_reference_matches_the_registered_commands():
    committed = (_ROOT / "docs/cli/reference.md").read_text(encoding="utf-8")
    assert committed == _gen.render_reference(*_gen.collect()), (
        "docs/cli/reference.md is stale. "
        "Run `uv run python scripts/gen_cli_reference.py`."
    )
