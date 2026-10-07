"""Each decision record carries a valid status header, and the index states the same status."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ADR_DIR = Path(__file__).resolve().parents[1] / "docs/contributing/adr"
_STATUS_RE = re.compile(
    r"^Status: (Proposed|Accepted|Superseded by ADR-\d{4})$", re.MULTILINE
)
_TARGET_RE = re.compile(r"^Target release: (none|v?\d+\.\d+\.\d+\S*)$", re.MULTILINE)
_INDEX_ROW_RE = re.compile(
    r"^\| \[(\d{4})\]\((\d{4}-[a-z0-9-]+\.md)\) \|[^|]*\| ([^|]+?) \|", re.MULTILINE
)

_RECORDS = sorted(_ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md"))


def _index_rows() -> dict[str, tuple[str, str]]:
    index = (_ADR_DIR / "README.md").read_text(encoding="utf-8")
    return {
        number: (file, status) for number, file, status in _INDEX_ROW_RE.findall(index)
    }


@pytest.mark.parametrize("record", _RECORDS, ids=lambda path: path.name)
def test_record_declares_status_and_target_release(record: Path) -> None:
    text = record.read_text(encoding="utf-8")
    assert _STATUS_RE.search(text), "missing or invalid `Status:` line"
    assert _TARGET_RE.search(text), "missing or invalid `Target release:` line"


@pytest.mark.parametrize("record", _RECORDS, ids=lambda path: path.name)
def test_index_row_matches_record_status(record: Path) -> None:
    status = _STATUS_RE.search(record.read_text(encoding="utf-8"))
    assert status
    rows = _index_rows()
    number = record.name[:4]
    assert number in rows, f"ADR-{number} has no row in adr/README.md"
    assert rows[number] == (record.name, status.group(1))


def test_index_lists_no_record_that_does_not_exist() -> None:
    assert {file for file, _ in _index_rows().values()} == {
        record.name for record in _RECORDS
    }
