"""Unit tests for portal Pydantic input models."""

from __future__ import annotations

import json
from typing import get_args

import pytest
from _shared.fixture_ids import EXAMPLE_PIPE_REPO_ID
from pydantic import ValidationError

from pipefy_sdk.models.portal import (
    CreatePortalElementInput,
    DeletePortalElementInput,
    InterfaceDataSource,
    InterfaceDataSources,
    PortalElementType,
    UpdatePortalElementInput,
    UpdatePortalInput,
)

_PORTAL_UUID = "portal-created-uuid"
_PAGE_ID = "page-uuid-1"
_ELEMENT_ID = "el-uuid-1"

_VALID_FORMS_METADATA = {"name": "Request form", "defaultValues": {}}
_VALID_FORMS_DATA_SOURCES = [{"repoId": EXAMPLE_PIPE_REPO_ID}]
_VALID_LINK_METADATA = {
    "linkName": "Open Pipefy",
    "linkUrl": "https://example.com/pipefy",
}
_VALID_LINK_METADATA_NAME_ONLY = {
    "linkName": "Open Pipefy",
    "gridMap": {"height": 64, "columns": 4, "minColumns": 4},
}
_VALID_SUB_PORTAL_METADATA: dict[str, str] = {}


@pytest.mark.unit
def test_create_portal_element_input_accepts_forms_with_data_sources() -> None:
    """forms elements require name; optional data_sources mirrors createElement input."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type="forms",
        metadata=_VALID_FORMS_METADATA,
        data_sources=_VALID_FORMS_DATA_SOURCES,
    )
    assert element_input.type == "forms"
    assert element_input.metadata["name"] == "Request form"
    assert element_input.data_sources == _VALID_FORMS_DATA_SOURCES


@pytest.mark.unit
def test_create_portal_element_input_accepts_sub_portal_type() -> None:
    """subPortal create validates metadata shape (empty until wired via the Internal API)."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type="subPortal",
        metadata=_VALID_SUB_PORTAL_METADATA,
    )
    assert element_input.type == "subPortal"
    assert element_input.metadata == {}


@pytest.mark.unit
def test_create_portal_element_input_accepts_link_metadata() -> None:
    """link elements require linkName; linkUrl is optional (live stored shape)."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type="link",
        metadata=_VALID_LINK_METADATA,
    )
    assert element_input.metadata["linkName"] == "Open Pipefy"
    assert element_input.metadata["linkUrl"] == "https://example.com/pipefy"


@pytest.mark.unit
def test_create_portal_element_input_accepts_link_metadata_with_name_only() -> None:
    """Template links often expose only linkName + gridMap on read."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type="link",
        metadata=_VALID_LINK_METADATA_NAME_ONLY,
    )
    assert element_input.metadata["linkName"] == "Open Pipefy"


@pytest.mark.unit
@pytest.mark.parametrize(
    "element_type",
    [
        "text",
        "table",
        "field",
        "embedLink",
        "embedVideo",
        "embedImage",
        "button",
        "divider",
        "pages",
        "subPortal",
        "automationButton",
        "contentBlock",
        "document",
        "customCode",
    ],
)
def test_create_portal_element_input_accepts_all_interface_page_element_types(
    element_type: str,
) -> None:
    """Every element type that accepts empty metadata validates."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type=element_type,  # type: ignore[arg-type]
        metadata={},
    )
    assert element_input.type == element_type


@pytest.mark.unit
def test_portal_element_type_lists_every_interface_page_element_type() -> None:
    assert set(get_args(PortalElementType)) == {
        "text",
        "table",
        "field",
        "embedLink",
        "embedVideo",
        "embedImage",
        "button",
        "divider",
        "link",
        "forms",
        "pages",
        "subPortal",
        "automationButton",
        "contentBlock",
        "document",
        "customCode",
    }


@pytest.mark.unit
def test_create_portal_element_input_rejects_unknown_element_type() -> None:
    with pytest.raises(ValidationError, match="type"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="pipe",  # type: ignore[arg-type]
            metadata={},
        )


@pytest.mark.unit
def test_create_portal_element_input_rejects_forms_metadata_missing_name() -> None:
    with pytest.raises(ValidationError, match="name"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="forms",
            metadata={},
        )


@pytest.mark.unit
@pytest.mark.parametrize("name", ["", "   "])
def test_create_portal_element_input_rejects_blank_forms_name(name: str) -> None:
    with pytest.raises(ValidationError, match="name"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="forms",
            metadata={"name": name},
        )


@pytest.mark.unit
def test_create_portal_element_input_rejects_link_metadata_missing_link_name() -> None:
    with pytest.raises(ValidationError, match="linkName"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata={"linkUrl": "https://example.com"},
        )


@pytest.mark.unit
@pytest.mark.parametrize("link_url", ["", "   "])
def test_create_portal_element_input_rejects_blank_link_url(link_url: str) -> None:
    with pytest.raises(ValidationError, match="linkUrl"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata={"linkUrl": link_url, "linkName": "Label"},
        )


@pytest.mark.unit
@pytest.mark.parametrize("link_name", ["", "   "])
def test_create_portal_element_input_rejects_blank_link_name(link_name: str) -> None:
    with pytest.raises(ValidationError, match="linkName"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata={"linkUrl": "https://example.com", "linkName": link_name},
        )


@pytest.mark.unit
def test_create_portal_element_input_rejects_blank_page_id() -> None:
    with pytest.raises(ValidationError, match="page_id"):
        CreatePortalElementInput(
            page_id="   ",
            type="text",
            metadata={},
        )


@pytest.mark.unit
def test_update_portal_element_input_accepts_forms_metadata() -> None:
    element_input = UpdatePortalElementInput(
        element_id=_ELEMENT_ID,
        page_id=_PAGE_ID,
        type="forms",
        metadata=_VALID_FORMS_METADATA,
        data_sources=_VALID_FORMS_DATA_SOURCES,
    )
    assert element_input.metadata["name"] == "Request form"


@pytest.mark.unit
def test_update_portal_element_input_accepts_link_metadata() -> None:
    element_input = UpdatePortalElementInput(
        element_id=_ELEMENT_ID,
        page_id=_PAGE_ID,
        type="link",
        metadata=_VALID_LINK_METADATA,
        data_sources=[],
    )
    assert element_input.metadata["linkUrl"] == "https://example.com/pipefy"


@pytest.mark.unit
def test_update_portal_element_input_accepts_portal_uuid_without_data_sources() -> None:
    """Omitted data_sources with portal_uuid means: keep the element's current ones."""
    element_input = UpdatePortalElementInput(
        element_id=_ELEMENT_ID,
        page_id=_PAGE_ID,
        type="forms",
        metadata=_VALID_FORMS_METADATA,
        portal_uuid=_PORTAL_UUID,
    )
    assert element_input.data_sources is None
    assert element_input.portal_uuid == _PORTAL_UUID


@pytest.mark.unit
def test_update_portal_element_input_rejects_missing_data_sources_and_portal_uuid() -> (
    None
):
    """Without either one, an update would unlink the element's data sources."""
    with pytest.raises(ValidationError, match="portal_uuid"):
        UpdatePortalElementInput(
            element_id=_ELEMENT_ID,
            page_id=_PAGE_ID,
            type="forms",
            metadata=_VALID_FORMS_METADATA,
        )


@pytest.mark.unit
def test_update_portal_element_input_rejects_blank_portal_uuid() -> None:
    with pytest.raises(ValidationError, match="portal_uuid"):
        UpdatePortalElementInput(
            element_id=_ELEMENT_ID,
            page_id=_PAGE_ID,
            type="forms",
            metadata=_VALID_FORMS_METADATA,
            portal_uuid="   ",
        )


@pytest.mark.unit
def test_update_portal_element_input_rejects_blank_element_id() -> None:
    with pytest.raises(ValidationError, match="element_id"):
        UpdatePortalElementInput(
            element_id="   ",
            page_id=_PAGE_ID,
            type="link",
            metadata=_VALID_LINK_METADATA,
        )


@pytest.mark.unit
def test_update_portal_element_input_rejects_invalid_link_metadata() -> None:
    with pytest.raises(ValidationError, match="linkName"):
        UpdatePortalElementInput(
            element_id=_ELEMENT_ID,
            page_id=_PAGE_ID,
            type="link",
            metadata={},
        )


@pytest.mark.unit
def test_update_portal_input_dump_uses_camel_case_for_display_pipefy_header() -> None:
    """Interfaces schema expects displayPipefyHeader, not display_pipefy_header."""
    portal_input = UpdatePortalInput(
        interface_uuid=_PORTAL_UUID,
        name="Renamed",
        visibility="public",
        color="#112233",
        icon="star",
        display_pipefy_header=False,
    )
    dumped = portal_input.model_dump(
        exclude_unset=True,
        exclude_none=True,
        by_alias=True,
    )
    assert dumped == {
        "interface_uuid": _PORTAL_UUID,
        "name": "Renamed",
        "visibility": "public",
        "color": "#112233",
        "icon": "star",
        "displayPipefyHeader": False,
    }
    assert "display_pipefy_header" not in dumped


@pytest.mark.unit
def test_update_portal_input_rejects_invalid_visibility() -> None:
    """visibility is validated by Pydantic Literal before GraphQL."""
    with pytest.raises(ValidationError):
        UpdatePortalInput(
            interface_uuid=_PORTAL_UUID,
            visibility="public_visibility",  # type: ignore[arg-type]
        )


_LAYOUT_ROWS = [
    {"id": "row-1", "type": "row", "children": ["el-existing"]},
    {"id": "row-2", "type": "row", "children": [_ELEMENT_ID]},
]


@pytest.mark.unit
def test_create_portal_element_input_accepts_layout_rows_placing_element() -> None:
    """layout is the page row array; the row listing element_id is what places it."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type="link",
        metadata=_VALID_LINK_METADATA,
        element_id=_ELEMENT_ID,
        layout=_LAYOUT_ROWS,
    )
    assert [row.model_dump() for row in element_input.layout] == _LAYOUT_ROWS


@pytest.mark.unit
def test_create_portal_element_input_rejects_object_layout() -> None:
    """The API stores an object wrapper verbatim, so it has to be rejected locally."""
    with pytest.raises(ValidationError):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata=_VALID_LINK_METADATA,
            element_id=_ELEMENT_ID,
            layout={"rows": _LAYOUT_ROWS},
        )


@pytest.mark.unit
def test_create_portal_element_input_rejects_layout_without_element_id() -> None:
    with pytest.raises(ValidationError, match="element_id"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata=_VALID_LINK_METADATA,
            layout=_LAYOUT_ROWS,
        )


@pytest.mark.unit
def test_create_portal_element_input_rejects_layout_that_omits_the_element() -> None:
    with pytest.raises(ValidationError, match="children include element_id"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata=_VALID_LINK_METADATA,
            element_id="el-not-in-layout",
            layout=_LAYOUT_ROWS,
        )


@pytest.mark.unit
def test_create_portal_element_input_rejects_empty_layout_array() -> None:
    """An empty array places nothing, so create still requires a row for element_id."""
    with pytest.raises(ValidationError, match="children include element_id"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata=_VALID_LINK_METADATA,
            element_id=_ELEMENT_ID,
            layout=[],
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "layout",
    [
        [{"children": [_ELEMENT_ID]}],
        [{"id": "row-1", "children": [_ELEMENT_ID]}],
        [{"id": "row-1", "type": "column", "children": [_ELEMENT_ID]}],
        [{"id": "row-1", "type": "row", "children": [1]}],
        [{"id": " ", "type": "row", "children": [_ELEMENT_ID]}],
        [{"id": "row-1", "type": "row", "children": [" "]}],
    ],
)
def test_create_portal_element_input_rejects_malformed_layout_rows(
    layout: list[dict[str, object]],
) -> None:
    """A complete write replaces the grid, so a partial row must not be stored."""
    with pytest.raises(ValidationError, match="type 'row'"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata=_VALID_LINK_METADATA,
            element_id=_ELEMENT_ID,
            layout=layout,
        )


@pytest.mark.unit
def test_create_portal_element_input_keeps_unknown_layout_keys() -> None:
    """Rows copied from get_portal may carry keys besides id, type, and children."""
    row = {
        "id": "row-1",
        "type": "row",
        "children": [_ELEMENT_ID],
        "minHeight": 2,
    }
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type="link",
        metadata=_VALID_LINK_METADATA,
        element_id=_ELEMENT_ID,
        layout=[dict(row)],
    )
    assert [row.model_dump() for row in element_input.layout] == [row]


@pytest.mark.unit
def test_create_portal_element_input_strips_padded_layout_ids() -> None:
    """A padded id still places the element, and id and row match once stripped."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type="link",
        metadata=_VALID_LINK_METADATA,
        element_id=f" {_ELEMENT_ID} ",
        layout=[{"id": " row-1 ", "type": "row", "children": [f" {_ELEMENT_ID} "]}],
    )
    assert element_input.element_id == _ELEMENT_ID
    assert [row.model_dump() for row in element_input.layout] == [
        {"id": "row-1", "type": "row", "children": [_ELEMENT_ID]}
    ]


@pytest.mark.unit
def test_create_portal_element_input_rejects_blank_element_id() -> None:
    with pytest.raises(ValidationError, match="element_id"):
        CreatePortalElementInput(
            page_id=_PAGE_ID,
            type="link",
            metadata=_VALID_LINK_METADATA,
            element_id="   ",
        )


_PRUNED_LAYOUT = [
    {"id": "row-1", "type": "row", "children": ["el-existing"]},
    {"id": "row-2", "type": "row", "children": []},
]


@pytest.mark.unit
def test_delete_portal_element_input_accepts_layout_without_the_element() -> None:
    delete_input = DeletePortalElementInput(
        element_id=_ELEMENT_ID, page_id=_PAGE_ID, layout=_PRUNED_LAYOUT
    )
    assert [row.model_dump() for row in delete_input.layout] == _PRUNED_LAYOUT


@pytest.mark.unit
def test_delete_portal_element_input_leaves_layout_unset_by_default() -> None:
    assert (
        DeletePortalElementInput(element_id=_ELEMENT_ID, page_id=_PAGE_ID).layout
        is None
    )


@pytest.mark.unit
def test_delete_portal_element_input_rejects_layout_still_listing_the_element() -> None:
    """The layout is stored with the delete, so a leftover child is an orphan ref."""
    with pytest.raises(ValidationError, match=r"layout\[1\] still lists element_id"):
        DeletePortalElementInput(
            element_id=_ELEMENT_ID, page_id=_PAGE_ID, layout=_LAYOUT_ROWS
        )


@pytest.mark.unit
def test_delete_portal_element_input_rejects_padded_leftover_child() -> None:
    with pytest.raises(ValidationError, match="still lists element_id"):
        DeletePortalElementInput(
            element_id=_ELEMENT_ID,
            page_id=_PAGE_ID,
            layout=[{"id": "row-1", "type": "row", "children": [f" {_ELEMENT_ID} "]}],
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "layout",
    [
        [{"children": []}],
        [{"id": "row-1", "type": "column", "children": []}],
        [{"id": "row-1", "type": "row", "children": [1]}],
    ],
)
def test_delete_portal_element_input_rejects_malformed_layout_rows(
    layout: list[dict[str, object]],
) -> None:
    with pytest.raises(ValidationError, match="type 'row'"):
        DeletePortalElementInput(
            element_id=_ELEMENT_ID, page_id=_PAGE_ID, layout=layout
        )


@pytest.mark.unit
def test_delete_portal_element_input_rejects_object_layout() -> None:
    with pytest.raises(ValidationError):
        DeletePortalElementInput(
            element_id=_ELEMENT_ID,
            page_id=_PAGE_ID,
            layout={"rows": _PRUNED_LAYOUT},
        )


_FIELD_UUID = "6a850d1c-0000-4000-8000-000000000016"
_OPEN_FILTER = {
    "id": "root",
    "type": "root",
    "conjunction": "and",
    "filterSet": [
        {"id": "leaf", "columnName": "title", "operator": "not_empty", "value": None}
    ],
}


def _source(**overrides: object) -> dict[str, object]:
    return {
        "id": "open-requests",
        "name": "Open requests",
        "repoId": EXAMPLE_PIPE_REPO_ID,
        "fieldKeys": ["title", _FIELD_UUID],
        **overrides,
    }


@pytest.mark.unit
def test_interface_data_source_reads_api_keys_and_snake_case_keys() -> None:
    camel = InterfaceDataSource.model_validate(_source())
    snake = InterfaceDataSource.model_validate(
        {
            "id": "open-requests",
            "name": "Open requests",
            "repo_id": EXAMPLE_PIPE_REPO_ID,
            "field_keys": ["title", _FIELD_UUID],
        }
    )

    assert camel == snake
    assert camel.repo_id == EXAMPLE_PIPE_REPO_ID
    assert camel.field_keys == ["title", _FIELD_UUID]
    assert camel.filters is None


@pytest.mark.unit
def test_interface_data_source_decodes_filters_read_back_as_json() -> None:
    """A source read from the API carries its filter tree as a JSON string."""
    source = InterfaceDataSource.model_validate(
        _source(filters=json.dumps(_OPEN_FILTER))
    )

    assert source.filters == _OPEN_FILTER


@pytest.mark.unit
def test_interface_data_source_drops_the_read_only_repo_name_and_type() -> None:
    """A source from get_html_interface can be sent back as it was read."""
    source = InterfaceDataSource.model_validate(
        _source(repoName="Requests", repoType="Pipe")
    )

    assert source == InterfaceDataSource.model_validate(_source())


@pytest.mark.unit
@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "  "},
        {"name": ""},
        {"repoId": ""},
        {"fieldKeys": []},
        {"fieldKeys": [" "]},
        {"fieldKeys": [f"key-{index}" for index in range(31)]},
        {"filters": ["not", "an", "object"]},
        {"filters": "not json"},
        {"filter": _OPEN_FILTER},
    ],
)
def test_interface_data_source_rejects_what_the_api_would_reject(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        InterfaceDataSource.model_validate(_source(**overrides))


@pytest.mark.unit
def test_interface_data_source_takes_thirty_field_keys() -> None:
    keys = [f"key-{index}" for index in range(30)]

    assert (
        InterfaceDataSource.model_validate(_source(fieldKeys=keys)).field_keys == keys
    )


@pytest.mark.unit
@pytest.mark.parametrize("missing", ["id", "name", "repoId", "fieldKeys"])
def test_interface_data_source_requires_handle_label_repo_and_keys(
    missing: str,
) -> None:
    source = _source()
    del source[missing]

    with pytest.raises(ValidationError):
        InterfaceDataSource.model_validate(source)


@pytest.mark.unit
def test_interface_data_sources_takes_ten_sources() -> None:
    sources = [_source(id=f"s{index}", name=f"S {index}") for index in range(10)]

    assert len(InterfaceDataSources.model_validate(sources).root) == 10


@pytest.mark.unit
def test_interface_data_sources_takes_an_empty_list() -> None:
    assert InterfaceDataSources.model_validate([]).root == []


@pytest.mark.unit
def test_interface_data_sources_rejects_an_eleventh_source() -> None:
    sources = [_source(id=f"s{index}", name=f"S {index}") for index in range(11)]

    with pytest.raises(ValidationError, match="at most 10"):
        InterfaceDataSources.model_validate(sources)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("second", "message"),
    [
        ({"name": "Closed requests"}, "own id; repeated: open-requests"),
        ({"id": "closed-requests"}, "own name; repeated: Open requests"),
    ],
)
def test_interface_data_sources_rejects_a_repeated_id_or_name(
    second: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        InterfaceDataSources.model_validate([_source(), _source(**second)])
