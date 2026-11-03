"""Pydantic models for Pipefy portal input validation."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Self, get_args

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    RootModel,
    ValidationError,
    model_validator,
)

from pipefy_sdk.models.validators import NonBlankStr, PipefyId

PortalVisibility = Literal["internal", "private", "public"]

PortalColor = Literal[
    "blue",
    "cyan",
    "gray",
    "green",
    "indigo",
    "lime",
    "pink",
    "purple",
    "orange",
    "red",
    "sky",
    "yellow",
]

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
    "customCode",
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


class CreateInterfaceInput(BaseModel):
    """Validated input for ``createInterface`` (Interfaces schema, plain creation).

    ``data_sources`` is validated separately as ``InterfaceDataSources``, not a
    field here: it has its own rules (uniqueness, a 10-source cap) independent
    of ``organization_uuid``/``name``.
    """

    model_config = ConfigDict(extra="forbid")

    organization_uuid: str | int = Field(
        description="Organization UUID or numeric organization id."
    )
    name: NonBlankStr
    color: PortalColor = "blue"


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

    ``data_sources`` is a full replace too, and the API rejects an update without
    it. Omitting it therefore needs ``portal_uuid``, so the element's current data
    sources (``repoId`` and ``fieldKeys``) and ``editable`` flag can be read and sent
    back; ``[]`` unlinks them all.
    """

    model_config = ConfigDict(extra="forbid")

    element_id: NonBlankStr
    page_id: NonBlankStr
    type: PortalElementType
    metadata: dict[str, Any]
    data_sources: list[dict[str, Any]] | None = None
    portal_uuid: NonBlankStr | None = Field(
        default=None,
        description=(
            "Portal holding the element; required when data_sources is omitted, "
            "to keep the element's current data sources and editable flag."
        ),
    )
    editable: bool | None = None

    @model_validator(mode="after")
    def validate_metadata_for_element_type(self) -> Self:
        if not isinstance(self.metadata, dict):
            raise ValueError(
                f"metadata must be a dict, got {type(self.metadata).__name__}."
            )
        _validate_element_metadata(self.type, self.metadata)
        return self

    @model_validator(mode="after")
    def validate_data_sources_can_be_kept(self) -> Self:
        """Omitted ``data_sources`` must come with ``portal_uuid`` to read them back.

        The update replaces the element's data sources with the list it sends, so
        sending ``[]`` for an omitted list would unlink the element from its pipe or
        table.
        """
        if self.data_sources is None and self.portal_uuid is None:
            raise ValueError(
                "Pass portal_uuid to keep the element's current data sources, or "
                "data_sources to replace them ([] unlinks them all)."
            )
        return self


MAX_DATA_SOURCE_FIELD_KEYS = 30
MAX_CUSTOM_CODE_DATA_SOURCES = 10

# Keys a read returns that the update input does not take.
_READ_ONLY_DATA_SOURCE_KEYS = frozenset({"repoName", "repoType"})


def _decode_json_string(value: object) -> object:
    """Decode a Json value read back as a string; a non-JSON string stays for the type check."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


class InterfaceDataSource(BaseModel):
    """One data source of an HTML interface's ``customCode`` element.

    ``id`` is the handle the element's HTML reads the source by and ``name`` its
    label; both are unique within the element. ``field_keys`` lists custom field
    uuids and built-in keys such as ``title``. ``filters`` is a filter tree, as
    ``get_interface_html_guidelines`` describes it, or ``None``. A source read from
    ``get_html_interface`` can be passed back as read: ``repoName`` and ``repoType``
    are dropped, and ``filters`` read as a JSON string is decoded.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: NonBlankStr
    name: NonBlankStr
    repo_id: NonBlankStr = Field(alias="repoId")
    field_keys: list[NonBlankStr] = Field(
        alias="fieldKeys", min_length=1, max_length=MAX_DATA_SOURCE_FIELD_KEYS
    )
    filters: Annotated[dict[str, Any] | None, BeforeValidator(_decode_json_string)] = (
        None
    )

    @model_validator(mode="before")
    @classmethod
    def drop_read_only_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                key: value
                for key, value in data.items()
                if key not in _READ_ONLY_DATA_SOURCE_KEYS
            }
        return data


class InterfaceDataSources(RootModel[list[InterfaceDataSource]]):
    """The complete data source list of an HTML interface's ``customCode`` element.

    At most 10 sources, each with its own ``id`` and ``name``; ``[]`` is an
    element with no sources.
    """

    root: list[InterfaceDataSource] = Field(max_length=MAX_CUSTOM_CODE_DATA_SOURCES)

    @model_validator(mode="after")
    def ids_and_names_are_unique(self) -> Self:
        for attribute in ("id", "name"):
            values = [getattr(source, attribute) for source in self.root]
            repeated = sorted({value for value in values if values.count(value) > 1})
            if repeated:
                msg = (
                    f"Each data source needs its own {attribute}; "
                    f"repeated: {', '.join(repeated)}."
                )
                raise ValueError(msg)
        return self


MAX_CUSTOM_CODE_ACTIONS = 50

# NOTE: ASCII classes on purpose: Python's \w also matches non-ASCII letters,
# which the API's actionId rule rejects.
_ACTION_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
_AUTOMATION_ID_PATTERN = r"^[0-9]+$"


class _InterfaceAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    action_id: str = Field(alias="actionId", pattern=_ACTION_ID_PATTERN)


class OpenStartFormAction(_InterfaceAction):
    """Opens the start form of ``repo_id``, the repo of one of the element's sources."""

    kind: Literal["openStartForm"]
    repo_id: NonBlankStr = Field(alias="repoId")


class OpenRecordAction(_InterfaceAction):
    """Opens a record of source ``source_id``, in a modal (the default) or on a page.

    ``field_keys`` picks the fields the modal shows, from the source's own
    ``fieldKeys``. ``display="page"`` needs ``page_id``, a record layout page of
    the interface for the source's repo.
    """

    kind: Literal["openRecord"]
    source_id: NonBlankStr = Field(alias="sourceId")
    display: Literal["modal", "page"] | None = None
    field_keys: list[NonBlankStr] | None = Field(default=None, alias="fieldKeys")
    page_id: NonBlankStr | None = Field(default=None, alias="pageId")

    @model_validator(mode="after")
    def page_display_names_its_page(self) -> Self:
        if self.display == "page" and self.page_id is None:
            msg = (
                f"Action {self.action_id} opens the record on a page, so it needs "
                "a pageId: a record layout page of this interface for the "
                "source's repo."
            )
            raise ValueError(msg)
        return self


class TriggerAutomationAction(_InterfaceAction):
    """Runs ``automation_ids`` on a record of source ``source_id``.

    Each id is a manually triggered automation of the source's repo, as a string of
    digits.
    """

    kind: Literal["triggerAutomation"]
    source_id: NonBlankStr = Field(alias="sourceId")
    automation_ids: list[Annotated[PipefyId, Field(pattern=_AUTOMATION_ID_PATTERN)]] = (
        Field(alias="automationIds", min_length=1)
    )
    label: str | None = None


InterfaceAction = Annotated[
    OpenStartFormAction | OpenRecordAction | TriggerAutomationAction,
    Field(discriminator="kind"),
]

INTERFACE_ACTION_KINDS: tuple[str, ...] = tuple(
    kind
    for action in (OpenStartFormAction, OpenRecordAction, TriggerAutomationAction)
    for kind in get_args(action.model_fields["kind"].annotation)
)


class InterfaceActions(RootModel[list[InterfaceAction]]):
    """The complete action list of an HTML interface's ``customCode`` element.

    The element's HTML runs an action with ``data-pfy-action="<actionId>"``. At
    most 50 actions, each with its own ``actionId``; ``[]`` is an element with
    no actions.
    """

    root: list[InterfaceAction] = Field(max_length=MAX_CUSTOM_CODE_ACTIONS)

    @model_validator(mode="after")
    def action_ids_are_unique(self) -> Self:
        ids = [action.action_id for action in self.root]
        repeated = sorted({value for value in ids if ids.count(value) > 1})
        if repeated:
            msg = (
                f"Each action needs its own actionId; repeated: {', '.join(repeated)}."
            )
            raise ValueError(msg)
        return self


__all__ = [
    "INTERFACE_ACTION_KINDS",
    "MAX_CUSTOM_CODE_ACTIONS",
    "MAX_CUSTOM_CODE_DATA_SOURCES",
    "MAX_DATA_SOURCE_FIELD_KEYS",
    "CreatePortalElementInput",
    "CreatePortalInput",
    "DeletePortalElementInput",
    "InterfaceAction",
    "InterfaceActions",
    "InterfaceDataSource",
    "InterfaceDataSources",
    "OpenRecordAction",
    "OpenStartFormAction",
    "PortalColor",
    "PortalElementType",
    "PortalPageLayoutRow",
    "PortalVisibility",
    "TriggerAutomationAction",
    "UpdatePortalElementInput",
    "UpdatePortalInput",
    "parse_portal_page_layout",
]
