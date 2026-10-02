"""Pydantic models for Pipefy portal input validation."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from pipefy_sdk.models.validators import NonBlankStr

PortalVisibility = Literal["internal", "private", "public"]

PortalElementType = Literal[
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
]


def _validate_forms_metadata(metadata: dict[str, Any]) -> None:
    """Require non-empty ``name`` for forms elements (matches live stored shape)."""
    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "type 'forms' requires metadata.name (non-empty display name string). "
            "Pipe linkage uses data_sources (e.g. repoId) on create."
        )


def _validate_sub_portal_metadata(metadata: dict[str, Any]) -> None:
    """Allow empty metadata until wired via the Internal API; validate optional keys."""
    sub_portal_uuid = metadata.get("subPortalUuid")
    if sub_portal_uuid is None:
        return
    if not isinstance(sub_portal_uuid, str) or not sub_portal_uuid.strip():
        raise ValueError(
            "type 'subPortal': metadata.subPortalUuid must be a non-empty string "
            "when set."
        )


def _validate_link_metadata(metadata: dict[str, Any]) -> None:
    """Require non-empty ``linkName``; ``linkUrl`` optional but must be non-empty when set."""
    link_name = metadata.get("linkName")
    if not isinstance(link_name, str) or not link_name.strip():
        raise ValueError(
            "type 'link' requires metadata.linkName (non-empty label string)."
        )
    link_url = metadata.get("linkUrl")
    if link_url is None:
        return
    if not isinstance(link_url, str) or not link_url.strip():
        raise ValueError(
            "type 'link': metadata.linkUrl must be a non-empty URL string when set."
        )


def _validate_element_metadata(element_type: str, metadata: dict[str, Any]) -> None:
    """Dispatch metadata validation by ``InterfacePageElementType``."""
    if element_type == "forms":
        _validate_forms_metadata(metadata)
    elif element_type == "subPortal":
        _validate_sub_portal_metadata(metadata)
    elif element_type == "link":
        _validate_link_metadata(metadata)


class CreatePortalInput(BaseModel):
    """Input for creating or fetching the org's main portal via template flow."""

    organization_uuid: str | int = Field(
        description="Organization UUID or numeric organization id."
    )

    model_config = ConfigDict(extra="forbid")


class UpdatePortalInput(BaseModel):
    """Partial update payload for ``updateInterface`` (Interfaces schema)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    interface_uuid: str = Field(min_length=1)
    name: str | None = None
    visibility: PortalVisibility | None = None
    color: str | None = None
    icon: str | None = None
    display_pipefy_header: bool | None = Field(
        default=None, alias="displayPipefyHeader"
    )


_LAYOUT_ROW_REQUIREMENT = (
    "id (non-empty string), type 'row', and children (list of non-empty strings)"
)


class PortalPageLayoutRow(BaseModel):
    """One ``pages[].layout`` row."""

    model_config = ConfigDict(extra="allow")

    id: NonBlankStr
    type: Literal["row"]
    children: list[NonBlankStr]


def parse_portal_page_layout(layout: list[Any]) -> list[PortalPageLayoutRow]:
    """Parse ``layout`` into page rows; an empty list is an empty page.

    Rows keep keys besides ``id``, ``type``, and ``children`` for the write.
    """
    rows: list[PortalPageLayoutRow] = []
    for index, row in enumerate(layout):
        if isinstance(row, PortalPageLayoutRow):
            rows.append(row)
            continue
        if not isinstance(row, dict):
            raise ValueError(
                f"layout[{index}] must be an object with {_LAYOUT_ROW_REQUIREMENT}; "
                f"got {type(row).__name__}."
            )
        try:
            rows.append(PortalPageLayoutRow.model_validate(row))
        except ValidationError as exc:
            raise ValueError(
                f"layout[{index}] must have {_LAYOUT_ROW_REQUIREMENT}; got {row!r}."
            ) from exc
    return rows


def _parse_layout_list(value: object) -> object:
    """Parse a list with indexed row messages; leave other values to the list check."""
    return parse_portal_page_layout(value) if isinstance(value, list) else value


_PortalPageLayout = Annotated[
    list[PortalPageLayoutRow], BeforeValidator(_parse_layout_list)
]


class CreatePortalElementInput(BaseModel):
    """Validated input for ``createElement`` on the Interfaces schema."""

    model_config = ConfigDict(extra="forbid")

    page_id: NonBlankStr
    type: PortalElementType
    metadata: dict[str, Any]
    data_sources: list[dict[str, Any]] = Field(default_factory=list)
    element_id: NonBlankStr | None = Field(
        default=None,
        description="Optional client-provided element UUID (GraphQL input id).",
    )
    editable: bool | None = None
    layout: _PortalPageLayout | None = Field(
        default=None,
        description=(
            "Full page layout row array (get_portal pages[].layout) including a row "
            "whose children list element_id; omit to leave the page grid untouched."
        ),
    )

    @model_validator(mode="after")
    def validate_metadata_for_element_type(self) -> Self:
        if not isinstance(self.metadata, dict):
            raise ValueError(
                f"metadata must be a dict, got {type(self.metadata).__name__}."
            )
        _validate_element_metadata(self.type, self.metadata)
        return self

    @model_validator(mode="after")
    def validate_layout_places_element(self) -> Self:
        """``layout`` must reference the new element, or the write places nothing.

        The Interfaces API stores whatever JSON it receives in ``layout``; a row
        array that never lists ``element_id`` leaves the element outside the grid.
        """
        if self.layout is None:
            return self
        if self.element_id is None:
            raise ValueError(
                "layout requires element_id: generate a UUID, pass it as element_id, "
                "and list it in the children of one layout row."
            )
        for row in self.layout:
            if self.element_id in row.children:
                return self
        raise ValueError(
            "layout must contain a row whose children include element_id; "
            "otherwise the element is created outside the page grid."
        )


class DeletePortalElementInput(BaseModel):
    """Validated input for ``deleteElement`` on the Interfaces schema."""

    model_config = ConfigDict(extra="forbid")

    element_id: NonBlankStr
    page_id: NonBlankStr
    layout: _PortalPageLayout | None = Field(
        default=None,
        description=(
            "Full page layout row array (get_portal pages[].layout) with element_id "
            "removed from every row; omit to leave the page grid untouched."
        ),
    )

    @model_validator(mode="after")
    def validate_layout_drops_element(self) -> Self:
        """``layout`` must not list the deleted element.

        The API stores ``layout`` verbatim with the delete, so a row that still
        lists ``element_id`` leaves an orphan reference on the page.
        """
        if self.layout is None:
            return self
        for index, row in enumerate(self.layout):
            if self.element_id in row.children:
                raise ValueError(
                    f"layout[{index}] still lists element_id {self.element_id!r} in "
                    "children; remove it so no row references the deleted element."
                )
        return self


class UpdatePortalElementInput(BaseModel):
    """Validated input for ``updateElement`` (Interfaces schema).

    Pipefy treats ``metadata`` as a **full replace** on every update — callers must
    send the complete blob, not a partial patch. The ``type`` field is used only for
    client-side metadata validation and is not sent to GraphQL.
    """

    model_config = ConfigDict(extra="forbid")

    element_id: NonBlankStr
    page_id: NonBlankStr
    type: PortalElementType
    metadata: dict[str, Any]
    data_sources: list[dict[str, Any]] = Field(default_factory=list)
    editable: bool | None = None

    @model_validator(mode="after")
    def validate_metadata_for_element_type(self) -> Self:
        if not isinstance(self.metadata, dict):
            raise ValueError(
                f"metadata must be a dict, got {type(self.metadata).__name__}."
            )
        _validate_element_metadata(self.type, self.metadata)
        return self


__all__ = [
    "CreatePortalElementInput",
    "CreatePortalInput",
    "DeletePortalElementInput",
    "PortalElementType",
    "PortalPageLayoutRow",
    "PortalVisibility",
    "UpdatePortalElementInput",
    "UpdatePortalInput",
    "parse_portal_page_layout",
]
