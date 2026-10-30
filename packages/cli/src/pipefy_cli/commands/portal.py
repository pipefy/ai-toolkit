"""Portal subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

import typer
from pipefy_sdk import (
    CreatePortalElementInput,
    PipefyClient,
    PipefyGraphQLError,
    UpdatePortalElementInput,
)
from pipefy_sdk.exceptions import (
    HtmlValidationError,
    PipefyError,
    PortalPermissionError,
)
from pipefy_sdk.models.portal import (
    DeletePortalElementInput,
    InterfaceActions,
    InterfaceDataSources,
    PortalColor,
    PortalPageLayoutRow,
    parse_portal_page_layout,
)
from pydantic import ValidationError

from pipefy_cli.commands._common import (
    ID_POSITIONAL_CONTEXT_SETTINGS,
    confirm_destructive,
    parse_json_object,
    parse_json_value,
    resource_id_argument,
    run_cli_command,
    validate_optional_resource_id,
)

portal_app = typer.Typer(help="Portal operations.", no_args_is_help=True)
page_app = typer.Typer(help="Portal page operations.", no_args_is_help=True)
layout_app = typer.Typer(help="Portal page layout.", no_args_is_help=True)
element_app = typer.Typer(
    help="Portal page elements (widgets / tools in the Pipefy UI).",
    no_args_is_help=True,
)
sub_portal_app = typer.Typer(
    help="Sub-portal create, attach, publish, and delete.",
    no_args_is_help=True,
)
html_interface_app = typer.Typer(
    help="HTML interfaces (contentModeHtml): create, read, and rewrite customCode pages.",
    no_args_is_help=True,
)


def _require_non_empty_portal_uuid(portal_uuid: str) -> str:
    """Reject blank portal UUIDs before SDK calls."""
    if not portal_uuid.strip():
        raise typer.BadParameter("Portal UUID must be non-empty.")
    return portal_uuid.strip()


_MAX_TEXT_OPTION_FILE_BYTES = 2 * 1024 * 1024


def _resolve_text_option(
    value: str | None,
    file_path: Path | None,
    *,
    option: str,
    file_option: str,
) -> str:
    """Resolve a required text value from ``option`` or read it from ``file_option``.

    A real HTML document is hard to quote in a shell and Linux caps a single
    argument's size, so this sub-app's text-document options each come as a pair
    (``--content``/``--content-file`` on ``write``, ``--html``/``--html-file`` on
    ``create``); exactly one of the two must be given.
    """
    if file_path is not None and value is not None:
        raise typer.BadParameter(f"Pass only one of {option} or {file_option}.")
    if file_path is None:
        if value is None:
            raise typer.BadParameter(f"Provide {option} or {file_option}.")
        text = value
    else:
        display = str(file_path)
        path = file_path.expanduser()
        try:
            if path.stat().st_size > _MAX_TEXT_OPTION_FILE_BYTES:
                raise typer.BadParameter(
                    f"{file_option} {display!r} exceeds "
                    f"{_MAX_TEXT_OPTION_FILE_BYTES} bytes."
                )
            raw = path.read_bytes()
        except OSError as exc:
            reason = exc.strerror or exc.__class__.__name__
            raise typer.BadParameter(
                f"Could not read {file_option} {display!r}: {reason}."
            ) from exc
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise typer.BadParameter(
                f"{file_option} {display!r} is not valid UTF-8 text."
            ) from exc
    if not text.strip():
        raise typer.BadParameter(f"{option}/{file_option} must be non-empty.")
    return text


def _reject_blank_optional_string(value: str | None, flag: str) -> None:
    """Reject whitespace-only optional string flags on update."""
    if value is not None and not value.strip():
        raise typer.BadParameter(f"{flag}, when provided, must be non-empty.")


def _validate_sort_page_id_item(value: object) -> str:
    """Validate one page UUID from ``--page-ids`` or ``--ids-json`` before a sort write."""
    if isinstance(value, bool) or value is None:
        raise typer.BadParameter(
            "Each page UUID must be a non-empty string or positive integer."
        )
    if isinstance(value, (dict, list)):
        raise typer.BadParameter(
            "Each page UUID must be a non-empty string or positive integer."
        )
    if not isinstance(value, (str, int)):
        raise typer.BadParameter(
            "Each page UUID must be a non-empty string or positive integer."
        )
    cleaned = str(value).strip() if isinstance(value, int) else value.strip()
    if not cleaned:
        raise typer.BadParameter(
            "Each page UUID must be a non-empty string or positive integer."
        )
    if cleaned.startswith("-") and cleaned[1:].isdigit():
        raise typer.BadParameter("Each page UUID must be a positive integer.")
    if cleaned.isdigit() and int(cleaned) <= 0:
        raise typer.BadParameter("Each page UUID must be a positive integer.")
    return cleaned


def _reject_duplicate_sort_page_ids(page_ids: list[str]) -> None:
    """Reject duplicate page identifiers before ``sortPages``."""
    if len(set(page_ids)) != len(page_ids):
        raise typer.BadParameter("Page UUID list must not contain duplicates.")


def _parse_page_ids_for_sort(
    page_ids_csv: str | None,
    ids_json: str | None,
) -> list[str]:
    """Resolve ordered page UUIDs from ``--page-ids`` or ``--ids-json``."""
    if page_ids_csv is not None and page_ids_csv.strip():
        parts = [p.strip() for p in page_ids_csv.split(",") if p.strip()]
        if not parts:
            raise typer.BadParameter("--page-ids must list at least one page UUID.")
        ordered = [_validate_sort_page_id_item(part) for part in parts]
        _reject_duplicate_sort_page_ids(ordered)
        return ordered
    if ids_json is not None and ids_json.strip():
        parsed = parse_json_value(ids_json, "--ids-json")
        if not isinstance(parsed, list):
            raise typer.BadParameter("--ids-json must be a JSON array of page UUIDs.")
        if not parsed:
            raise typer.BadParameter("--ids-json must list at least one page UUID.")
        ordered = [_validate_sort_page_id_item(item) for item in parsed]
        _reject_duplicate_sort_page_ids(ordered)
        return ordered
    raise typer.BadParameter(
        "Provide --page-ids or --ids-json with at least one page UUID."
    )


def _parse_required_metadata_json(raw: str | None, option_name: str) -> dict[str, Any]:
    """Parse a required JSON object for element metadata."""
    metadata_obj = parse_json_object(raw, option_name)
    if metadata_obj is None:
        raise typer.BadParameter(f"{option_name} is required.")
    return metadata_obj


def _parse_optional_data_sources_json(raw: str | None) -> list[dict[str, Any]] | None:
    """Parse optional ``--data-sources`` as a JSON array of objects."""
    if raw is None or not raw.strip():
        return None
    parsed = parse_json_value(raw, "--data-sources")
    if not isinstance(parsed, list):
        raise typer.BadParameter("--data-sources must be a JSON array.")
    return parsed


_LAYOUT_ROWS_MESSAGE = (
    "{option} must be a JSON array of row objects from get_portal pages[].layout."
)


def _parse_layout_rows(raw: str, option_name: str) -> list[PortalPageLayoutRow]:
    """Parse a given page layout row array; blank text and ``null`` are rejected."""
    parsed = parse_json_value(raw, option_name)
    if not isinstance(parsed, list) or not all(isinstance(row, dict) for row in parsed):
        raise typer.BadParameter(_LAYOUT_ROWS_MESSAGE.format(option=option_name))
    try:
        return parse_portal_page_layout(parsed)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _portal_element_create_kwargs(
    validated: CreatePortalElementInput,
) -> dict[str, Any]:
    """Build kwargs for ``PipefyClient.create_portal_element`` after validation."""
    kwargs: dict[str, Any] = {
        "type": validated.type,
        "metadata": validated.metadata,
        "data_sources": validated.data_sources,
    }
    if validated.element_id is not None:
        kwargs["element_id"] = validated.element_id
    if validated.editable is not None:
        kwargs["editable"] = validated.editable
    if validated.layout is not None:
        kwargs["layout"] = validated.layout
    return kwargs


def _portal_element_update_kwargs(
    validated: UpdatePortalElementInput,
) -> dict[str, Any]:
    """Build kwargs for ``PipefyClient.update_portal_element`` after validation."""
    kwargs: dict[str, Any] = {
        "type": validated.type,
        "metadata": validated.metadata,
        "data_sources": validated.data_sources,
        "portal_uuid": validated.portal_uuid,
    }
    if validated.editable is not None:
        kwargs["editable"] = validated.editable
    return kwargs


@portal_app.command("list")
def portal_list(
    ctx: typer.Context,
    organization_uuid: str = typer.Option(
        ...,
        "--organization-uuid",
        help="Organization UUID, or numeric organization id (string).",
    ),
    search_term: str | None = typer.Option(
        None,
        "--search-term",
        help="Optional portal name filter.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """List portals for an organization."""

    async def factory(client: PipefyClient):
        return await client.list_portals(organization_uuid, search_term=search_term)

    run_cli_command(ctx, json_out, factory)


@portal_app.command("get", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_get(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Portal UUID."),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Fetch a portal by UUID."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)

    async def factory(client: PipefyClient):
        return await client.get_portal(portal_uuid)

    run_cli_command(ctx, json_out, factory)


@portal_app.command("create")
def portal_create(
    ctx: typer.Context,
    organization_uuid: str = typer.Option(
        ...,
        "--organization-uuid",
        help="Organization UUID, or numeric organization id (string).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Create or fetch the organization's main portal (idempotent)."""

    async def factory(client: PipefyClient):
        return await client.create_portal(organization_uuid)

    run_cli_command(ctx, json_out, factory)


@portal_app.command("update", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_update(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Portal UUID."),
    name: str | None = typer.Option(None, "--name", help="Portal display name."),
    visibility: str | None = typer.Option(
        None,
        "--visibility",
        help="Portal visibility: internal, private, or public.",
    ),
    color: str | None = typer.Option(None, "--color", help="Theme color."),
    icon: str | None = typer.Option(None, "--icon", help="Icon identifier."),
    display_pipefy_header: bool | None = typer.Option(
        None,
        "--display-pipefy-header/--no-display-pipefy-header",
        help="Show or hide the Pipefy header.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Update portal metadata (pass at least one attribute)."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)

    if all(x is None for x in (name, visibility, color, icon, display_pipefy_header)):
        raise typer.BadParameter(
            "Provide at least one of: --name, --visibility, --color, --icon, "
            "--display-pipefy-header / --no-display-pipefy-header."
        )

    _reject_blank_optional_string(name, "--name")
    _reject_blank_optional_string(color, "--color")
    _reject_blank_optional_string(icon, "--icon")

    async def factory(client: PipefyClient):
        update_kwargs: dict[str, str | bool] = {}
        if name is not None:
            update_kwargs["name"] = name.strip()
        if visibility is not None:
            update_kwargs["visibility"] = visibility
        if color is not None:
            update_kwargs["color"] = color.strip()
        if icon is not None:
            update_kwargs["icon"] = icon.strip()
        if display_pipefy_header is not None:
            update_kwargs["display_pipefy_header"] = display_pipefy_header
        return await client.update_portal(portal_uuid, **update_kwargs)

    run_cli_command(ctx, json_out, factory)


@portal_app.command("delete", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_delete(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Portal UUID."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Delete a portal permanently."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    confirm_destructive(yes=yes, description=f"portal {portal_uuid}")

    async def factory(client: PipefyClient):
        return await client.delete_portal(portal_uuid)

    run_cli_command(ctx, json_out, factory)


@page_app.command("create")
def portal_page_create(
    ctx: typer.Context,
    portal_uuid: str = typer.Option(
        ...,
        "--portal-uuid",
        help="Parent portal interface UUID.",
    ),
    title: str = typer.Option(..., "--title", help="Page title."),
    description: str | None = typer.Option(
        None,
        "--description",
        help="Optional page description.",
    ),
    index: int | None = typer.Option(
        None,
        "--index",
        min=0,
        help="Optional sort index (non-negative).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Create a portal page (bootstrap template when elements omitted on the API)."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    _reject_blank_optional_string(title, "--title")
    _reject_blank_optional_string(description, "--description")

    async def factory(client: PipefyClient):
        return await client.create_portal_page(
            portal_uuid,
            title.strip(),
            description=description.strip() if description is not None else None,
            index=index,
        )

    run_cli_command(ctx, json_out, factory)


@page_app.command("update", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_page_update(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Parent portal interface UUID."),
    page_uuid: str = resource_id_argument(help="Page UUID."),
    title: str | None = typer.Option(None, "--title", help="New page title."),
    description: str | None = typer.Option(
        None,
        "--description",
        help="New page description.",
    ),
    index: int | None = typer.Option(
        None,
        "--index",
        min=0,
        help="New sort index (non-negative).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Update portal page metadata (pass at least one attribute)."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    page_uuid = _require_non_empty_portal_uuid(page_uuid)

    if all(x is None for x in (title, description, index)):
        raise typer.BadParameter(
            "Provide at least one of: --title, --description, --index."
        )

    _reject_blank_optional_string(title, "--title")
    _reject_blank_optional_string(description, "--description")

    async def factory(client: PipefyClient):
        update_kwargs: dict[str, str | int] = {}
        if title is not None:
            update_kwargs["title"] = title.strip()
        if description is not None:
            update_kwargs["description"] = description.strip()
        if index is not None:
            update_kwargs["index"] = index
        return await client.update_portal_page(
            portal_uuid,
            page_uuid,
            **update_kwargs,
        )

    run_cli_command(ctx, json_out, factory)


@page_app.command("delete", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_page_delete(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Parent portal interface UUID."),
    page_uuid: str = resource_id_argument(help="Page UUID."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Delete a portal page permanently."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    page_uuid = _require_non_empty_portal_uuid(page_uuid)
    confirm_destructive(
        yes=yes,
        description=f"page {page_uuid} on portal {portal_uuid}",
    )

    async def factory(client: PipefyClient):
        return await client.delete_portal_page(portal_uuid, page_uuid)

    run_cli_command(ctx, json_out, factory)


@page_app.command("sort")
def portal_page_sort(
    ctx: typer.Context,
    portal_uuid: str = typer.Option(
        ...,
        "--portal-uuid",
        help="Parent portal interface UUID.",
    ),
    page_ids: str | None = typer.Option(
        None,
        "--page-ids",
        help="Comma-separated ordered page UUIDs.",
    ),
    ids_json: str | None = typer.Option(
        None,
        "--ids-json",
        help="JSON array of ordered page UUIDs.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Reorder portal pages."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    ordered_page_ids = _parse_page_ids_for_sort(page_ids, ids_json)

    async def factory(client: PipefyClient):
        return await client.sort_portal_pages(portal_uuid, ordered_page_ids)

    run_cli_command(ctx, json_out, factory)


@layout_app.command("update")
def portal_page_layout_update(
    ctx: typer.Context,
    page_id: str = typer.Option(..., "--page-id", help="Page UUID."),
    layout: str = typer.Option(
        ...,
        "--layout",
        help=(
            "Page layout row array. Each row needs a non-empty id, type row, "
            "and string children. [] is an empty page."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Update a portal page grid layout."""

    page_id = _require_non_empty_portal_uuid(page_id)
    layout_rows = _parse_layout_rows(layout, "--layout")

    async def factory(client: PipefyClient):
        return await client.update_portal_page_layout(page_id, layout_rows)

    run_cli_command(ctx, json_out, factory)


@element_app.command("create")
def portal_element_create(
    ctx: typer.Context,
    page_id: str = typer.Option(..., "--page-id", help="Parent page UUID."),
    type: str = typer.Option(
        ...,
        "--type",
        help="InterfacePageElementType value (e.g. forms, link).",
    ),
    metadata: str = typer.Option(
        None,
        "--metadata",
        help="Element metadata JSON (required; full shape depends on --type).",
    ),
    data_sources: str | None = typer.Option(
        None,
        "--data-sources",
        help="Optional JSON array of data source bindings (forms elements).",
    ),
    element_id: str | None = typer.Option(
        None,
        "--element-id",
        help=(
            "Client-provided element UUID; required with --layout so a layout row "
            "can reference the new element."
        ),
    ),
    layout: str | None = typer.Option(
        None,
        "--layout",
        help=(
            "Full page layout row array (get_portal pages[].layout) with a row listing "
            "--element-id, to create and place in one call. Each row needs a non-empty "
            "id, type row, and string children. Omit to leave the grid untouched."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Create a portal page element, optionally placed via --element-id and --layout."""

    page_id = _require_non_empty_portal_uuid(page_id)
    metadata_obj = _parse_required_metadata_json(metadata, "--metadata")
    data_sources_list = _parse_optional_data_sources_json(data_sources)
    layout_rows = None if layout is None else _parse_layout_rows(layout, "--layout")
    cleaned_element_id = (
        element_id.strip() if element_id and element_id.strip() else None
    )

    try:
        validated = CreatePortalElementInput.model_validate(
            {
                "page_id": page_id,
                "type": type,
                "metadata": metadata_obj,
                "data_sources": data_sources_list or [],
                "element_id": cleaned_element_id,
                "layout": layout_rows,
            }
        )
    except ValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc

    create_kwargs = _portal_element_create_kwargs(validated)

    async def factory(client: PipefyClient):
        return await client.create_portal_element(validated.page_id, **create_kwargs)

    run_cli_command(ctx, json_out, factory)


@element_app.command("update", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_element_update(
    ctx: typer.Context,
    element_id: str = resource_id_argument(help="Element UUID."),
    page_id: str = resource_id_argument(help="Parent page UUID."),
    type: str = typer.Option(
        ...,
        "--type",
        help="Element type for metadata validation (full metadata replace on API).",
    ),
    metadata: str = typer.Option(
        None,
        "--metadata",
        help="Complete element metadata JSON (Pipefy replaces the whole blob).",
    ),
    data_sources: str | None = typer.Option(
        None,
        "--data-sources",
        help=(
            'JSON array of {"repoId": ..., "fieldKeys": [...]} bindings; replaces '
            "the element's list, so '[]' unlinks them all. The API also needs "
            "editable when an entry lists fieldKeys, which this command does not "
            "send. Omit with --portal-uuid to keep the current ones."
        ),
    ),
    portal_uuid: str | None = typer.Option(
        None,
        "--portal-uuid",
        help=(
            "Portal holding the element; required when --data-sources is omitted. "
            "Its data sources and editable flag are read and sent back."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Update a portal page element (send the full metadata blob)."""

    element_id = _require_non_empty_portal_uuid(element_id)
    page_id = _require_non_empty_portal_uuid(page_id)
    metadata_obj = _parse_required_metadata_json(metadata, "--metadata")
    _reject_blank_optional_string(data_sources, "--data-sources")
    _reject_blank_optional_string(portal_uuid, "--portal-uuid")
    if data_sources is None and portal_uuid is None:
        raise typer.BadParameter(
            "Pass --portal-uuid to keep the element's current data sources, or "
            "--data-sources to replace them ('[]' unlinks them all)."
        )
    data_sources_list = _parse_optional_data_sources_json(data_sources)

    try:
        validated = UpdatePortalElementInput.model_validate(
            {
                "element_id": element_id,
                "page_id": page_id,
                "type": type,
                "metadata": metadata_obj,
                "data_sources": data_sources_list,
                "portal_uuid": portal_uuid,
            }
        )
    except ValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc

    update_kwargs = _portal_element_update_kwargs(validated)

    async def factory(client: PipefyClient):
        return await client.update_portal_element(
            validated.element_id,
            validated.page_id,
            **update_kwargs,
        )

    run_cli_command(ctx, json_out, factory)


@element_app.command("delete", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_element_delete(
    ctx: typer.Context,
    element_id: str = resource_id_argument(help="Element UUID."),
    page_id: str = resource_id_argument(help="Parent page UUID."),
    layout: str | None = typer.Option(
        None,
        "--layout",
        help=(
            "Full page layout row array (get_portal pages[].layout) with the element "
            "removed from every row, to prune the grid in the same call. Each row "
            "needs a non-empty id, type row, and string children."
        ),
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Delete a portal page element permanently; --layout prunes the page grid too."""

    element_id = _require_non_empty_portal_uuid(element_id)
    page_id = _require_non_empty_portal_uuid(page_id)
    layout_rows = None if layout is None else _parse_layout_rows(layout, "--layout")
    try:
        validated = DeletePortalElementInput.model_validate(
            {"element_id": element_id, "page_id": page_id, "layout": layout_rows}
        )
    except ValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc
    description = f"element {element_id} on page {page_id}"
    if validated.layout is not None:
        description += " and replace that page's layout"
    confirm_destructive(yes=yes, description=description)
    delete_kwargs = {} if validated.layout is None else {"layout": validated.layout}

    async def factory(client: PipefyClient):
        return await client.delete_portal_element(element_id, page_id, **delete_kwargs)

    run_cli_command(ctx, json_out, factory)


@element_app.command("duplicate")
def portal_element_duplicate(
    ctx: typer.Context,
    element_id: str = typer.Option(
        ...,
        "--element-id",
        help="Element UUID to duplicate.",
    ),
    portal_uuid: str = typer.Option(
        ...,
        "--portal-uuid",
        help="Portal interface UUID that owns the page.",
    ),
    page_id: str = typer.Option(
        ...,
        "--page-id",
        help="Page UUID that contains the element.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Duplicate a portal page element on the same page (source portal + page UUIDs)."""

    element_id = _require_non_empty_portal_uuid(element_id)
    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    page_id = _require_non_empty_portal_uuid(page_id)

    async def factory(client: PipefyClient):
        return await client.duplicate_portal_element(
            element_id=element_id,
            portal_uuid=portal_uuid,
            page_id=page_id,
        )

    run_cli_command(ctx, json_out, factory)


@sub_portal_app.command("create")
def portal_sub_portal_create(
    ctx: typer.Context,
    main_portal_uuid: str = typer.Option(
        ...,
        "--main-portal-uuid",
        help="Parent main portal interface UUID.",
    ),
    name: str | None = typer.Option(None, "--name", help="Optional sub-portal name."),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Create a sub-portal on a main portal."""

    main_portal_uuid = _require_non_empty_portal_uuid(main_portal_uuid)
    _reject_blank_optional_string(name, "--name")

    async def factory(client: PipefyClient):
        return await client.create_sub_portal(
            main_portal_uuid,
            name=name.strip() if name is not None else None,
        )

    run_cli_command(ctx, json_out, factory)


@sub_portal_app.command("attach", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_sub_portal_attach(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Main portal interface UUID."),
    element_id: str = resource_id_argument(help="Page element UUID."),
    sub_portal_uuid: str = resource_id_argument(help="Sub-portal UUID."),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Attach a sub-portal to a portal page element."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    element_id = _require_non_empty_portal_uuid(element_id)
    sub_portal_uuid = _require_non_empty_portal_uuid(sub_portal_uuid)

    async def factory(client: PipefyClient):
        return await client.update_sub_portal_element(
            portal_uuid,
            element_id,
            sub_portal_uuid,
        )

    run_cli_command(ctx, json_out, factory)


@sub_portal_app.command("detach", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_sub_portal_detach(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Main portal interface UUID."),
    element_id: str = resource_id_argument(help="Page element UUID."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Detach a sub-portal from a portal page element."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    element_id = _require_non_empty_portal_uuid(element_id)
    confirm_destructive(
        yes=yes,
        description=(
            f"sub-portal wiring on element {element_id} on portal {portal_uuid}"
        ),
    )

    async def factory(client: PipefyClient):
        return await client.delete_sub_portal_element(portal_uuid, element_id)

    run_cli_command(ctx, json_out, factory)


@sub_portal_app.command("publish", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_sub_portal_publish(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Main portal interface UUID."),
    element_id: str = resource_id_argument(help="Page element UUID."),
    sub_portal_uuid: str = resource_id_argument(help="Sub-portal UUID."),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Publish a sub-portal on a portal page element."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    element_id = _require_non_empty_portal_uuid(element_id)
    sub_portal_uuid = _require_non_empty_portal_uuid(sub_portal_uuid)

    async def factory(client: PipefyClient):
        return await client.publish_sub_portal(
            portal_uuid,
            element_id,
            sub_portal_uuid,
        )

    run_cli_command(ctx, json_out, factory)


@sub_portal_app.command("unpublish", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_sub_portal_unpublish(
    ctx: typer.Context,
    portal_uuid: str = resource_id_argument(help="Main portal interface UUID."),
    element_id: str = resource_id_argument(help="Page element UUID."),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Unpublish a sub-portal from a portal page element."""

    portal_uuid = _require_non_empty_portal_uuid(portal_uuid)
    element_id = _require_non_empty_portal_uuid(element_id)

    async def factory(client: PipefyClient):
        return await client.unpublish_sub_portal(portal_uuid, element_id)

    run_cli_command(ctx, json_out, factory)


@sub_portal_app.command("delete", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def portal_sub_portal_delete(
    ctx: typer.Context,
    sub_portal_uuid: str = resource_id_argument(help="Sub-portal UUID."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Delete a sub-portal permanently."""

    sub_portal_uuid = _require_non_empty_portal_uuid(sub_portal_uuid)
    confirm_destructive(yes=yes, description=f"sub-portal {sub_portal_uuid}")

    async def factory(client: PipefyClient):
        return await client.delete_sub_portal(sub_portal_uuid)

    run_cli_command(ctx, json_out, factory)


_HTML_INTERFACE_PERMISSION_GUIDANCE = (
    "Permission denied. Request organization permissions such as "
    "`create_portal` or `manage_portals` from your admin."
)
_HTML_INTERFACE_SOURCE_ACCESS_DENIED = (
    "Permission denied for a data source: you can bind only the pipes and "
    "tables 'portal html-interface repos' returns for this interface."
)
_HTML_INTERFACE_ACTION_SOURCE_ACCESS_DENIED = (
    "Permission denied for a data source of this element: you can set its "
    "actions only when you can bind every pipe and table its sources read, as "
    "'portal html-interface repos' returns them for this interface."
)
_NOT_FOUND_ERROR_CODES = frozenset({"RECORD_NOT_FOUND", "RESOURCE_NOT_FOUND"})
_GRID_INTERFACE_ERROR_MARKER = "use get_portal to read its elements"


def _rewrite_grid_interface_error(exc: ValueError) -> ValueError:
    """Rewrite get_html_interface's grid-interface error to name the CLI command.

    ``get_html_interface`` raises this ``ValueError`` (not a ``PipefyGraphQLError``,
    so ``_html_interface_error_text`` never sees it) pointing a caller at
    ``get_portal``, its own SDK/MCP method name. A CLI user needs
    ``pipefy portal get`` instead. Any other ``ValueError`` (e.g. a plain
    not-found) passes through unchanged, keeping its own exit code (2).
    """
    text = str(exc)
    if _GRID_INTERFACE_ERROR_MARKER not in text:
        return exc
    return ValueError(
        text.replace(
            _GRID_INTERFACE_ERROR_MARKER, "use `pipefy portal get` to read its elements"
        )
    )


def _graphql_error_codes(exc: BaseException) -> list[str]:
    """Extract GraphQL ``extensions.code`` values from a Pipefy GraphQL error."""
    codes: list[str] = []
    errors = getattr(exc, "errors", None)
    if isinstance(errors, list):
        for item in errors:
            if not isinstance(item, dict):
                continue
            extensions = item.get("extensions")
            if isinstance(extensions, dict):
                code = extensions.get("code")
                if isinstance(code, str) and code:
                    codes.append(code)
    return codes


def _html_validation_error_text(exc: HtmlValidationError) -> str:
    """One line per violation, matching the MCP tools' own formatting."""
    count = len(exc.violations)
    noun = "violation" if count == 1 else "violations"
    lines = [
        f"The HTML was not saved: it has {count} {noun}. "
        "Fix every one, then write the whole document again."
    ]
    for violation in exc.violations:
        location = violation.selector or ""
        if violation.attribute:
            location += f"[{violation.attribute}]"
        location_clause = f" at {location}" if location else ""
        lines.append(f"- {violation.code}{location_clause}: {violation.message}")
    return "\n".join(lines)


def _html_interface_error_text(
    exc: BaseException,
    *,
    not_found_message: str | None = None,
    source_access_denied: bool = False,
    source_access_denied_message: str = _HTML_INTERFACE_SOURCE_ACCESS_DENIED,
) -> str | None:
    """CLI-side twin of the MCP html-interface tools' error mapping.

    Returns ``None`` when this doesn't recognize the error, so the caller
    (``_reraise_mapped_html_interface_error``) knows to leave it unmapped.
    """
    if isinstance(exc, HtmlValidationError):
        return _html_validation_error_text(exc)

    if not isinstance(exc, PipefyGraphQLError):
        return None

    text = str(exc).strip()
    lowered = text.lower()
    codes = _graphql_error_codes(exc)

    if not_found_message is not None and (
        _NOT_FOUND_ERROR_CODES.intersection(codes)
        or lowered.startswith("couldn't find")
    ):
        return not_found_message

    if source_access_denied and not codes and lowered == "permission denied":
        return source_access_denied_message

    if "PERMISSION_DENIED" in codes or "permission denied" in lowered:
        return _HTML_INTERFACE_PERMISSION_GUIDANCE

    return None


def _reraise_mapped_html_interface_error(
    exc: Exception,
    *,
    not_found_message: str | None = None,
    source_access_denied: bool = False,
    source_access_denied_message: str = _HTML_INTERFACE_SOURCE_ACCESS_DENIED,
) -> NoReturn:
    """Re-raise ``exc`` with the MCP twins' clean text in place of the raw API text.

    Keeps ``exc``'s own exception type (and so ``run_cli_command``'s exit code
    for it) wherever possible, by reconstructing the same type with the clean
    text rather than wrapping it in a different one. This needs no change to
    the shared ``run_cli_command``: every command here calls this from its own
    ``except`` block instead.

    ``PortalPermissionError`` is left untouched on purpose: its own message is
    already the clean guidance text, and it is already the CLI-wide exit-2
    pattern for a denial. A permission denial that instead reaches here as a
    raw ``PipefyGraphQLError`` (a read, which the SDK does not wrap into
    ``PortalPermissionError``) is re-raised as ``PortalPermissionError`` too,
    for the same reason: both ``_HTML_INTERFACE_PERMISSION_GUIDANCE`` and
    ``_HTML_INTERFACE_SOURCE_ACCESS_DENIED`` are a permission denial, and a
    caller scripting against this sub-app should see one exit code for that
    cause regardless of which internal call (read or write) was refused.
    """
    if isinstance(exc, PortalPermissionError):
        raise exc
    text = _html_interface_error_text(
        exc,
        not_found_message=not_found_message,
        source_access_denied=source_access_denied,
        source_access_denied_message=source_access_denied_message,
    )
    if text is None:
        raise exc
    if text in (
        _HTML_INTERFACE_PERMISSION_GUIDANCE,
        _HTML_INTERFACE_SOURCE_ACCESS_DENIED,
        _HTML_INTERFACE_ACTION_SOURCE_ACCESS_DENIED,
    ):
        raise PortalPermissionError(text) from exc
    if isinstance(exc, PipefyGraphQLError):
        raise PipefyGraphQLError([{"message": text}]) from exc
    raise PipefyError(text) from exc


@html_interface_app.command("list")
def html_interface_list(
    ctx: typer.Context,
    organization_uuid: str = typer.Option(
        ...,
        "--organization-uuid",
        help="Organization UUID, or numeric organization id.",
    ),
    search_term: str | None = typer.Option(
        None,
        "--search-term",
        help="Optional interface name filter.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """List an organization's HTML interfaces (grid portals are not returned here)."""

    async def factory(client: PipefyClient):
        try:
            return await client.list_html_interfaces(
                organization_uuid, search_term=search_term
            )
        except Exception as exc:
            _reraise_mapped_html_interface_error(exc)

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("guidelines")
def html_interface_guidelines(
    ctx: typer.Context,
    include_design_system: bool = typer.Option(
        False,
        "--include-design-system",
        help="Also return the designSystem component catalog. It is most of "
        "the response; request it only when styling a page.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Fetch the HTML/CSS authoring rules and data-source filter format.

    The rules are the same for every organization; this takes no required
    argument.
    """

    async def factory(client: PipefyClient):
        try:
            return await client.get_interface_html_guidelines(
                include_design_system=include_design_system
            )
        except Exception as exc:
            _reraise_mapped_html_interface_error(exc)

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("get", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def html_interface_get(
    ctx: typer.Context,
    interface_uuid: str = resource_id_argument(help="HTML interface UUID."),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Fetch an HTML interface with each customCode element's live HTML."""

    interface_uuid = _require_non_empty_portal_uuid(interface_uuid)

    async def factory(client: PipefyClient):
        try:
            return await client.get_html_interface(interface_uuid)
        except ValueError as exc:
            raise _rewrite_grid_interface_error(exc) from exc
        except Exception as exc:
            _reraise_mapped_html_interface_error(
                exc, not_found_message=f"No HTML interface has uuid '{interface_uuid}'."
            )

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("write")
def html_interface_write(
    ctx: typer.Context,
    page_id: str = typer.Option(..., "--page-id", help="Page holding the element."),
    element_id: str = typer.Option(
        ..., "--element-id", help="The page's customCode element."
    ),
    content: str | None = typer.Option(
        None,
        "--content",
        help="The whole HTML document; it replaces the live one. "
        "Mutually exclusive with --content-file.",
    ),
    content_file: Path | None = typer.Option(
        None,
        "--content-file",
        help="Read the HTML document from this file instead of --content.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Write and publish the HTML of an HTML interface's customCode element."""

    page_id = _require_non_empty_portal_uuid(page_id)
    element_id = _require_non_empty_portal_uuid(element_id)
    content = _resolve_text_option(
        content, content_file, option="--content", file_option="--content-file"
    )

    async def factory(client: PipefyClient):
        try:
            return await client.write_html_document(
                page_id=page_id, element_id=element_id, content=content
            )
        except Exception as exc:
            _reraise_mapped_html_interface_error(exc)

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("create")
def html_interface_create(
    ctx: typer.Context,
    organization_uuid: str = typer.Option(
        ...,
        "--organization-uuid",
        help="Organization UUID, or numeric organization id.",
    ),
    name: str = typer.Option(
        ..., "--name", help="Interface name; also used as the one page's title."
    ),
    html: str | None = typer.Option(
        None,
        "--html",
        help="The page's whole HTML document. Mutually exclusive with --html-file.",
    ),
    html_file: Path | None = typer.Option(
        None,
        "--html-file",
        help="Read the page's whole HTML document from this file instead of --html.",
    ),
    color: PortalColor = typer.Option(
        "blue",
        "--color",
        help=(
            "One of: blue, cyan, gray, green, indigo, lime, pink, purple, "
            "orange, red, sky, yellow."
        ),
    ),
    data_sources: str | None = typer.Option(
        None,
        "--data-sources",
        help=(
            "Optional JSON array of source bindings (id, name, repoId, fieldKeys, "
            "optional filters); at most 10, id/name unique among them."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Create an HTML interface and write its first page in one call."""

    if not name.strip():
        raise typer.BadParameter("--name must be non-empty.")
    name = name.strip()
    html = _resolve_text_option(
        html, html_file, option="--html", file_option="--html-file"
    )
    data_sources_list = _parse_optional_data_sources_json(data_sources)
    if data_sources_list is not None:
        try:
            InterfaceDataSources.model_validate(data_sources_list)
        except ValidationError as exc:
            raise typer.BadParameter(str(exc)) from exc

    async def factory(client: PipefyClient):
        try:
            interface = await client.create_interface(
                organization_uuid, name, color=color, data_sources=data_sources_list
            )
        except Exception as exc:
            _reraise_mapped_html_interface_error(
                exc,
                not_found_message="One of the data sources' repoId was not found.",
                source_access_denied=True,
            )
        pages = interface.get("pages") or []
        elements = pages[0].get("elements") if pages else None
        if not pages or not elements:
            msg = (
                "createInterface returned no page to write HTML into. The "
                f"interface ({interface.get('uuid')}) may already exist; check "
                "with 'pipefy portal html-interface get' before retrying, "
                "instead of running create again, which would create a second, "
                "orphaned interface."
            )
            raise ValueError(msg)
        page_id = pages[0]["uuid"]
        element_id = elements[0]["uuid"]
        try:
            await client.write_html_document(
                page_id=page_id, element_id=element_id, content=html
            )
        except Exception as exc:
            interface_uuid = interface.get("uuid")
            typer.echo(
                f"The interface ({interface_uuid}) was already created with a "
                "blank page. Resolve the error below, then write with:\n"
                f"  pipefy portal html-interface write --page-id {page_id} "
                f"--element-id {element_id} --content ...\n"
                "Do not run create again; it would create a second, orphaned "
                "interface.",
                err=True,
            )
            # No not_found_message here: create_html_interface's own write-phase
            # handling (portal_tools.py) doesn't map one either for this exact
            # failure, so this stays a twin of that, not an invented improvement.
            _reraise_mapped_html_interface_error(exc)
        return interface

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("repos")
def html_interface_repos(
    ctx: typer.Context,
    organization_id: str = typer.Option(
        ...,
        "--organization-id",
        help="Numeric organization id; a uuid is rejected.",
    ),
    interface_uuid: str | None = typer.Option(
        None,
        "--interface-uuid",
        help="Interface the source is for; narrows to repos it can bind.",
    ),
    repo_name: str | None = typer.Option(
        None,
        "--repo-name",
        help="Case-insensitive part of the repo name.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """List the pipes and tables an interface element can take as a data source."""

    interface_uuid = validate_optional_resource_id(interface_uuid, "interface_uuid")

    async def factory(client: PipefyClient):
        try:
            repos = await client.list_interface_repos(
                organization_id, interface_uuid=interface_uuid, repo_name=repo_name
            )
        except Exception as exc:
            _reraise_mapped_html_interface_error(
                exc,
                not_found_message=f"No organization has id '{organization_id}'.",
                source_access_denied=True,
            )
        return {"repos": repos}

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("repo-fields")
def html_interface_repo_fields(
    ctx: typer.Context,
    repo_uuid: str = typer.Option(
        ..., "--repo-uuid", help="The repo's uuid, as 'repos' returns it."
    ),
    interface_uuid: str | None = typer.Option(
        None,
        "--interface-uuid",
        help="Interface the source is for.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """List a pipe's or table's custom fields, for an interface data source."""

    repo_uuid = _require_non_empty_portal_uuid(repo_uuid)
    interface_uuid = validate_optional_resource_id(interface_uuid, "interface_uuid")

    async def factory(client: PipefyClient):
        missing = f"No repo has uuid '{repo_uuid}'"
        if interface_uuid is not None:
            missing += f", or no interface has uuid '{interface_uuid}'"
        not_found_message = (
            f"{missing}. 'pipefy portal html-interface repos' lists the repos "
            "an interface can read."
        )
        try:
            fields = await client.get_interface_repo_fields(
                repo_uuid, interface_uuid=interface_uuid
            )
        except Exception as exc:
            _reraise_mapped_html_interface_error(
                exc, not_found_message=not_found_message, source_access_denied=True
            )
        return {"fields": fields}

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("set-sources")
def html_interface_set_sources(
    ctx: typer.Context,
    interface_uuid: str = typer.Option(
        ..., "--interface-uuid", help="HTML interface holding the page."
    ),
    page_id: str = typer.Option(..., "--page-id", help="Page holding the element."),
    element_id: str = typer.Option(
        ..., "--element-id", help="The page's customCode element."
    ),
    data_sources: str = typer.Option(
        ...,
        "--data-sources",
        help=(
            "JSON array, the element's complete source list (id, name, repoId, "
            "fieldKeys, optional filters); '[]' removes them all."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Replace the data sources of an HTML interface's customCode element."""

    interface_uuid = _require_non_empty_portal_uuid(interface_uuid)
    page_id = _require_non_empty_portal_uuid(page_id)
    element_id = _require_non_empty_portal_uuid(element_id)
    parsed = parse_json_value(data_sources, "--data-sources")
    if not isinstance(parsed, list):
        raise typer.BadParameter("--data-sources must be a JSON array.")
    try:
        sources = InterfaceDataSources.model_validate(parsed)
    except ValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc

    async def factory(client: PipefyClient):
        try:
            return await client.set_interface_sources(
                page_id, element_id, sources.root, interface_uuid=interface_uuid
            )
        except ValueError as exc:
            raise _rewrite_grid_interface_error(exc) from exc
        except Exception as exc:
            _reraise_mapped_html_interface_error(
                exc,
                not_found_message=f"No HTML interface has uuid '{interface_uuid}'.",
                source_access_denied=True,
            )

    run_cli_command(ctx, json_out, factory)


@html_interface_app.command("set-actions")
def html_interface_set_actions(
    ctx: typer.Context,
    interface_uuid: str = typer.Option(
        ..., "--interface-uuid", help="HTML interface holding the page."
    ),
    page_id: str = typer.Option(..., "--page-id", help="Page holding the element."),
    element_id: str = typer.Option(
        ..., "--element-id", help="The page's customCode element."
    ),
    actions: str = typer.Option(
        ...,
        "--actions",
        help=(
            "JSON array, the element's complete action list (actionId, kind and "
            "the kind's keys); '[]' removes them all."
        ),
    ),
    editable: bool | None = typer.Option(
        None,
        "--editable/--no-editable",
        help=(
            "Whether viewers can save edits to the element's data-pfy-editable "
            "fields; omit to keep the current value."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Replace the actions of an HTML interface's customCode element."""

    interface_uuid = _require_non_empty_portal_uuid(interface_uuid)
    page_id = _require_non_empty_portal_uuid(page_id)
    element_id = _require_non_empty_portal_uuid(element_id)
    parsed = parse_json_value(actions, "--actions")
    if not isinstance(parsed, list):
        raise typer.BadParameter("--actions must be a JSON array.")
    try:
        validated = InterfaceActions.model_validate(parsed)
    except ValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc

    async def factory(client: PipefyClient):
        try:
            return await client.set_interface_actions(
                page_id,
                element_id,
                validated.root,
                interface_uuid=interface_uuid,
                editable=editable,
            )
        except ValueError as exc:
            raise _rewrite_grid_interface_error(exc) from exc
        except Exception as exc:
            _reraise_mapped_html_interface_error(
                exc,
                not_found_message=f"No HTML interface has uuid '{interface_uuid}'.",
                source_access_denied=True,
                source_access_denied_message=(
                    _HTML_INTERFACE_ACTION_SOURCE_ACCESS_DENIED
                ),
            )

    run_cli_command(ctx, json_out, factory)


page_app.add_typer(layout_app, name="layout")
portal_app.add_typer(page_app, name="page")
portal_app.add_typer(element_app, name="element")
portal_app.add_typer(sub_portal_app, name="sub-portal")
portal_app.add_typer(html_interface_app, name="html-interface")
