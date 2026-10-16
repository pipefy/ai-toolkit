"""Tests for shared Pipefy service types and helpers."""

from typing import cast

import pytest
from pydantic import TypeAdapter, ValidationError

from pipefy_sdk.services.types import (
    CardSearch,
    RecordFilter,
    RecordOrder,
    copy_card_search,
    validate_record_filter,
)


@pytest.mark.unit
def test_copy_card_search_preserves_defined_keys():
    src: CardSearch = {"title": "x", "include_done": True}
    assert copy_card_search(src) == {"title": "x", "include_done": True}


@pytest.mark.unit
def test_copy_card_search_strips_keys_not_on_card_search():
    """Unknown keys (e.g. from a loose MCP payload) must not reach the client."""
    loose = {"title": "x", "not_a_card_search_field": 99, "assignee_ids": ["1"]}
    out = copy_card_search(cast(CardSearch, loose))
    assert out == {"title": "x", "assignee_ids": ["1"]}
    assert "not_a_card_search_field" not in out


_FIELD_UUID = "00000000-0000-4000-8000-0000000000aa"


@pytest.mark.unit
def test_record_filter_json_schema_resolves_recursion():
    schema = TypeAdapter(RecordFilter).json_schema()
    props = schema["$defs"]["RecordFilter"]["properties"]
    assert "and" in props
    assert "field" in props


@pytest.mark.unit
def test_validate_record_filter_accepts_field_uuid():
    validate_record_filter({"and": [{"field": _FIELD_UUID, "eq": "x"}]})


@pytest.mark.unit
@pytest.mark.parametrize(
    "where",
    [
        {"field": "total_value", "eq": "x"},
        {"and": [{"attribute": "TITLE", "eq": "a"}, {"field": "total_value"}]},
        {"or": [{"and": [{"field": "total_value", "eq": 1}]}]},
    ],
)
def test_validate_record_filter_rejects_slug_anywhere(where):
    with pytest.raises(ValueError, match="uuid.*'total_value'"):
        validate_record_filter(cast(RecordFilter, where))


@pytest.mark.unit
@pytest.mark.parametrize(
    "where",
    [
        {"attribute": "TITLE", "bogus_op": "x"},
        {"AND": [{"attribute": "TITLE", "eq": "a"}]},
        {"attribute": "FINISHED_AT", "between": {"min": 1, "max": 2, "x": 3}},
    ],
)
def test_record_filter_rejects_unknown_keys(where):
    with pytest.raises(ValidationError, match="extra"):
        TypeAdapter(RecordFilter).validate_python(where)


@pytest.mark.unit
def test_record_order_rejects_unknown_keys():
    with pytest.raises(ValidationError, match="extra"):
        TypeAdapter(RecordOrder).validate_python({"attribute": "TITLE", "dir": "ASC"})


@pytest.mark.unit
def test_record_filter_json_schema_forbids_additional_properties():
    defs = TypeAdapter(RecordFilter).json_schema()["$defs"]
    assert defs["RecordFilter"]["additionalProperties"] is False
    assert defs["RecordRange"]["additionalProperties"] is False


@pytest.mark.unit
@pytest.mark.parametrize(
    "where",
    [
        {"and": ["x"]},
        {"and": {"field": "total_value"}},
        {"or": "x"},
        {"and": [None, 1, {"attribute": "TITLE", "eq": "a"}]},
    ],
)
def test_validate_record_filter_leaves_malformed_shapes_to_the_api(where):
    validate_record_filter(cast(RecordFilter, where))


@pytest.mark.unit
def test_validate_record_filter_still_checks_fields_beside_malformed_nodes():
    with pytest.raises(ValueError, match="'total_value'"):
        validate_record_filter(
            cast(RecordFilter, {"and": ["x", {"field": "total_value", "eq": 1}]})
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    [
        _FIELD_UUID.replace("-", ""),
        "{" + _FIELD_UUID + "}",
        "urn:uuid:" + _FIELD_UUID,
        " " + _FIELD_UUID + " ",
        _FIELD_UUID.upper(),
    ],
)
def test_validate_record_filter_rejects_non_canonical_uuids(field):
    with pytest.raises(ValueError, match="lowercase with hyphens"):
        validate_record_filter({"field": field, "eq": "x"})
