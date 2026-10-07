"""Every page under ``docs/`` ends with the feedback footer, and only an ADR record goes without it."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/doc_footer.py"
_spec = importlib.util.spec_from_file_location("doc_footer", _SCRIPT)
assert _spec and _spec.loader
_footer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_footer)


def test_with_footer_appends_the_footer_once():
    once = _footer.with_footer("# Page\n\nText.\n", "docs/page.md")
    assert once.endswith(_footer.footer("docs/page.md"))
    assert _footer.with_footer(once, "docs/page.md") == once


def test_with_footer_repairs_a_footer_that_names_another_page():
    moved = _footer.with_footer("# Page\n", "docs/old.md")
    assert _footer.with_footer(moved, "docs/new.md") == _footer.with_footer(
        "# Page\n", "docs/new.md"
    )


def test_adr_records_are_exempt_and_their_index_is_not():
    pages = _footer.pages()
    assert "docs/contributing/adr/README.md" in pages
    assert not any(page.startswith("docs/contributing/adr/0") for page in pages)


def test_every_docs_page_carries_the_footer():
    assert _footer.main([]) == 0
