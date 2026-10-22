"""Service for Pipefy portal operations (Interfaces + Internal API routing)."""

from __future__ import annotations

import json
import logging
from typing import Any

from graphql import DocumentNode

from pipefy_sdk.exceptions import (
    HtmlValidationError,
    HtmlViolation,
    PortalPermissionError,
)
from pipefy_sdk.graphql_executor import GraphQLExecutor, PipefyGraphQLError
from pipefy_sdk.graphql_problem import (
    HTML_VALIDATION_FAILED_CODE,
    GraphQLProblemKind,
    classify_exception,
)
from pipefy_sdk.models.portal import (
    CreateInterfaceInput,
    CreatePortalElementInput,
    CreatePortalInput,
    DeletePortalElementInput,
    InterfaceDataSource,
    InterfaceDataSources,
    PortalElementType,
    PortalPageLayoutRow,
    UpdatePortalElementInput,
    UpdatePortalInput,
    parse_portal_page_layout,
)
from pipefy_sdk.queries.portal_internal_queries import (
    DELETE_SUB_PORTAL_ELEMENT_MUTATION,
    DELETE_SUB_PORTAL_INTERFACE_MUTATION,
    UPDATE_SUB_PORTAL_ELEMENT_MUTATION,
)
from pipefy_sdk.queries.portal_queries import (
    CREATE_ELEMENT_MUTATION,
    CREATE_INTERFACE_MUTATION,
    CREATE_PAGE_MUTATION,
    CREATE_SUB_PORTAL_MUTATION,
    DELETE_ELEMENT_MUTATION,
    DELETE_INTERFACE_MUTATION,
    DELETE_PAGE_MUTATION,
    DUPLICATE_ELEMENT_MUTATION,
    FIND_OR_CREATE_PORTAL_MUTATION,
    GET_HTML_INTERFACE_QUERY,
    GET_INTERFACE_HTML_GUIDELINES_QUERY,
    GET_INTERFACE_REPO_FIELDS_QUERY,
    GET_PORTAL_QUERY,
    LIST_INTERFACE_REPOS_QUERY,
    LIST_INTERFACES_QUERY,
    LIST_PORTALS_QUERY,
    SORT_PAGES_MUTATION,
    UPDATE_ELEMENT_MUTATION,
    UPDATE_INTERFACE_MUTATION,
    UPDATE_PAGE_LAYOUT_MUTATION,
    UPDATE_PAGE_MUTATION,
    WRITE_HTML_DOCUMENT_MUTATION,
)
from pipefy_sdk.utils.organization_identifiers import (
    numeric_organization_id,
    resolve_organization_uuid,
)
from pipefy_sdk.utils.relay import unwrap_relay_connection_nodes

logger = logging.getLogger(__name__)


def _with_uuid_alias(record: dict[str, Any]) -> dict[str, Any]:
    """Expose GraphQL ``id`` as ``uuid`` in portal payloads."""
    if "id" in record and "uuid" not in record:
        return {**record, "uuid": record["id"]}
    return record


_PORTAL_PERMISSION_MESSAGE = (
    "Permission denied. Request organization permissions such as "
    "`create_portal` or `manage_portals` from your admin."
)

# Largest page the Interfaces API returns per request.
_INTERFACES_PER_REQUEST = 50


def _map_portal_permission_error(
    exc: PipefyGraphQLError,
) -> PortalPermissionError | None:
    """Return ``PortalPermissionError`` for a permission-denied error; else ``None``.

    Delegates classification to the shared ``classify_exception`` so portal
    permission mapping reads the same ``extensions.code`` signal the rest of the
    SDK does, rather than re-deriving it here. Two consequences of sharing the
    classifier, neither observable on the single-error responses portal returns:
    it treats ``FORBIDDEN`` and ``UNAUTHORIZED`` as permission denied alongside
    ``PERMISSION_DENIED``, and it reads the first error only (see
    ``test_portal_permission_mapping_only_inspects_the_first_error``).
    """
    problem = classify_exception(exc)
    if problem is not None and problem.kind is GraphQLProblemKind.PERMISSION_DENIED:
        return PortalPermissionError(_PORTAL_PERMISSION_MESSAGE)
    return None


def _map_html_validation_error(
    exc: PipefyGraphQLError,
) -> HtmlValidationError | None:
    """Return an ``HtmlValidationError`` for an ``HTML_VALIDATION_FAILED`` error; else ``None``.

    The API puts each violation on ``extensions.violations`` of the first error.
    Entries that cannot form an ``HtmlViolation`` are skipped; an error with none
    left stays a plain ``PipefyGraphQLError``, whose message still says what failed.
    """
    first = exc.errors[0] if exc.errors else None
    if not isinstance(first, dict):
        return None
    extensions = first.get("extensions")
    if not isinstance(extensions, dict):
        return None
    code = extensions.get("code")
    if not isinstance(code, str) or code.strip().upper() != HTML_VALIDATION_FAILED_CODE:
        return None
    raw_violations = extensions.get("violations")
    if not isinstance(raw_violations, list):
        return None
    parsed = (
        HtmlViolation.from_extension(raw)
        for raw in raw_violations
        if isinstance(raw, dict)
    )
    violations = tuple(violation for violation in parsed if violation is not None)
    return HtmlValidationError(violations) if violations else None


def _serialize_interfaces_json(value: dict[str, Any] | list[Any]) -> str:
    """Encode Json scalars for the Interfaces GraphQL endpoint (gql expects strings)."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _serialize_layout_rows(rows: list[PortalPageLayoutRow]) -> str:
    """Encode parsed page rows, extra keys included, as an Interfaces Json scalar."""
    return _serialize_interfaces_json([row.model_dump() for row in rows])


def _filters_json_scalar(filters: dict[str, Any] | str) -> str:
    """Encode a source's filter tree as an Interfaces Json string; reads return one already."""
    return filters if isinstance(filters, str) else _serialize_interfaces_json(filters)


def _data_source_inputs(sources: InterfaceDataSources) -> list[dict[str, Any]]:
    """Map parsed sources to Interfaces ``DataSourceInput`` objects."""
    inputs: list[dict[str, Any]] = []
    for source in sources.root:
        entry = source.model_dump(by_alias=True, exclude={"filters"})
        if source.filters is not None:
            entry["filters"] = _filters_json_scalar(source.filters)
        inputs.append(entry)
    return inputs


def _require_update_success(
    data: dict[str, Any], *, element_id: str, page_id: str
) -> None:
    """Raise ``ValueError`` unless ``updateElement`` reported ``success``."""
    if not (data.get("updateElement") or {}).get("success"):
        msg = (
            f"updateElement returned success=false for element_id={element_id!r} "
            f"on page_id={page_id!r}."
        )
        raise ValueError(msg)


def _normalize_portal_data_sources(
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Map agent-friendly keys to Interfaces ``DataSourceInput``.

    ``repoId`` is the declared Interfaces input field (a pipe repo UUID). A source's
    ``id``, ``name`` and ``filters`` go through when set, since the API replaces the
    stored list with exactly what is sent. ``filters`` is sent as an Interfaces Json
    string; a string, as reads return it, goes through as is. Invalid entries are
    skipped and logged at warning level.
    """
    normalized: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            logger.warning(
                "Skipping portal data_sources[%s]: expected object, got %s",
                index,
                type(source).__name__,
            )
            continue
        repo_id = source.get("repoId")
        if not isinstance(repo_id, str) or not repo_id.strip():
            logger.warning(
                "Skipping portal data_sources[%s]: missing repo id "
                "(use repoId); keys=%s",
                index,
                sorted(source.keys()),
            )
            continue
        field_keys = source.get("fieldKeys")
        if field_keys is None:
            field_keys = source.get("field_keys", [])
        if not isinstance(field_keys, list):
            field_keys = []
        entry: dict[str, Any] = {
            key: source[key] for key in ("id", "name") if source.get(key) is not None
        }
        if source.get("filters") is not None:
            entry["filters"] = _filters_json_scalar(source["filters"])
        normalized.append({**entry, "repoId": repo_id.strip(), "fieldKeys": field_keys})
    return normalized


# TODO: delete this once #816/#817 merge; replace its one call site in
# create_interface with the InterfaceDataSource/InterfaceDataSources model
# they add, instead of this hand-rolled dict shape.
def _normalize_html_interface_data_sources(
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Map agent-friendly keys to ``DataSourceInput`` for a ``customCode`` element.

    Unlike ``_normalize_portal_data_sources`` (shared with ``create_portal_element``/
    ``update_portal_element``), this keeps ``id``, ``name`` and ``filters`` when the
    caller supplies them: a ``customCode`` element always requires ``id``/``name``
    on every source, so dropping them makes ``create_interface`` reject any non-empty
    ``data_sources`` outright. This is scoped to ``create_interface`` only; the two
    older tools keep their existing, unrelated behavior unchanged.
    """
    normalized: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            logger.warning(
                "Skipping html interface data_sources[%s]: expected object, got %s",
                index,
                type(source).__name__,
            )
            continue
        repo_id = source.get("repoId")
        if not isinstance(repo_id, str) or not repo_id.strip():
            logger.warning(
                "Skipping html interface data_sources[%s]: missing repo id "
                "(use repoId); keys=%s",
                index,
                sorted(source.keys()),
            )
            continue
        field_keys = source.get("fieldKeys")
        if not isinstance(field_keys, list):
            field_keys = []
        entry: dict[str, Any] = {"repoId": repo_id.strip(), "fieldKeys": field_keys}
        source_id = source.get("id")
        if isinstance(source_id, str) and source_id.strip():
            entry["id"] = source_id.strip()
        name = source.get("name")
        if isinstance(name, str) and name.strip():
            entry["name"] = name
        filters = source.get("filters")
        if filters is not None:
            entry["filters"] = _serialize_interfaces_json(filters)
        normalized.append(entry)
    return normalized


async def _execute_query_with_portal_errors(
    execute: Any,
    query: Any,
    variables: dict[str, Any],
) -> dict[str, Any]:
    """Run a portal operation and map PERMISSION_DENIED to ``PortalPermissionError``.

    Serves both the Interfaces and Internal API endpoints: each raises
    ``PipefyGraphQLError`` on GraphQL errors, and the PERMISSION_DENIED code lives
    in the structured ``errors`` regardless of endpoint.
    """
    try:
        return await execute(query, variables)
    except PipefyGraphQLError as exc:
        permission_error = _map_portal_permission_error(exc)
        if permission_error is not None:
            raise permission_error from exc
        raise


def _graphql_create_element_input(
    validated: CreatePortalElementInput,
) -> dict[str, Any]:
    """Map validated create input to Interfaces ``createElement`` variables."""
    payload: dict[str, Any] = {
        "page_id": validated.page_id,
        "type": validated.type,
        "metadata": _serialize_interfaces_json(validated.metadata),
    }
    # Always send data_sources (even []): the API fails the create when it is omitted.
    payload["data_sources"] = _normalize_portal_data_sources(validated.data_sources)
    if validated.element_id is not None:
        payload["id"] = validated.element_id
    if validated.editable is not None:
        payload["editable"] = validated.editable
    if validated.layout is not None:
        payload["layout"] = _serialize_layout_rows(validated.layout)
    return payload


def _graphql_update_element_input(
    validated: UpdatePortalElementInput,
) -> dict[str, Any]:
    """Map validated update input to Interfaces ``updateElement`` variables."""
    payload: dict[str, Any] = {
        "element_id": validated.element_id,
        "page_id": validated.page_id,
        "metadata": _serialize_interfaces_json(validated.metadata),
    }
    payload["data_sources"] = _normalize_portal_data_sources(validated.data_sources)
    if validated.editable is not None:
        payload["editable"] = validated.editable
    return payload


def _with_parsed_data_source_filters(element: dict[str, Any]) -> dict[str, Any]:
    """Parse each data source's ``filters`` back into a dict when read as a JSON string.

    Writes accept ``filters`` as a dict and serialize it before sending (the
    Interfaces Json scalar rides the wire as a string); reads otherwise hand
    that same string straight back, so a value an agent reads is rejected if
    copied unchanged into a write (``must be a JSON object``).
    """
    sources = element.get("dataSources")
    if not isinstance(sources, list):
        return element
    parsed_sources: list[Any] = []
    for source in sources:
        if not isinstance(source, dict):
            parsed_sources.append(source)
            continue
        filters = source.get("filters")
        if isinstance(filters, str):
            try:
                source = {**source, "filters": json.loads(filters)}
            except ValueError:
                pass
        parsed_sources.append(source)
    return {**element, "dataSources": parsed_sources}


def _normalize_portal_page(page: dict[str, Any]) -> dict[str, Any]:
    """Normalize a portal page payload with ``uuid`` alias and element ids."""
    page_record = _with_uuid_alias(page)
    elements = [
        _with_parsed_data_source_filters(_with_uuid_alias(element))
        for element in page.get("elements") or []
    ]
    return {**page_record, "elements": elements}


def _normalize_portal_detail(portal: dict[str, Any]) -> dict[str, Any]:
    """Normalize a ``PortalInterface`` detail payload from the Interfaces schema."""
    pages = portal.get("pages") or []
    normalized_pages = []
    for page in pages:
        page_record = _with_uuid_alias(page)
        elements = [_with_uuid_alias(element) for element in page.get("elements") or []]
        normalized_pages.append({**page_record, "elements": elements})
    sub_portals = [
        _with_uuid_alias(sub_portal) for sub_portal in portal.get("subPortals") or []
    ]
    return {
        **_with_uuid_alias(portal),
        "pages": normalized_pages,
        "subPortals": sub_portals,
    }


def _normalize_html_interface_detail(interface: dict[str, Any]) -> dict[str, Any]:
    """Normalize an HTML interface payload with ``uuid`` aliases on pages and elements."""
    pages = [_normalize_portal_page(page) for page in interface.get("pages") or []]
    return {**_with_uuid_alias(interface), "pages": pages}


def _element_on_page(
    interface: dict[str, Any],
    *,
    interface_kind: str,
    interface_uuid: str,
    page_id: str,
    element_id: str,
    not_found_hint: str,
) -> dict[str, Any]:
    """Return element ``element_id`` of page ``page_id`` of an interface payload.

    Raises:
        ValueError: The element is on another page (the message names it), or on
            no page (the message ends with ``not_found_hint``).
    """
    for page in interface["pages"]:
        for element in page["elements"]:
            if element["id"] != element_id:
                continue
            if page["id"] == page_id:
                return element
            msg = (
                f"Element '{element_id}' is on page '{page['id']}' of "
                f"{interface_kind} '{interface_uuid}', not on page '{page_id}'. "
                f"Pass page_id='{page['id']}'."
            )
            raise ValueError(msg)
    msg = (
        f"Element '{element_id}' is on no page of {interface_kind} "
        f"'{interface_uuid}'. {not_found_hint}"
    )
    raise ValueError(msg)


def _stored_element(
    portal: dict[str, Any], *, portal_uuid: str, page_id: str, element_id: str
) -> dict[str, Any]:
    """Return element ``element_id`` from page ``page_id`` of a ``get_portal`` payload.

    Raises:
        ValueError: The element is on another page, or on no page of the portal.
    """
    return _element_on_page(
        portal,
        interface_kind="portal",
        interface_uuid=portal_uuid,
        page_id=page_id,
        element_id=element_id,
        not_found_hint=(
            "Check portal_uuid and element_id, or pass data_sources to skip the read."
        ),
    )


def _stored_custom_code_element(
    interface: dict[str, Any], *, interface_uuid: str, page_id: str, element_id: str
) -> dict[str, Any]:
    """Return ``customCode`` element ``element_id`` of page ``page_id`` of an HTML interface.

    Raises:
        ValueError: The element is on another page or on no page, or is not
            ``customCode``.
    """
    element = _element_on_page(
        interface,
        interface_kind="interface",
        interface_uuid=interface_uuid,
        page_id=page_id,
        element_id=element_id,
        not_found_hint="get_html_interface lists its pages and elements.",
    )
    if element["type"] != "customCode":
        msg = (
            f"Element '{element_id}' is a '{element['type']}' element; named data "
            "sources go on an HTML interface's customCode element."
        )
        raise ValueError(msg)
    return element


class PortalService:
    """GraphQL operations for Pipefy portals across multiple endpoints.

    Takes three executors because portal operations span three endpoints: the
    public GraphQL schema, the Interfaces schema, and the internal_api endpoint
    for sub-portal wiring. The executors are injected, not built here; the
    composition root constructs all three over one shared ``auth`` so the OAuth
    token cache is not duplicated.
    """

    def __init__(
        self,
        *,
        public_executor: GraphQLExecutor,
        interfaces_executor: GraphQLExecutor,
        internal_executor: GraphQLExecutor,
    ) -> None:
        """Wire the public, Interfaces, and Internal API executors.

        Args:
            public_executor: Public GraphQL executor (organization-uuid resolution).
            interfaces_executor: Executor aimed at the Interfaces schema endpoint.
            internal_executor: Executor for sub-portal element wiring mutations.
        """
        self._public_executor = public_executor
        self._interfaces_executor = interfaces_executor
        self._internal_executor = internal_executor

    async def execute_interfaces_query(
        self,
        query: DocumentNode,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a GraphQL query or mutation on the Interfaces schema.

        Args:
            query: Parsed GraphQL document (``gql()`` output).
            variables: Variable map for the operation.
        """
        return await self._interfaces_executor.execute_query(query, variables)

    async def execute_internal_api_query(
        self,
        query: DocumentNode,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a GraphQL query or mutation on the Internal API endpoint.

        Args:
            query: Parsed GraphQL document (``gql()`` output).
            variables: Variable map for the operation.
        """
        return await self._internal_executor.execute_query(query, variables)

    async def list_portals(
        self,
        organization_uuid: str | int,
        search_term: str | None = None,
    ) -> list[dict[str, Any]]:
        """List portals for an organization via the Interfaces schema.

        Args:
            organization_uuid: Organization UUID, or numeric organization id.
            search_term: Optional name filter forwarded as ``searchTerm``.
        """
        resolved_org_uuid = await resolve_organization_uuid(
            self._public_executor.execute_query,
            organization_uuid,
        )
        variables: dict[str, Any] = {
            "org_uuid": resolved_org_uuid,
            "filterBySubType": "portal",
        }
        if search_term is not None:
            variables["searchTerm"] = search_term
        data = await self.execute_interfaces_query(LIST_PORTALS_QUERY, variables)
        nodes = unwrap_relay_connection_nodes(data.get("interfaces"))
        return [_with_uuid_alias(node) for node in nodes]

    async def get_portal(self, portal_uuid: str) -> dict[str, Any]:
        """Fetch a portal by UUID including pages, elements, and sub-portals.

        Args:
            portal_uuid: Portal interface UUID.

        Raises:
            ValueError: When ``portalInterface`` resolves to null.
        """
        data = await self.execute_interfaces_query(
            GET_PORTAL_QUERY, {"uuid": portal_uuid}
        )
        portal = data.get("portalInterface")
        if portal is None:
            msg = f"Portal '{portal_uuid}' was not found."
            raise ValueError(msg)
        return _normalize_portal_detail(portal)

    async def list_html_interfaces(
        self,
        organization_uuid: str | int,
        search_term: str | None = None,
    ) -> list[dict[str, Any]]:
        """List an organization's HTML interfaces via the Interfaces schema.

        Queries plain interfaces (no sub type, so never portals) page by page and
        keeps the ones with ``contentModeHtml``; grid interfaces are dropped.

        Args:
            organization_uuid: Organization UUID, or numeric organization id.
            search_term: Optional name filter forwarded as ``searchTerm``.
        """
        resolved_org_uuid = await resolve_organization_uuid(
            self._public_executor.execute_query,
            organization_uuid,
        )
        variables: dict[str, Any] = {
            "org_uuid": resolved_org_uuid,
            "filterBySubType": "interface",
            "first": _INTERFACES_PER_REQUEST,
        }
        if search_term is not None:
            variables["searchTerm"] = search_term
        nodes = await self._all_connection_nodes(
            LIST_INTERFACES_QUERY, "interfaces", variables
        )
        return [_with_uuid_alias(node) for node in nodes if node.get("contentModeHtml")]

    async def _all_connection_nodes(
        self, query: DocumentNode, connection_field: str, variables: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Run an Interfaces connection query page by page and return every node."""
        nodes: list[dict[str, Any]] = []
        while True:
            data = await self.execute_interfaces_query(query, variables)
            connection = data.get(connection_field) or {}
            nodes.extend(unwrap_relay_connection_nodes(connection))
            page_info = connection.get("pageInfo") or {}
            end_cursor = page_info.get("endCursor")
            if not page_info.get("hasNextPage") or not end_cursor:
                return nodes
            variables = {**variables, "after": end_cursor}

    async def list_interface_repos(
        self,
        organization_id: str | int,
        *,
        interface_uuid: str | None = None,
        repo_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """List the pipes and tables an interface element can take as a data source.

        For a portal or sub-portal interface, these are the organization's findable
        published pipes; otherwise the published pipes and tables the caller
        administers. Results are ordered by name, and every page is followed.

        Args:
            organization_id: Numeric organization id; a uuid is rejected.
            interface_uuid: Interface the source is for; it decides which repos
                qualify, as above.
            repo_name: Case-insensitive part of the repo name.

        Returns:
            Repo nodes with ``id``, ``uuid``, ``suid``, ``name``, ``type`` (``Pipe``
            or ``Table``), ``icon``, ``color`` and ``noun``. A data source's
            ``repoId`` is the ``uuid``.

        Raises:
            ValueError: ``organization_id`` is not numeric; nothing is sent.
        """
        variables: dict[str, Any] = {
            "orgId": numeric_organization_id(organization_id),
            "first": _INTERFACES_PER_REQUEST,
        }
        if interface_uuid is not None:
            variables["interfaceUuid"] = interface_uuid
        if repo_name is not None:
            variables["repoName"] = repo_name
        return await self._all_connection_nodes(
            LIST_INTERFACE_REPOS_QUERY, "interfaceRepos", variables
        )

    async def get_interface_repo_fields(
        self, repo_uuid: str, *, interface_uuid: str | None = None
    ) -> list[dict[str, Any]]:
        """List a pipe's or table's custom fields, for an interface data source.

        A custom field's data source key is its ``uuid``. The built-in keys (such
        as ``title``, ``created_at`` and ``current_phase_id``) are not fields of
        the repo: ``get_interface_html_guidelines`` lists them as
        ``filters.fixedColumnNames``.

        Args:
            repo_uuid: The repo's uuid, as ``list_interface_repos`` returns it.
            interface_uuid: Interface the source is for; access to the repo is
                checked in its context.

        Returns:
            Fields with ``id``, ``uuid``, ``label``, ``type``, ``phaseId``,
            ``archived``, ``required``, ``options``, ``description``, ``helpText``
            and ``connectedRepoId``. Archived fields are included.

        Raises:
            ValueError: The response has no repo structure.
            PipefyGraphQLError: No repo has this uuid, or the caller cannot read it.
        """
        variables: dict[str, Any] = {"repoId": repo_uuid}
        if interface_uuid is not None:
            variables["interfaceId"] = interface_uuid
        data = await self.execute_interfaces_query(
            GET_INTERFACE_REPO_FIELDS_QUERY, variables
        )
        structure = data.get("interfacesRepoStructure")
        if structure is None:
            msg = f"Repo '{repo_uuid}' was not found."
            raise ValueError(msg)
        return structure["fields"]

    async def get_html_interface(self, interface_uuid: str) -> dict[str, Any]:
        """Fetch an HTML interface with each page's elements and live HTML documents.

        Each element carries ``dataSources`` (``id``, ``name``, ``filters``, ``repoId``,
        ``repoName``, ``repoType``, ``fieldKeys``) and ``htmlDocument`` (``content``,
        ``contentHash``, ``createdAt``); ``htmlDocument`` is null for an element that
        is not ``customCode`` or has no stored HTML yet.

        Args:
            interface_uuid: HTML interface UUID.

        Raises:
            PipefyGraphQLError: No interface has this uuid; the API answers a
                missing uuid with an error.
            ValueError: The interface is a grid interface, or the response has no
                interface.
        """
        data = await self.execute_interfaces_query(
            GET_HTML_INTERFACE_QUERY, {"uuid": interface_uuid}
        )
        interface = data.get("interface")
        if interface is None:
            msg = f"Interface '{interface_uuid}' was not found."
            raise ValueError(msg)
        if not interface.get("contentModeHtml"):
            msg = (
                f"Interface '{interface_uuid}' is not an HTML interface; "
                "use get_portal to read its elements."
            )
            raise ValueError(msg)
        return _normalize_html_interface_detail(interface)

    async def write_html_document(
        self, *, page_id: str, element_id: str, content: str
    ) -> dict[str, Any]:
        """Write and publish the HTML of an HTML interface's ``customCode`` element.

        Writing publishes: the new document goes live as soon as it is stored.

        Args:
            page_id: Page holding the element.
            element_id: The page's ``customCode`` element.
            content: The whole HTML document; it replaces the live one.

        Raises:
            HtmlValidationError: The HTML broke the API's HTML rules; nothing was
                stored, and ``violations`` lists every rule it broke.
            PortalPermissionError: The caller cannot update the interface.
            PipefyGraphQLError: No page has this id, or the element is not on the
                page; the API answers a missing target with an error.
        """
        try:
            return await _execute_query_with_portal_errors(
                self.execute_interfaces_query,
                WRITE_HTML_DOCUMENT_MUTATION,
                {
                    "input": {
                        "page_id": page_id,
                        "element_id": element_id,
                        "content": content,
                    }
                },
            )
        except PipefyGraphQLError as exc:
            validation_error = _map_html_validation_error(exc)
            if validation_error is not None:
                raise validation_error from exc
            raise

    async def set_interface_sources(
        self,
        page_id: str,
        element_id: str,
        data_sources: list[InterfaceDataSource | dict[str, Any]],
        *,
        interface_uuid: str,
    ) -> dict[str, Any]:
        """Replace the data sources of an HTML interface's ``customCode`` element.

        Reads the element first and sends its ``metadata`` and ``editable`` back
        unchanged, since the update replaces the metadata and fails a source with
        field keys when ``editable`` is missing.

        Args:
            page_id: Page holding the element.
            element_id: The page's ``customCode`` element.
            data_sources: The element's complete source list; ``[]`` removes them
                all. Each source has ``id`` (the handle the HTML reads it by),
                ``name``, ``repoId`` (a uuid from ``list_interface_repos``),
                ``fieldKeys`` (custom field uuids from ``get_interface_repo_fields``
                and built-in keys such as ``title``) and optional ``filters``.
            interface_uuid: HTML interface holding the page.

        Returns:
            The element ``id`` (and ``uuid``) and the ``dataSources`` as parsed and
            sent, each with ``filters`` as an object or ``None``. This echoes the
            input once ``updateElement`` reports success; it is not read back. Call
            ``get_html_interface`` for the stored sources.

        Raises:
            pydantic.ValidationError: ``data_sources`` breaks a source rule; nothing
                is sent.
            ValueError: The element is not on page ``page_id``, is not ``customCode``,
                or the update reports ``success=false``.
            PortalPermissionError: The caller cannot update the interface.
            PipefyGraphQLError: The caller cannot manage a repo that a new or
                widened source reads (the API answers "Permission denied" with no
                code); nothing is stored.
        """
        sources = InterfaceDataSources.model_validate(data_sources)
        element = _stored_custom_code_element(
            await self.get_html_interface(interface_uuid),
            interface_uuid=interface_uuid,
            page_id=page_id,
            element_id=element_id,
        )
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            UPDATE_ELEMENT_MUTATION,
            {
                "input": {
                    "element_id": element_id,
                    "page_id": page_id,
                    "metadata": _serialize_interfaces_json(element["metadata"]),
                    "editable": element["editable"],
                    "data_sources": _data_source_inputs(sources),
                }
            },
        )
        _require_update_success(data, element_id=element_id, page_id=page_id)
        return _with_uuid_alias(
            {"id": element_id, "dataSources": sources.model_dump(by_alias=True)}
        )

    async def get_interface_html_guidelines(self) -> dict[str, Any]:
        """Fetch the HTML/CSS rules and data-source filter format for ``customCode`` content.

        The rules are the same for every organization, so the query takes no
        argument.
        """
        data = await self.execute_interfaces_query(
            GET_INTERFACE_HTML_GUIDELINES_QUERY, {}
        )
        return data["interfaceHtmlGuidelines"]

    async def create_interface(
        self,
        organization_uuid: str | int,
        name: str,
        *,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create an HTML interface (``contentModeHtml``) with one ``customCode`` page.

        One ``createInterface`` call makes the interface, a page titled ``name``,
        and that page's single ``customCode`` element; ``write_html_document``
        then writes the page's HTML. ``data_sources`` always rides on the
        element, empty or not: the API fails the create when it is omitted.

        Args:
            organization_uuid: Organization UUID or numeric organization id.
            name: Interface name; also used as the one page's title.
            data_sources: Optional source bindings for the page's element
                (``repoId``, ``fieldKeys``, and, since a ``customCode`` element
                requires them, ``id`` and ``name``; optional ``filters``).

        Returns:
            Created interface summary with ``uuid`` alias for ``id``.
        """
        validated = CreateInterfaceInput.model_validate(
            {
                "organization_uuid": organization_uuid,
                "name": name,
                "data_sources": data_sources if data_sources is not None else [],
            }
        )
        resolved_org_uuid = await resolve_organization_uuid(
            self._public_executor.execute_query,
            validated.organization_uuid,
        )
        element = {
            "type": "customCode",
            "metadata": _serialize_interfaces_json({}),
            # Nested under pages[].elements[], this field is dataSources on the wire
            # (unlike createElement's top-level data_sources, which is snake_case).
            "dataSources": _normalize_html_interface_data_sources(
                validated.data_sources
            ),
        }
        page = {
            "title": validated.name,
            "layout": _serialize_interfaces_json([]),
            "elements": [element],
        }
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            CREATE_INTERFACE_MUTATION,
            {
                "input": {
                    "org_uuid": resolved_org_uuid,
                    "name": validated.name,
                    "contentModeHtml": True,
                    "pages": [page],
                }
            },
        )
        interface = (data.get("createInterface") or {}).get("interface")
        if not isinstance(interface, dict):
            msg = "createInterface returned no interface."
            raise ValueError(msg)
        pages = [_normalize_portal_page(p) for p in interface.get("pages") or []]
        return {**_with_uuid_alias(interface), "pages": pages}

    async def create_portal(self, organization_uuid: str | int) -> dict[str, Any]:
        """Create or fetch the organization's main portal (idempotent template flow).

        Args:
            organization_uuid: Organization UUID or numeric organization id.

        Returns:
            Portal interface summary with ``uuid`` alias for ``id``.
        """
        portal_input = CreatePortalInput.model_validate(
            {"organization_uuid": organization_uuid}
        )
        resolved_org_uuid = await resolve_organization_uuid(
            self._public_executor.execute_query,
            portal_input.organization_uuid,
        )
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            FIND_OR_CREATE_PORTAL_MUTATION,
            {"input": {"orgUuid": resolved_org_uuid, "subType": "portal"}},
        )
        interface = (data.get("findOrCreateInterfaceByTemplate") or {}).get("interface")
        if not isinstance(interface, dict):
            msg = "findOrCreateInterfaceByTemplate returned no interface."
            raise ValueError(msg)
        return _with_uuid_alias(interface)

    async def update_portal(
        self,
        interface_uuid: str,
        *,
        name: str | None = None,
        visibility: str | None = None,
        color: str | None = None,
        icon: str | None = None,
        display_pipefy_header: bool | None = None,
    ) -> dict[str, Any]:
        """Update portal metadata on the Interfaces schema.

        Args:
            interface_uuid: Portal interface UUID.
            name: Optional display name.
            visibility: ``internal``, ``private``, or ``public``.
            color: Optional theme color.
            icon: Optional icon identifier.
            display_pipefy_header: Whether to show the Pipefy header.
        """
        portal_input = UpdatePortalInput(
            interface_uuid=interface_uuid,
            name=name,
            visibility=visibility,
            color=color,
            icon=icon,
            display_pipefy_header=display_pipefy_header,
        )
        variables = {
            "input": portal_input.model_dump(
                exclude_unset=True,
                exclude_none=True,
                by_alias=True,
            )
        }
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            UPDATE_INTERFACE_MUTATION,
            variables,
        )
        interface = (data.get("updateInterface") or {}).get("interface")
        if not isinstance(interface, dict):
            msg = "updateInterface returned no interface."
            raise ValueError(msg)
        return _with_uuid_alias(interface)

    async def delete_portal(self, interface_uuid: str) -> dict[str, Any]:
        """Delete a portal interface (irreversible).

        Args:
            interface_uuid: Portal interface UUID.
        """
        return await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            DELETE_INTERFACE_MUTATION,
            {"input": {"interface_uuid": interface_uuid}},
        )

    async def create_portal_page(
        self,
        interface_uuid: str,
        title: str,
        *,
        description: str | None = None,
        index: int | None = None,
    ) -> dict[str, Any]:
        """Create a portal page on the Interfaces schema.

        On an empty main portal, ``createPage`` without ``elements`` may
        auto-provision a templated page with multiple default elements.

        Args:
            interface_uuid: Parent portal interface UUID.
            title: Page title.
            description: Optional page description.
            index: Optional sort index.
        """
        page_input: dict[str, Any] = {
            "interface_uuid": interface_uuid,
            "title": title,
        }
        if description is not None:
            page_input["description"] = description
        if index is not None:
            page_input["index"] = index
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            CREATE_PAGE_MUTATION,
            {"input": page_input},
        )
        page = (data.get("createPage") or {}).get("page")
        if not isinstance(page, dict):
            msg = "createPage returned no page."
            raise ValueError(msg)
        return _normalize_portal_page(page)

    async def update_portal_page(
        self,
        interface_uuid: str,
        page_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        index: int | None = None,
    ) -> dict[str, Any]:
        """Update portal page metadata.

        Args:
            interface_uuid: Parent portal interface UUID.
            page_id: Page UUID.
            title: Optional new title.
            description: Optional new description.
            index: Optional sort index.
        """
        page_input: dict[str, Any] = {
            "interface_uuid": interface_uuid,
            "page_id": page_id,
        }
        if title is not None:
            page_input["title"] = title
        if description is not None:
            page_input["description"] = description
        if index is not None:
            page_input["index"] = index
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            UPDATE_PAGE_MUTATION,
            {"input": page_input},
        )
        page = (data.get("updatePage") or {}).get("page")
        if not isinstance(page, dict):
            msg = "updatePage returned no page."
            raise ValueError(msg)
        return _normalize_portal_page(page)

    async def delete_portal_page(
        self, interface_uuid: str, page_id: str
    ) -> dict[str, Any]:
        """Delete a portal page (irreversible).

        Args:
            interface_uuid: Parent portal interface UUID.
            page_id: Page UUID.
        """
        return await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            DELETE_PAGE_MUTATION,
            {"input": {"interface_uuid": interface_uuid, "page_id": page_id}},
        )

    async def sort_portal_pages(
        self, interface_uuid: str, page_ids: list[str]
    ) -> dict[str, Any]:
        """Reorder portal pages by id list.

        Args:
            interface_uuid: Parent portal interface UUID.
            page_ids: Ordered list of page UUIDs.
        """
        return await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            SORT_PAGES_MUTATION,
            {"input": {"interface_uuid": interface_uuid, "page_ids": page_ids}},
        )

    async def update_portal_page_layout(
        self, page_id: str, layout: list[PortalPageLayoutRow | dict[str, Any]]
    ) -> dict[str, Any]:
        """Update a portal page grid layout (full layout blob).

        Args:
            page_id: Page UUID (no parent ``interface_uuid`` on this mutation).
            layout: Full row array from ``get_portal`` -> ``pages[].layout``, as
                dicts or parsed rows. ``[]`` is an empty page.

        Raises:
            ValueError: A row lacks a non-empty id, type ``"row"``, or children as
                non-empty strings.
        """
        rows = parse_portal_page_layout(layout)
        return await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            UPDATE_PAGE_LAYOUT_MUTATION,
            {
                "input": {
                    "page_id": page_id,
                    "layout": _serialize_layout_rows(rows),
                }
            },
        )

    async def create_portal_element(
        self,
        page_id: str,
        *,
        type: PortalElementType,
        metadata: dict[str, Any],
        data_sources: list[dict[str, Any]] | None = None,
        element_id: str | None = None,
        editable: bool | None = None,
        layout: list[PortalPageLayoutRow | dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a portal page element on the Interfaces schema.

        Args:
            page_id: Parent page UUID.
            type: One of the 15 ``InterfacePageElementType`` values.
            metadata: Element metadata JSON (validated per ``type``).
            data_sources: Optional data source bindings (e.g. for ``forms``).
            element_id: Optional client-provided element UUID (GraphQL ``id``).
            editable: Optional editable flag.
            layout: Optional full page layout row array (``get_portal`` ->
                ``pages[].layout``) with a row whose children list ``element_id``,
                to create and place in one call. Omit to leave the grid untouched.
        """
        validated = CreatePortalElementInput.model_validate(
            {
                "page_id": page_id,
                "type": type,
                "metadata": metadata,
                "data_sources": data_sources if data_sources is not None else [],
                "element_id": element_id,
                "editable": editable,
                "layout": layout,
            }
        )
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            CREATE_ELEMENT_MUTATION,
            {"input": _graphql_create_element_input(validated)},
        )
        element = (data.get("createElement") or {}).get("element")
        if not isinstance(element, dict):
            msg = "createElement returned no element."
            raise ValueError(msg)
        return _with_uuid_alias(element)

    async def update_portal_element(
        self,
        element_id: str,
        page_id: str,
        *,
        type: PortalElementType,
        metadata: dict[str, Any],
        data_sources: list[dict[str, Any]] | None = None,
        portal_uuid: str | None = None,
        editable: bool | None = None,
    ) -> dict[str, Any]:
        """Update a portal page element (full ``metadata`` replace).

        The returned ``metadata`` is the validated input echo: ``updateElement`` only
        returns ``success``, not the stored element. Use ``get_portal`` for a
        read-after-write view of what Pipefy persisted.

        Args:
            element_id: Element UUID.
            page_id: Parent page UUID.
            type: Element type for client-side metadata validation only.
            metadata: Complete metadata blob (Pipefy replaces the whole object).
            data_sources: Data source bindings that replace the element's list;
                ``[]`` unlinks them all. Omit, with ``portal_uuid``, to keep the
                current ones. A caller already holding the element from
                ``get_portal`` can pass its ``dataSources`` here (and its
                ``editable``) to skip the second read.
            portal_uuid: Portal holding the element. Required when ``data_sources``
                is omitted: the element's ``dataSources`` (``repoId`` and
                ``fieldKeys``) and, unless ``editable`` is given, its ``editable``
                flag are read from ``get_portal`` and sent back.
            editable: Editable flag. The API rejects an update whose data sources
                list ``fieldKeys`` without it; the keep path sends the stored one.

        Raises:
            ValueError: ``data_sources`` and ``portal_uuid`` are both omitted, or
                the element is not on page ``page_id`` of the portal.
            PipefyGraphQLError: Reading the portal failed (no update is sent).
            PortalPermissionError: The caller may not update the element.
        """
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
        if validated.data_sources is None:
            stored = _stored_element(
                await self.get_portal(validated.portal_uuid),
                portal_uuid=validated.portal_uuid,
                page_id=validated.page_id,
                element_id=validated.element_id,
            )
            kept: dict[str, Any] = {"data_sources": stored["dataSources"]}
            if validated.editable is None:
                kept["editable"] = stored["editable"]
            validated = validated.model_copy(update=kept)
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            UPDATE_ELEMENT_MUTATION,
            {"input": _graphql_update_element_input(validated)},
        )
        _require_update_success(data, element_id=element_id, page_id=page_id)
        return _with_uuid_alias(
            {
                "id": validated.element_id,
                "type": validated.type,
                "metadata": validated.metadata,
            }
        )

    async def delete_portal_element(
        self,
        element_id: str,
        page_id: str,
        *,
        layout: list[PortalPageLayoutRow | dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Delete a portal page element (irreversible).

        Args:
            element_id: Element UUID.
            page_id: Parent page UUID.
            layout: Optional full page layout row array with ``element_id`` removed
                from every row, written in the same call so no row is left
                pointing at the deleted element. Omit to leave the grid untouched.
        """
        validated = DeletePortalElementInput.model_validate(
            {"element_id": element_id, "page_id": page_id, "layout": layout}
        )
        variables: dict[str, Any] = {
            "element_id": validated.element_id,
            "page_id": validated.page_id,
        }
        if validated.layout is not None:
            variables["layout"] = _serialize_layout_rows(validated.layout)
        return await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            DELETE_ELEMENT_MUTATION,
            {"input": variables},
        )

    async def duplicate_portal_element(
        self,
        *,
        element_id: str,
        portal_uuid: str,
        page_id: str,
    ) -> dict[str, Any]:
        """Duplicate a portal page element on the same portal page.

        ``portal_uuid`` and ``page_id`` identify where the source element lives
        (not a cross-page destination). Pipefy appends a copy on that page.

        Args:
            element_id: Element UUID to duplicate.
            portal_uuid: Portal interface UUID that owns the page.
            page_id: Page UUID that contains the element.
        """
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            DUPLICATE_ELEMENT_MUTATION,
            {
                "input": {
                    "elementUuid": element_id,
                    "interfaceUuid": portal_uuid,
                    "pageUuid": page_id,
                }
            },
        )
        element = (data.get("duplicateElement") or {}).get("element")
        if not isinstance(element, dict):
            msg = "duplicateElement returned no element."
            raise ValueError(msg)
        return _with_uuid_alias(element)

    async def create_sub_portal(
        self,
        main_portal_uuid: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a sub-portal attached to a main portal (Interfaces schema).

        Args:
            main_portal_uuid: Parent main portal interface UUID.
            name: Optional display name; omitted from the mutation when ``None``.
        """
        portal_input: dict[str, Any] = {"mainPortalUuid": main_portal_uuid}
        if name is not None:
            portal_input["name"] = name
        data = await _execute_query_with_portal_errors(
            self.execute_interfaces_query,
            CREATE_SUB_PORTAL_MUTATION,
            {"input": portal_input},
        )
        sub_portal = (data.get("createSubPortal") or {}).get("subPortal")
        if not isinstance(sub_portal, dict):
            msg = "createSubPortal returned no subPortal."
            raise ValueError(msg)
        return _with_uuid_alias(sub_portal)

    async def update_sub_portal_element(
        self,
        portal_uuid: str,
        element_id: str,
        sub_portal_uuid: str,
    ) -> dict[str, Any]:
        """Attach a sub-portal to a portal page element (Internal API).

        Args:
            portal_uuid: Main portal interface UUID.
            element_id: Page element UUID (e.g. templated ``forms`` slot).
            sub_portal_uuid: Sub-portal UUID to wire to the element.
        """
        return await _execute_query_with_portal_errors(
            self.execute_internal_api_query,
            UPDATE_SUB_PORTAL_ELEMENT_MUTATION,
            {
                "input": {
                    "portalUuid": portal_uuid,
                    "elementId": element_id,
                    "subPortalUuid": sub_portal_uuid,
                }
            },
        )

    async def publish_sub_portal(
        self,
        portal_uuid: str,
        element_id: str,
        sub_portal_uuid: str,
    ) -> dict[str, Any]:
        """Publish a sub-portal on a page element via ``updateSubPortalElement``.

        Args:
            portal_uuid: Main portal interface UUID.
            element_id: Page element UUID.
            sub_portal_uuid: Sub-portal UUID to attach.
        """
        return await self.update_sub_portal_element(
            portal_uuid,
            element_id,
            sub_portal_uuid,
        )

    async def unpublish_sub_portal(
        self,
        portal_uuid: str,
        element_id: str,
    ) -> dict[str, Any]:
        """Unpublish a sub-portal from a page element via ``updateSubPortalElement``.

        Sends ``subPortalUuid: null`` to clear the link. Distinct from
        ``delete_sub_portal_element`` (removes the wiring slot) and
        ``delete_sub_portal`` (deletes the sub-portal entity).

        Args:
            portal_uuid: Main portal interface UUID.
            element_id: Page element UUID.
        """
        return await _execute_query_with_portal_errors(
            self.execute_internal_api_query,
            UPDATE_SUB_PORTAL_ELEMENT_MUTATION,
            {
                "input": {
                    "portalUuid": portal_uuid,
                    "elementId": element_id,
                    "subPortalUuid": None,
                }
            },
        )

    async def delete_sub_portal_element(
        self,
        portal_uuid: str,
        element_id: str,
    ) -> dict[str, Any]:
        """Remove sub-portal wiring from a page element (Internal API).

        Args:
            portal_uuid: Main portal interface UUID.
            element_id: Page element UUID.
        """
        return await _execute_query_with_portal_errors(
            self.execute_internal_api_query,
            DELETE_SUB_PORTAL_ELEMENT_MUTATION,
            {"input": {"portalUuid": portal_uuid, "elementId": element_id}},
        )

    async def delete_sub_portal(self, uuid: str) -> dict[str, Any]:
        """Delete a sub-portal entity (irreversible; Internal API).

        Args:
            uuid: Sub-portal UUID.
        """
        return await _execute_query_with_portal_errors(
            self.execute_internal_api_query,
            DELETE_SUB_PORTAL_INTERFACE_MUTATION,
            {"input": {"uuid": uuid}},
        )
