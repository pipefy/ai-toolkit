"""MCP tools for Pipefy portal operations."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pipefy_sdk import PipefyId
from pipefy_sdk.models.portal import (
    CreatePortalElementInput,
    DeletePortalElementInput,
    InterfaceDataSources,
    PortalElementType,
    PortalVisibility,
    UpdatePortalElementInput,
    parse_portal_page_layout,
)
from pipefy_sdk.utils.organization_identifiers import numeric_organization_id
from pydantic import ValidationError

from pipefy_mcp.core.tool_error_envelope import tool_error
from pipefy_mcp.tools.destructive_tool_guard import check_destructive_confirmation
from pipefy_mcp.tools.introspection_tool_helpers import (
    build_error_payload,
    build_success_payload,
)
from pipefy_mcp.tools.portal_tool_helpers import (
    finalize_internal_api_mutation,
    interface_sources_validation_error,
    map_interface_source_error_to_message,
    map_portal_error_to_message,
    plan_portal_element_delete_confirmation,
    portal_element_validation_error,
    run_sub_portal_internal_api_tool,
    validate_portal_optional_string,
    validate_portal_page_index,
    validate_sort_page_ids_no_duplicates,
    validate_tool_ids,
)
from pipefy_mcp.tools.remote_profile import REMOTE
from pipefy_mcp.tools.tool_context import get_pipefy_client
from pipefy_mcp.tools.validation_helpers import (
    validate_optional_tool_id,
    validate_tool_id,
)

_PORTAL_READ_FAILED = "Portal request failed."


def _repo_fields_not_found_message(repo_uuid: str, interface_uuid: str | None) -> str:
    missing = f"No repo has uuid '{repo_uuid}'"
    if interface_uuid is not None:
        missing += f", or no interface has uuid '{interface_uuid}'"
    return f"{missing}. list_interface_repos lists the repos an interface can read."


class PortalTools:
    """Registers MCP tools for portal read, metadata CRUD, and page operations."""

    @staticmethod
    def register(mcp: MCPServer) -> None:
        """Register portal-related tools on the MCP server."""

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=True),
            meta=REMOTE,
        )
        async def list_portals(
            ctx: Context,
            organization_uuid: PipefyId,
            search_term: str | None = None,
        ) -> dict[str, Any]:
            """List portals for an organization.

            Each organization has at most one main portal; additional entries may be
            sub-portals. Returns uuid, name, visibility, and subType for each
            portal (use ``get_portal`` for ``published`` and page detail). The
            response includes both ``result`` (pretty-printed JSON string)
            and ``data`` (parsed dict) for convenience.

            Args:
                organization_uuid: Organization UUID, or numeric organization id
                    (string or unquoted integer via MCP clients).
                search_term: Optional name filter.
            """
            client = get_pipefy_client(ctx)
            organization_uuid, err = validate_tool_id(
                organization_uuid, "organization_uuid"
            )
            if err is not None:
                return err
            await ctx.debug(
                f"list_portals: organization_uuid={organization_uuid}, "
                f"search_term={search_term}"
            )
            try:
                portals = await client.list_portals(
                    organization_uuid, search_term=search_term
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_portal_error_to_message(exc, empty_fallback=_PORTAL_READ_FAILED)
                )
            return build_success_payload({"portals": portals}, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=True),
            meta=REMOTE,
        )
        async def get_portal(
            ctx: Context,
            portal_uuid: str,
        ) -> dict[str, Any]:
            """Fetch a portal by UUID with pages, elements, and sub-portals.

            Returns uuid, name, visibility, published, pages (with elements), and
            subPortals. The response includes both ``result`` (pretty-printed JSON
            string) and ``data`` (parsed dict) for convenience.

            Page elements include a ``metadata`` JSON object whose shape depends on
            ``type`` (non-exhaustive):

            - ``forms`` -> ``{ name: str, defaultValues?: object, ... }``
            - ``pipe`` -> ``{ pipeId: str }``
            - ``link`` -> ``{ linkName: str, linkUrl?: str, gridMap?: object }``

            Additional element types may appear; treat unknown keys as opaque.

            Args:
                portal_uuid: Portal interface UUID.
            """
            client = get_pipefy_client(ctx)
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            await ctx.debug(f"get_portal: portal_uuid={portal_uuid}")
            try:
                portal = await client.get_portal(portal_uuid)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_portal_error_to_message(exc, empty_fallback=_PORTAL_READ_FAILED)
                )
            return build_success_payload(portal, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=True),
            meta=REMOTE,
        )
        async def get_interface_html_guidelines(ctx: Context) -> dict[str, Any]:
            """Fetch the HTML/CSS rules and data-source filter format for customCode content.

            Call this before writing an HTML interface's customCode element.
            Returns every allowed tag and attribute, every forbidden
            tag/attribute/CSS construct with its violation code, the full
            error-code list, the filter-tree
            format (a worked example plus the operators each field type supports),
            content-size and nesting limits, and a ``designSystem`` snapshot: a
            component catalog (tokens, icons and components with usage examples)
            to style generated content consistently. The rules are the same for
            every organization. The response includes both ``result``
            (pretty-printed JSON string) and ``data`` (parsed dict) for convenience.
            """
            client = get_pipefy_client(ctx)
            await ctx.debug("get_interface_html_guidelines")
            try:
                guidelines = await client.get_interface_html_guidelines()
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_portal_error_to_message(exc, empty_fallback=_PORTAL_READ_FAILED)
                )
            return build_success_payload(guidelines, include_parsed=True)

        @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
        async def list_interface_repos(
            ctx: Context,
            organization_id: PipefyId,
            interface_uuid: str | None = None,
            repo_name: str | None = None,
        ) -> dict[str, Any]:
            """List the pipes and tables an HTML interface can take as data sources.

            Step one of declaring a source: pick a repo here, its fields with
            ``get_interface_repo_fields``, then set the sources with
            ``set_interface_sources``. Configure sources before writing the HTML
            that reads them. For an interface that is not a portal, the list holds
            the published pipes and tables you administer, ordered by name. Each
            repo has ``uuid`` (a source's ``repoId``), ``name``, ``type`` (``Pipe``
            or ``Table``), ``id``, ``suid``, ``icon``, ``color`` and ``noun``.

            A successful listing does not show that the interface exists: an
            unknown ``interface_uuid`` is listed like an interface that is not a
            portal, and an organization you cannot see lists nothing, both without
            an error. Confirm the interface with ``get_html_interface``.

            Args:
                organization_id: Numeric organization id (``list_organizations``
                    returns it as ``id``); a uuid is rejected.
                interface_uuid: The interface the sources are for; pass it, since it
                    decides which repos qualify. An unknown uuid is not an error.
                repo_name: Case-insensitive part of the repo name.
            """
            client = get_pipefy_client(ctx)
            try:
                organization_id = numeric_organization_id(organization_id)
            except ValueError as exc:
                return tool_error(str(exc), code="INVALID_ARGUMENTS")
            _ok, interface_uuid, err = validate_optional_tool_id(
                interface_uuid, "interface_uuid"
            )
            if err is not None:
                return err
            repo_name, err = validate_portal_optional_string(repo_name, "repo_name")
            if err is not None:
                return err
            await ctx.debug(
                f"list_interface_repos: organization_id={organization_id}, "
                f"interface_uuid={interface_uuid}"
            )
            try:
                repos = await client.list_interface_repos(
                    organization_id, interface_uuid=interface_uuid, repo_name=repo_name
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_interface_source_error_to_message(
                        exc,
                        not_found_message=(
                            f"No organization has id '{organization_id}'."
                        ),
                        empty_fallback=_PORTAL_READ_FAILED,
                    )
                )
            return build_success_payload({"repos": repos}, include_parsed=True)

        @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
        async def get_interface_repo_fields(
            ctx: Context,
            repo_uuid: str,
            interface_uuid: str | None = None,
        ) -> dict[str, Any]:
            """List a pipe's or table's custom fields, to choose a data source's keys.

            A custom field's key in ``fieldKeys`` is its ``uuid``, not its ``id``.
            Built-in keys such as ``title``, ``created_at`` and ``current_phase_id``
            are not listed here: ``get_interface_html_guidelines`` returns them as
            ``filters.fixedColumnNames``. Each field has ``uuid``, ``label``,
            ``type``, ``phaseId``, ``archived``, ``required``, ``options``,
            ``description``, ``helpText`` and ``connectedRepoId``; archived fields
            are included.

            Args:
                repo_uuid: The repo's ``uuid`` from ``list_interface_repos``.
                interface_uuid: The interface the source is for.
            """
            client = get_pipefy_client(ctx)
            repo_uuid, err = validate_tool_id(repo_uuid, "repo_uuid")
            if err is not None:
                return err
            _ok, interface_uuid, err = validate_optional_tool_id(
                interface_uuid, "interface_uuid"
            )
            if err is not None:
                return err
            await ctx.debug(f"get_interface_repo_fields: repo_uuid={repo_uuid}")
            try:
                fields = await client.get_interface_repo_fields(
                    repo_uuid, interface_uuid=interface_uuid
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_interface_source_error_to_message(
                        exc,
                        not_found_message=_repo_fields_not_found_message(
                            repo_uuid, interface_uuid
                        ),
                        empty_fallback=_PORTAL_READ_FAILED,
                    )
                )
            return build_success_payload({"fields": fields}, include_parsed=True)

        @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False))
        async def set_interface_sources(
            ctx: Context,
            interface_uuid: str,
            page_id: str,
            element_id: str,
            data_sources: list[dict[str, Any]],
        ) -> dict[str, Any]:
            """Replace the data sources of an HTML interface's customCode element.

            Set sources before writing the HTML that reads them. The list replaces
            the element's sources (``[]`` removes them all); the element's other
            settings are kept. Each source is
            ``{"id", "name", "repoId", "fieldKeys", "filters"}``:

            - ``id``: the handle the element's HTML reads the source by; ``name``:
              its label. Both unique within the element.
            - ``repoId``: a repo ``uuid`` from ``list_interface_repos``.
            - ``fieldKeys``: 1 to 30 keys, custom field uuids from
              ``get_interface_repo_fields`` and built-in keys such as ``title``.
            - ``filters``: optional filter tree in the format
              ``get_interface_html_guidelines`` describes, or null.

            At most 10 sources. Returns the element ``uuid`` and the
            ``dataSources`` as sent, once the update reports success; they are not
            read back. Call ``get_html_interface`` for the stored sources.

            Args:
                interface_uuid: The HTML interface's uuid.
                page_id: Page holding the element.
                element_id: The page's customCode element.
                data_sources: The element's complete source list.
            """
            client = get_pipefy_client(ctx)
            interface_uuid, err = validate_tool_id(interface_uuid, "interface_uuid")
            if err is not None:
                return err
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            element_id, err = validate_tool_id(element_id, "element_id")
            if err is not None:
                return err
            try:
                sources = InterfaceDataSources.model_validate(data_sources)
            except ValidationError as exc:
                return interface_sources_validation_error(exc)
            await ctx.debug(
                f"set_interface_sources: element_id={element_id}, "
                f"sources={len(sources.root)}"
            )
            try:
                element = await client.set_interface_sources(
                    page_id, element_id, sources.root, interface_uuid=interface_uuid
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_interface_source_error_to_message(
                        exc,
                        not_found_message=(
                            f"No HTML interface has uuid '{interface_uuid}'."
                        ),
                    )
                )
            return build_success_payload(element, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=True),
        )
        async def list_interfaces(
            ctx: Context,
            organization_uuid: PipefyId,
            search_term: str | None = None,
        ) -> dict[str, Any]:
            """List an organization's HTML interfaces (``contentModeHtml``).

            Grid-layout portals and sub-portals are not returned here; use
            ``list_portals`` for those. Returns uuid, name, visibility, and
            ``contentModeHtml`` for each interface. The response includes both
            ``result`` (pretty-printed JSON string) and ``data`` (parsed dict)
            for convenience.

            Args:
                organization_uuid: Organization UUID, or numeric organization id.
                search_term: Optional name filter.
            """
            client = get_pipefy_client(ctx)
            organization_uuid, err = validate_tool_id(
                organization_uuid, "organization_uuid"
            )
            if err is not None:
                return err
            await ctx.debug(
                f"list_interfaces: organization_uuid={organization_uuid}, "
                f"search_term={search_term}"
            )
            try:
                interfaces = await client.list_html_interfaces(
                    organization_uuid, search_term=search_term
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_portal_error_to_message(exc, empty_fallback=_PORTAL_READ_FAILED)
                )
            return build_success_payload(
                {"interfaces": interfaces}, include_parsed=True
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=True),
        )
        async def get_interface_html(
            ctx: Context,
            interface_uuid: str,
        ) -> dict[str, Any]:
            """Fetch an HTML interface with each ``customCode`` element's live HTML.

            Returns uuid, name, visibility, ``contentModeHtml``, and pages (each
            with elements carrying ``dataSources`` and ``htmlDocument``: ``content``,
            ``contentHash``, ``createdAt``). Raises on a grid-layout interface; use
            ``get_portal`` for those. The response includes both ``result``
            (pretty-printed JSON string) and ``data`` (parsed dict) for convenience.

            Args:
                interface_uuid: HTML interface UUID.
            """
            client = get_pipefy_client(ctx)
            interface_uuid, err = validate_tool_id(interface_uuid, "interface_uuid")
            if err is not None:
                return err
            await ctx.debug(f"get_interface_html: interface_uuid={interface_uuid}")
            try:
                interface = await client.get_html_interface(interface_uuid)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_portal_error_to_message(exc, empty_fallback=_PORTAL_READ_FAILED)
                )
            return build_success_payload(interface, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
        )
        async def write_interface_html(
            ctx: Context,
            page_id: str,
            element_id: str,
            content: str,
        ) -> dict[str, Any]:
            """Write and publish the HTML of an HTML interface's ``customCode`` element.

            Call ``get_interface_html_guidelines`` first: it returns the allowed
            tags and attributes, every forbidden construct with its violation code,
            the ``data-pfy-*`` vocabulary, and the filter-tree format. Read the
            element with ``get_interface_html`` before writing to it, since this
            replaces its whole document. On ``HTML_VALIDATION_FAILED``, nothing is
            stored; fix every listed violation and retry with the corrected HTML.

            Args:
                page_id: Page holding the element (``get_interface_html``
                    ``pages[].uuid``).
                element_id: The page's ``customCode`` element
                    (``pages[].elements[].uuid``).
                content: The whole HTML document; it replaces the live one.
            """
            client = get_pipefy_client(ctx)
            cleaned, err = validate_tool_ids(
                {"page_id": page_id, "element_id": element_id}
            )
            if err is not None:
                return err
            page_id = cleaned["page_id"]
            element_id = cleaned["element_id"]
            if not isinstance(content, str) or not content.strip():
                return tool_error(
                    "Invalid 'content': must be a non-empty string.",
                    code="INVALID_ARGUMENTS",
                )
            await ctx.debug(
                f"write_interface_html: page_id={page_id}, element_id={element_id}"
            )
            try:
                result = await client.write_html_document(
                    page_id=page_id, element_id=element_id, content=content
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(result, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
        )
        async def create_html_interface(
            ctx: Context,
            organization_uuid: PipefyId,
            name: str,
            html: str,
            data_sources: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            """Create an HTML interface and write its first page in one call.

            Call ``get_interface_html_guidelines`` first: it returns the allowed
            tags and attributes, every forbidden construct with its violation code,
            the ``data-pfy-*`` vocabulary, and the filter-tree format. Fix every
            listed violation before retrying; this is two API calls under the
            hood (create, then write), so a validation failure on the second
            leaves the interface created with a blank page. The error then
            includes ``uuid``, ``page_id`` and ``element_id``: retry the write
            with ``write_interface_html`` using those ids, instead of calling
            this tool again, which would create a second, orphaned interface.

            ``data_sources`` binds the page's one element, which is always
            ``customCode`` (optional; omit for none): ``{"id", "name", "repoId",
            "fieldKeys", "filters"}``.

            - ``id``: the handle the page's HTML reads the source by; ``name``:
              its label. Both unique within the element.
            - ``repoId``: a repo ``uuid`` from ``list_interface_repos``.
            - ``fieldKeys``: 1 to 30 keys, custom field uuids from
              ``get_interface_repo_fields`` and built-in keys such as ``title``.
            - ``filters``: optional filter tree in the format
              ``get_interface_html_guidelines`` describes, or null.

            At most 10 sources.

            Args:
                organization_uuid: Organization UUID, or numeric organization id.
                name: Interface name; also used as the one page's title.
                html: The page's whole HTML document.
                data_sources: The page's element's source bindings.
            """
            client = get_pipefy_client(ctx)
            organization_uuid, err = validate_tool_id(
                organization_uuid, "organization_uuid"
            )
            if err is not None:
                return err
            if not isinstance(name, str) or not name.strip():
                return tool_error(
                    "Invalid 'name': must be a non-empty string.",
                    code="INVALID_ARGUMENTS",
                )
            name = name.strip()
            if not isinstance(html, str) or not html.strip():
                return tool_error(
                    "Invalid 'html': must be a non-empty string.",
                    code="INVALID_ARGUMENTS",
                )
            try:
                sources = InterfaceDataSources.model_validate(data_sources or [])
            except ValidationError as exc:
                return interface_sources_validation_error(exc)
            await ctx.debug(
                f"create_html_interface: organization_uuid={organization_uuid}, "
                f"name={name}"
            )
            try:
                interface = await client.create_interface(
                    organization_uuid, name, data_sources=sources.root
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(
                    map_interface_source_error_to_message(
                        exc,
                        not_found_message=(
                            "One of the data sources' repoId was not found."
                        ),
                    )
                )
            pages = interface.get("pages") or []
            elements = pages[0].get("elements") if pages else None
            if not pages or not elements:
                return tool_error(
                    "createInterface returned no page to write HTML into.",
                    details={"uuid": interface.get("uuid")},
                )
            page_id = pages[0]["uuid"]
            element_id = elements[0]["uuid"]
            try:
                await client.write_html_document(
                    page_id=page_id, element_id=element_id, content=html
                )
            except Exception as exc:  # noqa: BLE001
                interface_uuid = interface.get("uuid")
                guidance = (
                    f"The interface ({interface_uuid}) was already created with a "
                    "blank page. Fix the HTML and call write_interface_html with "
                    f"page_id={page_id!r} and element_id={element_id!r} "
                    "(also in details); do not call create_html_interface again, "
                    "which would create a second, orphaned interface."
                )
                return tool_error(
                    f"{map_portal_error_to_message(exc)}\n\n{guidance}",
                    details={
                        "uuid": interface_uuid,
                        "page_id": page_id,
                        "element_id": element_id,
                    },
                )
            return build_success_payload(interface, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def create_portal(
            ctx: Context,
            organization_uuid: PipefyId,
        ) -> dict[str, Any]:
            """Create or fetch the organization's main portal (idempotent).

            Uses the same template bootstrap as the Pipefy product
            (``findOrCreateInterfaceByTemplate``). Each organization allows at most
            one main portal; a second call returns the existing portal UUID.

            Args:
                organization_uuid: Organization UUID, or numeric organization id.
            """
            client = get_pipefy_client(ctx)
            organization_uuid, err = validate_tool_id(
                organization_uuid, "organization_uuid"
            )
            if err is not None:
                return err
            await ctx.debug(f"create_portal: organization_uuid={organization_uuid}")
            try:
                portal = await client.create_portal(organization_uuid)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(portal, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def update_portal(
            ctx: Context,
            portal_uuid: str,
            name: str | None = None,
            visibility: PortalVisibility | None = None,
            color: str | None = None,
            icon: str | None = None,
            display_pipefy_header: bool | None = None,
        ) -> dict[str, Any]:
            """Update portal metadata (name, visibility, theme).

            Pass only fields you want to change. ``visibility`` must be one of
            ``internal``, ``private``, or ``public``.

            Args:
                portal_uuid: Portal interface UUID.
                name: Optional display name.
                visibility: ``internal``, ``private``, or ``public``.
                color: Optional theme color.
                icon: Optional icon identifier.
                display_pipefy_header: Whether to show the Pipefy header.
            """
            client = get_pipefy_client(ctx)
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            await ctx.debug(f"update_portal: portal_uuid={portal_uuid}")
            if all(
                x is None
                for x in (name, visibility, color, icon, display_pipefy_header)
            ):
                return tool_error(
                    "Provide at least one of: name, visibility, color, icon, "
                    "display_pipefy_header.",
                    code="INVALID_ARGUMENTS",
                )
            update_kwargs: dict[str, Any] = {}
            for field_name, raw_value in (
                ("name", name),
                ("color", color),
                ("icon", icon),
            ):
                cleaned, field_err = validate_portal_optional_string(
                    raw_value, field_name
                )
                if field_err is not None:
                    return field_err
                if cleaned is not None:
                    update_kwargs[field_name] = cleaned
            if visibility is not None:
                update_kwargs["visibility"] = visibility
            if display_pipefy_header is not None:
                update_kwargs["display_pipefy_header"] = display_pipefy_header
            try:
                portal = await client.update_portal(portal_uuid, **update_kwargs)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(portal, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
            ),
            meta=REMOTE,
        )
        async def delete_portal(
            ctx: Context,
            portal_uuid: str,
            confirm: bool = False,
            confirmation_token: str | None = None,
        ) -> dict[str, Any]:
            """Delete a portal interface (irreversible).

            Two-step operation: preview with ``confirm=False`` (default), then echo
            ``confirmation_token`` from the preview on step 2.

            Args:
                portal_uuid: Portal interface UUID to delete.
                confirm: Set to True with the preview token to execute the deletion (step 2).
                confirmation_token: Token from the preview response.
            """
            client = get_pipefy_client(ctx)
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            await ctx.debug(f"delete_portal: portal_uuid={portal_uuid}")
            guard = await check_destructive_confirmation(
                ctx,
                confirm=confirm,
                resource_descriptor=f"portal (UUID: {portal_uuid})",
                resource_identity={"portal_uuid": portal_uuid},
                tool_name="delete_portal",
                confirmation_token=confirmation_token,
            )
            if guard is not None:
                return guard

            try:
                result = await client.delete_portal(portal_uuid)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))

            delete_data = result.get("deleteInterface", {})
            if delete_data.get("success"):
                return build_success_payload(result, include_parsed=True)
            return build_error_payload(
                f"Failed to delete portal '{portal_uuid}'. "
                "Please try again or contact support."
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def create_portal_page(
            ctx: Context,
            portal_uuid: str,
            title: str,
            description: str | None = None,
            index: int | None = None,
        ) -> dict[str, Any]:
            """Create a portal page on the Interfaces schema.

            On an empty main portal skeleton, ``createPage`` without an ``elements``
            array often auto-provisions a templated page with multiple elements — the
            supported way to bootstrap a landing page when template create was skipped.

            Args:
                portal_uuid: Parent portal interface UUID.
                title: Page title.
                description: Optional page description.
                index: Optional sort index.
            """
            client = get_pipefy_client(ctx)
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            if not isinstance(title, str) or not title.strip():
                return tool_error(
                    "Invalid 'title': must be a non-empty string.",
                    code="INVALID_ARGUMENTS",
                )
            title = title.strip()
            description, desc_err = validate_portal_optional_string(
                description, "description"
            )
            if desc_err is not None:
                return desc_err
            index_err = validate_portal_page_index(index)
            if index_err is not None:
                return index_err
            await ctx.debug(
                f"create_portal_page: portal_uuid={portal_uuid}, title={title}"
            )
            try:
                page = await client.create_portal_page(
                    portal_uuid,
                    title,
                    description=description,
                    index=index,
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(page, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def update_portal_page(
            ctx: Context,
            portal_uuid: str,
            page_id: str,
            title: str | None = None,
            description: str | None = None,
            index: int | None = None,
        ) -> dict[str, Any]:
            """Update portal page metadata (title, description, sort index).

            Pass only fields you want to change.

            Args:
                portal_uuid: Parent portal interface UUID.
                page_id: Page UUID.
                title: Optional new title.
                description: Optional new description.
                index: Optional sort index.
            """
            client = get_pipefy_client(ctx)
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            await ctx.debug(
                f"update_portal_page: portal_uuid={portal_uuid}, page_id={page_id}"
            )
            if all(x is None for x in (title, description, index)):
                return tool_error(
                    "Provide at least one of: title, description, index.",
                    code="INVALID_ARGUMENTS",
                )
            update_kwargs: dict[str, Any] = {}
            cleaned_title, title_err = validate_portal_optional_string(title, "title")
            if title_err is not None:
                return title_err
            if cleaned_title is not None:
                update_kwargs["title"] = cleaned_title
            cleaned_description, desc_err = validate_portal_optional_string(
                description, "description"
            )
            if desc_err is not None:
                return desc_err
            if cleaned_description is not None:
                update_kwargs["description"] = cleaned_description
            index_err = validate_portal_page_index(index)
            if index_err is not None:
                return index_err
            if index is not None:
                update_kwargs["index"] = index
            try:
                page = await client.update_portal_page(
                    portal_uuid,
                    page_id,
                    **update_kwargs,
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(page, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
            ),
            meta=REMOTE,
        )
        async def delete_portal_page(
            ctx: Context,
            portal_uuid: str,
            page_id: str,
            confirm: bool = False,
            confirmation_token: str | None = None,
        ) -> dict[str, Any]:
            """Delete a portal page (irreversible).

            Two-step operation: preview with ``confirm=False`` (default), then echo
            ``confirmation_token`` from the preview on step 2.

            Args:
                portal_uuid: Parent portal interface UUID.
                page_id: Page UUID to delete.
                confirm: Set to True with the preview token to execute the deletion (step 2).
                confirmation_token: Token from the preview response.
            """
            client = get_pipefy_client(ctx)
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            await ctx.debug(
                f"delete_portal_page: portal_uuid={portal_uuid}, page_id={page_id}"
            )
            guard = await check_destructive_confirmation(
                ctx,
                confirm=confirm,
                resource_descriptor=(
                    f"portal page (UUID: {page_id}) in portal (UUID: {portal_uuid})"
                ),
                resource_identity={"page_id": page_id, "portal_uuid": portal_uuid},
                tool_name="delete_portal_page",
                confirmation_token=confirmation_token,
            )
            if guard is not None:
                return guard

            try:
                result = await client.delete_portal_page(portal_uuid, page_id)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))

            delete_data = result.get("deletePage", {})
            if delete_data.get("success"):
                return build_success_payload(result, include_parsed=True)
            return build_error_payload(
                f"Failed to delete portal page '{page_id}'. "
                "Please try again or contact support."
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def sort_portal_pages(
            ctx: Context,
            portal_uuid: str,
            page_ids: list[str],
        ) -> dict[str, Any]:
            """Reorder portal pages.

            Args:
                portal_uuid: Parent portal interface UUID.
                page_ids: Ordered list of page UUIDs (new sort order).
            """
            client = get_pipefy_client(ctx)
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            if not page_ids:
                return tool_error(
                    "Invalid 'page_ids': must be a non-empty list of page UUIDs.",
                    code="INVALID_ARGUMENTS",
                )
            cleaned_page_ids: list[str] = []
            for page_id in page_ids:
                cleaned_id, id_err = validate_tool_id(page_id, "page_ids")
                if id_err is not None:
                    return id_err
                cleaned_page_ids.append(cleaned_id)
            dup_err = validate_sort_page_ids_no_duplicates(cleaned_page_ids)
            if dup_err is not None:
                return dup_err
            await ctx.debug(
                f"sort_portal_pages: portal_uuid={portal_uuid}, "
                f"page_ids_count={len(cleaned_page_ids)}"
            )
            try:
                result = await client.sort_portal_pages(portal_uuid, cleaned_page_ids)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            if result.get("sortPages", {}).get("success"):
                return build_success_payload(result, include_parsed=True)
            return build_error_payload(
                "Failed to reorder portal pages. Please try again or contact support."
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def update_portal_page_layout(
            ctx: Context,
            page_id: str,
            layout: list[dict[str, Any]],
        ) -> dict[str, Any]:
            """Update a portal page grid layout.

            Uses ``updatePageLayout`` on the Interfaces schema. Does not require the
            parent portal UUID — only ``page_id`` and ``layout``.

            Args:
                page_id: Page UUID.
                layout: Full array from get_portal -> pages[].layout. Each row
                    needs a non-empty id, type "row", and children as non-empty
                    strings. [] is an empty page. Preserve row IDs and children,
                    changing only intended positions. Do not wrap it in an object
                    or infer positions from metadata.gridMap (element dimensions).
                    An incomplete row is rejected because the API stores this JSON
                    verbatim. Re-read to verify.
            """
            client = get_pipefy_client(ctx)
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            try:
                rows = parse_portal_page_layout(layout)
            except ValueError as exc:
                return tool_error(str(exc), code="INVALID_ARGUMENTS")
            await ctx.debug(f"update_portal_page_layout: page_id={page_id}")
            try:
                result = await client.update_portal_page_layout(page_id, rows)
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            if result.get("updatePageLayout", {}).get("success"):
                return build_success_payload(result, include_parsed=True)
            return build_error_payload(
                f"Failed to update layout for portal page '{page_id}'. "
                "Please try again or contact support."
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def create_portal_element(
            ctx: Context,
            page_id: str,
            type: PortalElementType,
            metadata: dict[str, Any],
            data_sources: list[dict[str, Any]] | None = None,
            element_id: str | None = None,
            editable: bool | None = None,
            layout: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            """Create a portal page element (portal "tool" / widget in the Pipefy UI).

            Validates ``type`` and ``metadata`` before calling the Interfaces API.
            For ``forms`` elements, include ``metadata.name`` and optional
            ``data_sources`` (``repoId`` + ``fieldKeys`` per Interfaces schema).

            To create and place in one call, read ``get_portal`` -> ``pages[].layout``,
            generate ``element_id``, and pass ``layout`` as the existing rows plus a
            row whose ``children`` list ``element_id``. Without ``layout`` the element
            exists but is not on the page grid. Re-read with ``get_portal`` after.

            Args:
                page_id: Parent page UUID.
                type: ``InterfacePageElementType`` value (e.g. ``forms``, ``link``).
                metadata: Element metadata JSON (shape depends on ``type``).
                data_sources: Optional data source bindings for ``forms`` elements.
                element_id: Optional client-provided element UUID. Required with
                    ``layout`` so a row can reference the new element.
                editable: Optional editable flag.
                layout: Optional full page layout row array (``id``, ``type: "row"``,
                    ``children``). Each row needs a non-empty id, type "row", and
                    children as non-empty strings. Preserve every existing row;
                    never send an object wrapper. The API stores this JSON verbatim,
                    so an incomplete row replaces the page grid and is rejected.
            """
            client = get_pipefy_client(ctx)
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            cleaned_element_id, element_id_err = validate_portal_optional_string(
                element_id, "element_id"
            )
            if element_id_err is not None:
                return element_id_err
            await ctx.debug(f"create_portal_element: page_id={page_id}, type={type}")
            try:
                validated = CreatePortalElementInput.model_validate(
                    {
                        "page_id": page_id,
                        "type": type,
                        "metadata": metadata,
                        "data_sources": data_sources or [],
                        "element_id": cleaned_element_id,
                        "editable": editable,
                        "layout": layout,
                    }
                )
            except ValidationError as exc:
                return portal_element_validation_error(exc)
            create_kwargs: dict[str, Any] = {
                "type": validated.type,
                "metadata": validated.metadata,
                "data_sources": validated.data_sources,
            }
            if validated.element_id is not None:
                create_kwargs["element_id"] = validated.element_id
            if validated.editable is not None:
                create_kwargs["editable"] = validated.editable
            if validated.layout is not None:
                create_kwargs["layout"] = validated.layout
            try:
                element = await client.create_portal_element(
                    validated.page_id,
                    **create_kwargs,
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(element, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def update_portal_element(
            ctx: Context,
            element_id: str,
            page_id: str,
            type: PortalElementType,
            metadata: dict[str, Any],
            data_sources: list[dict[str, Any]] | None = None,
            portal_uuid: str | None = None,
            editable: bool | None = None,
        ) -> dict[str, Any]:
            """Update a portal page element (full metadata replace).

            Pipefy treats ``metadata`` as a **complete replacement** on every update —
            send the full blob for the element type, not a partial patch. ``type`` is
            used only for client-side metadata validation.

            ``data_sources`` is a complete replacement too: ``[]`` unlinks the element
            from its pipe or table. To keep the current data sources, omit
            ``data_sources`` and pass ``portal_uuid``; the tool reads the element's
            ``dataSources`` and ``editable`` flag from the portal and sends them back.
            Every update passes one of the two, or it is rejected.

            The success payload ``metadata`` is the input echo (Interfaces
            ``updateElement`` returns only ``success``). Call ``get_portal`` for
            read-after-write state from Pipefy.

            Args:
                element_id: Element UUID.
                page_id: Parent page UUID.
                type: Element type for metadata validation.
                metadata: Complete metadata JSON for the element.
                data_sources: Data source bindings that replace the element's list,
                    each ``{"repoId": ..., "fieldKeys": [...]}`` as ``get_portal``
                    returns them. An element with no bindings can pass ``[]``,
                    which skips the portal read.
                portal_uuid: The portal you passed to ``get_portal`` whose
                    ``pages[]`` holds ``page_id``; required when ``data_sources``
                    is omitted.
                editable: Editable flag. The API requires it when a data source
                    lists ``fieldKeys``; the keep path resends the stored one.
            """
            client = get_pipefy_client(ctx)
            element_id, err = validate_tool_id(element_id, "element_id")
            if err is not None:
                return err
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            await ctx.debug(
                f"update_portal_element: element_id={element_id}, page_id={page_id}, "
                f"type={type}"
            )
            try:
                validated = UpdatePortalElementInput.model_validate(
                    {
                        "element_id": element_id,
                        "page_id": page_id,
                        "type": type,
                        "metadata": metadata,
                        "data_sources": data_sources,
                        "portal_uuid": portal_uuid,
                        "editable": editable,
                    }
                )
            except ValidationError as exc:
                return portal_element_validation_error(exc)
            update_kwargs: dict[str, Any] = {
                "type": validated.type,
                "metadata": validated.metadata,
                "data_sources": validated.data_sources,
                "portal_uuid": validated.portal_uuid,
            }
            if validated.editable is not None:
                update_kwargs["editable"] = validated.editable
            try:
                element = await client.update_portal_element(
                    validated.element_id,
                    validated.page_id,
                    **update_kwargs,
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(element, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
            ),
            meta=REMOTE,
        )
        async def delete_portal_element(
            ctx: Context,
            element_id: str,
            page_id: str,
            layout: list[dict[str, Any]] | None = None,
            confirm: bool = False,
            confirmation_token: str | None = None,
        ) -> dict[str, Any]:
            """Delete a portal page element (irreversible).

            Two-step operation: preview with ``confirm=False`` (default), then echo
            ``confirmation_token`` from the preview on step 2.

            Without ``layout`` the page grid keeps any row reference to the deleted
            element, and an orphan reference can break the portal viewer (HTTP
            500). Read ``get_portal`` -> ``pages[].layout``, remove ``element_id``
            from every row's ``children``, and pass the complete array as
            ``layout`` to prune the grid in the same call. Re-read after.

            Args:
                element_id: Element UUID to delete.
                page_id: Parent page UUID.
                layout: Optional full page layout row array with ``element_id``
                    removed. Each row needs a non-empty id, type "row", and
                    children as non-empty strings; a row still listing
                    ``element_id`` is rejected. Send the same rows on both steps.
                confirm: Set to True with the preview token to execute the deletion (step 2).
                confirmation_token: Token from the preview response.
            """
            client = get_pipefy_client(ctx)
            element_id, err = validate_tool_id(element_id, "element_id")
            if err is not None:
                return err
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            try:
                validated = DeletePortalElementInput.model_validate(
                    {"element_id": element_id, "page_id": page_id, "layout": layout}
                )
            except ValidationError as exc:
                return portal_element_validation_error(exc)
            await ctx.debug(
                f"delete_portal_element: element_id={element_id}, page_id={page_id}"
            )
            confirmation = plan_portal_element_delete_confirmation(validated)
            guard = await check_destructive_confirmation(
                ctx,
                confirm=confirm,
                resource_descriptor=confirmation.resource_descriptor,
                resource_identity=confirmation.resource_identity,
                tool_name="delete_portal_element",
                confirmation_token=confirmation_token,
            )
            if guard is not None:
                return guard

            delete_kwargs: dict[str, Any] = {}
            if validated.layout is not None:
                delete_kwargs["layout"] = validated.layout
            try:
                result = await client.delete_portal_element(
                    validated.element_id, validated.page_id, **delete_kwargs
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))

            delete_data = result.get("deleteElement", {})
            if delete_data.get("success"):
                return build_success_payload(result, include_parsed=True)
            return build_error_payload(
                f"Failed to delete portal element '{element_id}'. "
                "Please try again or contact support."
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def duplicate_portal_element(
            ctx: Context,
            element_id: str,
            portal_uuid: str,
            page_id: str,
        ) -> dict[str, Any]:
            """Duplicate a portal page element on the same page.

            Uses ``duplicateElement`` on the Interfaces schema (camelCase input).
            ``portal_uuid`` and ``page_id`` must be the portal/page where the
            source element already exists; Pipefy appends a copy on that page.

            Args:
                element_id: Element UUID to duplicate.
                portal_uuid: Portal interface UUID that owns the page.
                page_id: Page UUID that contains the element.
            """
            client = get_pipefy_client(ctx)
            element_id, err = validate_tool_id(element_id, "element_id")
            if err is not None:
                return err
            portal_uuid, err = validate_tool_id(portal_uuid, "portal_uuid")
            if err is not None:
                return err
            page_id, err = validate_tool_id(page_id, "page_id")
            if err is not None:
                return err
            await ctx.debug(
                f"duplicate_portal_element: element_id={element_id}, "
                f"portal_uuid={portal_uuid}, page_id={page_id}"
            )
            try:
                element = await client.duplicate_portal_element(
                    element_id=element_id,
                    portal_uuid=portal_uuid,
                    page_id=page_id,
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(element, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def create_sub_portal(
            ctx: Context,
            main_portal_uuid: str,
            name: str | None = None,
        ) -> dict[str, Any]:
            """Create a sub-portal under a main portal (Interfaces API).

            Main portals are always ``published: true``. Public access to the
            hub is ``update_portal(visibility="public")``, not sub-portal flags.
            Sub-portal visibility appears on ``get_portal`` ->
            ``subPortals[].published`` after attach/publish.

            Args:
                main_portal_uuid: Parent main portal interface UUID.
                name: Optional display name.
            """
            client = get_pipefy_client(ctx)
            main_portal_uuid, err = validate_tool_id(
                main_portal_uuid, "main_portal_uuid"
            )
            if err is not None:
                return err
            cleaned_name, name_err = validate_portal_optional_string(name, "name")
            if name_err is not None:
                return name_err
            await ctx.debug(f"create_sub_portal: main_portal_uuid={main_portal_uuid}")
            try:
                sub_portal = await client.create_sub_portal(
                    main_portal_uuid,
                    cleaned_name,
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))
            return build_success_payload(sub_portal, include_parsed=True)

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def update_sub_portal_element(
            ctx: Context,
            portal_uuid: str,
            element_id: str,
            sub_portal_uuid: str,
        ) -> dict[str, Any]:
            """Attach a sub-portal to a main portal page element.

            Uses ``updateSubPortalElement`` (internal API) on an existing page
            slot (typically a ``forms`` element). Main portal ``published`` is
            always true; use ``update_portal(visibility="public")`` for public
            hub access. Check ``get_portal`` -> ``subPortals[].published`` for
            sub-portal visibility after attach.

            Args:
                portal_uuid: Main portal interface UUID.
                element_id: Page element UUID (e.g. templated ``forms`` slot).
                sub_portal_uuid: Sub-portal UUID to attach.
            """
            client = get_pipefy_client(ctx)
            return await run_sub_portal_internal_api_tool(
                ids={
                    "portal_uuid": portal_uuid,
                    "element_id": element_id,
                    "sub_portal_uuid": sub_portal_uuid,
                },
                debug_message=(
                    "update_sub_portal_element: portal_uuid={portal_uuid}, "
                    "element_id={element_id}, sub_portal_uuid={sub_portal_uuid}"
                ),
                ctx_debug=ctx.debug,
                invoke=lambda ids: client.update_sub_portal_element(
                    ids["portal_uuid"],
                    ids["element_id"],
                    ids["sub_portal_uuid"],
                ),
                mutation_key="updateSubPortalElement",
                failure_message=(
                    "Failed to attach sub-portal '{sub_portal_uuid}' to element "
                    "'{element_id}'. Please try again or contact support."
                ),
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def publish_sub_portal(
            ctx: Context,
            portal_uuid: str,
            element_id: str,
            sub_portal_uuid: str,
        ) -> dict[str, Any]:
            """Publish a sub-portal on a main portal page element.

            Wires ``updateSubPortalElement`` with ``subPortalUuid`` on an
            existing page slot. Confirm visibility via ``get_portal`` ->
            ``subPortals[].published`` (main portal ``published`` stays true).

            Args:
                portal_uuid: Main portal interface UUID.
                element_id: Page element UUID (e.g. templated ``forms`` slot).
                sub_portal_uuid: Sub-portal UUID to publish on the element.
            """
            client = get_pipefy_client(ctx)
            return await run_sub_portal_internal_api_tool(
                ids={
                    "portal_uuid": portal_uuid,
                    "element_id": element_id,
                    "sub_portal_uuid": sub_portal_uuid,
                },
                debug_message=(
                    "publish_sub_portal: portal_uuid={portal_uuid}, "
                    "element_id={element_id}, sub_portal_uuid={sub_portal_uuid}"
                ),
                ctx_debug=ctx.debug,
                invoke=lambda ids: client.publish_sub_portal(
                    ids["portal_uuid"],
                    ids["element_id"],
                    ids["sub_portal_uuid"],
                ),
                mutation_key="updateSubPortalElement",
                failure_message=(
                    "Failed to publish sub-portal '{sub_portal_uuid}' on element "
                    "'{element_id}'. Please try again or contact support."
                ),
            )

        @mcp.tool(
            annotations=ToolAnnotations(readOnlyHint=False),
            meta=REMOTE,
        )
        async def unpublish_sub_portal(
            ctx: Context,
            portal_uuid: str,
            element_id: str,
        ) -> dict[str, Any]:
            """Unpublish a sub-portal from a main portal page element.

            Clears the sub-portal link via ``updateSubPortalElement`` with
            ``subPortalUuid: null``. Verify state with ``get_portal`` ->
            ``subPortals[].published``.

            Args:
                portal_uuid: Main portal interface UUID.
                element_id: Page element UUID to unpublish.
            """
            client = get_pipefy_client(ctx)
            return await run_sub_portal_internal_api_tool(
                ids={
                    "portal_uuid": portal_uuid,
                    "element_id": element_id,
                },
                debug_message=(
                    "unpublish_sub_portal: portal_uuid={portal_uuid}, "
                    "element_id={element_id}"
                ),
                ctx_debug=ctx.debug,
                invoke=lambda ids: client.unpublish_sub_portal(
                    ids["portal_uuid"],
                    ids["element_id"],
                ),
                mutation_key="updateSubPortalElement",
                failure_message=(
                    "Failed to unpublish sub-portal on element '{element_id}'. "
                    "Please try again or contact support."
                ),
            )

        @mcp.tool(
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
            ),
            meta=REMOTE,
        )
        async def delete_sub_portal_element(
            ctx: Context,
            portal_uuid: str,
            element_id: str,
            confirm: bool = False,
            confirmation_token: str | None = None,
        ) -> dict[str, Any]:
            """Detach sub-portal wiring from a main portal page element.

            Two-step operation: preview with ``confirm=False`` (default), then echo
            ``confirmation_token`` from the preview on step 2. Uses
            ``deleteSubPortalElement`` (internal API).

            Args:
                portal_uuid: Main portal interface UUID.
                element_id: Page element UUID to detach.
                confirm: Set to True with the preview token to execute the detach (step 2).
                confirmation_token: Token from the preview response.
            """
            client = get_pipefy_client(ctx)
            ids, err = validate_tool_ids(
                {"portal_uuid": portal_uuid, "element_id": element_id}
            )
            if err is not None or ids is None:
                return err or build_error_payload("Invalid tool IDs.")
            await ctx.debug(
                "delete_sub_portal_element: portal_uuid={portal_uuid}, "
                "element_id={element_id}".format(**ids)
            )
            guard = await check_destructive_confirmation(
                ctx,
                confirm=confirm,
                resource_descriptor=(
                    f"sub-portal element link (element UUID: {ids['element_id']}) "
                    f"in portal (UUID: {ids['portal_uuid']})"
                ),
                resource_identity={
                    "element_id": ids["element_id"],
                    "portal_uuid": ids["portal_uuid"],
                },
                tool_name="delete_sub_portal_element",
                confirmation_token=confirmation_token,
            )
            if guard is not None:
                return guard

            try:
                result = await client.delete_sub_portal_element(
                    ids["portal_uuid"],
                    ids["element_id"],
                )
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))

            return finalize_internal_api_mutation(
                result,
                "deleteSubPortalElement",
                (
                    "Failed to detach sub-portal from element '{element_id}'. "
                    "Please try again or contact support."
                ).format(**ids),
            )

        @mcp.tool(
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
            ),
            meta=REMOTE,
        )
        async def delete_sub_portal(
            ctx: Context,
            sub_portal_uuid: str,
            confirm: bool = False,
            confirmation_token: str | None = None,
        ) -> dict[str, Any]:
            """Delete a sub-portal entity (irreversible).

            Two-step operation: preview with ``confirm=False`` (default), then echo
            ``confirmation_token`` from the preview on step 2.
            Removes the sub-portal interface via ``deleteSubPortalInterface``.

            Args:
                sub_portal_uuid: Sub-portal UUID to delete permanently.
                confirm: Set to True with the preview token to execute the deletion (step 2).
                confirmation_token: Token from the preview response.
            """
            client = get_pipefy_client(ctx)
            ids, err = validate_tool_ids({"sub_portal_uuid": sub_portal_uuid})
            if err is not None or ids is None:
                return err or build_error_payload("Invalid tool IDs.")
            await ctx.debug(
                "delete_sub_portal: sub_portal_uuid={sub_portal_uuid}".format(**ids)
            )
            guard = await check_destructive_confirmation(
                ctx,
                confirm=confirm,
                resource_descriptor=f"sub-portal (UUID: {ids['sub_portal_uuid']})",
                resource_identity={"sub_portal_uuid": ids["sub_portal_uuid"]},
                tool_name="delete_sub_portal",
                confirmation_token=confirmation_token,
            )
            if guard is not None:
                return guard

            try:
                result = await client.delete_sub_portal(ids["sub_portal_uuid"])
            except Exception as exc:  # noqa: BLE001
                return build_error_payload(map_portal_error_to_message(exc))

            return finalize_internal_api_mutation(
                result,
                "deleteSubPortalInterface",
                (
                    "Failed to delete sub-portal '{sub_portal_uuid}'. "
                    "Please try again or contact support."
                ).format(**ids),
            )
