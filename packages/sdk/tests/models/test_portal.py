"""Unit tests for portal Pydantic input models."""

from __future__ import annotations

import pytest
from _shared.fixture_ids import EXAMPLE_PIPE_REPO_ID
from pydantic import ValidationError

from pipefy_sdk.models.portal import (
    CreatePortalElementInput,
    DeletePortalElementInput,
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
        "automationButton",
        "contentBlock",
        "document",
    ],
)
def test_create_portal_element_input_accepts_all_interface_page_element_types(
    element_type: str,
) -> None:
    """InterfacePageElementType Literal must allow all 15 enum values."""
    element_input = CreatePortalElementInput(
        page_id=_PAGE_ID,
        type=element_type,  # type: ignore[arg-type]
        metadata={},
    )
    assert element_input.type == element_type


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
    )
    assert element_input.metadata["linkUrl"] == "https://example.com/pipefy"


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
