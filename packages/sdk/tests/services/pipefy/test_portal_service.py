"""Unit tests for PortalService multi-endpoint routing."""

from __future__ import annotations

import importlib
import json
import logging
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import call as mock_call

import pytest
from _shared.fixture_ids import (
    EXAMPLE_FIELD_INTERNAL_ID,
    EXAMPLE_NUMERIC_ORG_ID,
    EXAMPLE_ORG_UUID,
    EXAMPLE_OTHER_ORG_UUID,
    EXAMPLE_PHASE_ID,
    EXAMPLE_PIPE_ID,
    EXAMPLE_PIPE_ID_2,
    EXAMPLE_PIPE_REPO_ID,
)
from _shared.mock_clients import mock_executor
from gql import gql
from pydantic import ValidationError

from pipefy_sdk.exceptions import (
    HtmlValidationError,
    HtmlViolation,
    PortalPermissionError,
)
from pipefy_sdk.graphql_executor import PipefyGraphQLError
from pipefy_sdk.models.portal import InterfaceDataSource, parse_portal_page_layout
from pipefy_sdk.queries.observability_queries import RESOLVE_ORGANIZATION_UUID_QUERY
from pipefy_sdk.queries.portal_queries import (
    CREATE_INTERFACE_MUTATION,
    GET_HTML_INTERFACE_QUERY,
    GET_INTERFACE_HTML_GUIDELINES_QUERY,
    GET_INTERFACE_REPO_FIELDS_QUERY,
    GET_PORTAL_QUERY,
    LIST_INTERFACE_REPOS_QUERY,
    LIST_INTERFACES_QUERY,
    LIST_PORTALS_QUERY,
    UPDATE_ELEMENT_MUTATION,
    WRITE_HTML_DOCUMENT_MUTATION,
)
from pipefy_sdk.services.portal_service import PortalService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_interfaces_query_routes_through_interfaces_client() -> None:
    """Representative Interfaces call delegates to the Interfaces GraphQL executor."""
    interfaces = mock_executor({"interfaces": {"edges": []}})
    service = PortalService(
        public_executor=mock_executor(),
        interfaces_executor=interfaces,
        internal_executor=mock_executor(),
    )

    query = gql("query { interfaces(orgUuid: $orgUuid) { edges { node { uuid } } } }")
    variables = {"orgUuid": "org-123"}
    result = await service.execute_interfaces_query(query, variables)

    interfaces.execute_query.assert_called_once()
    call_query, call_vars = interfaces.execute_query.call_args[0]
    assert call_query == query
    assert call_vars == variables
    assert result == {"interfaces": {"edges": []}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sub_portal_element_call_routes_through_internal_api_client() -> None:
    """Sub-portal wiring mutations delegate to the internal GraphQL executor."""
    internal = mock_executor({"updateSubPortalElement": {}})
    service = PortalService(
        public_executor=mock_executor(),
        interfaces_executor=mock_executor(),
        internal_executor=internal,
    )

    query = gql(
        "mutation updateSubPortalElement($input: UpdateSubPortalElementInput!) "
        "{ updateSubPortalElement(input: $input) { success } }"
    )
    variables = {
        "input": {
            "portalUuid": "portal-uuid",
            "elementId": 42,
            "subPortalUuid": "sub-uuid",
        }
    }
    result = await service.execute_internal_api_query(query, variables)

    internal.execute_query.assert_called_once()
    call_query, call_vars = internal.execute_query.call_args[0]
    assert call_query == query
    assert call_vars == variables
    assert result == {"updateSubPortalElement": {}}


def _make_interfaces_service(return_value):
    public = mock_executor()
    interfaces = mock_executor(return_value)
    service = PortalService(
        public_executor=public,
        interfaces_executor=interfaces,
        internal_executor=mock_executor(),
    )
    return service, public, interfaces


_PORTAL_LIST_GRAPHQL_NODE = {
    "id": "portal-uuid-1",
    "name": "Main Portal",
    "visibility": "internal",
    "subType": "portal",
}

_PORTAL_LIST_NODE = {
    **_PORTAL_LIST_GRAPHQL_NODE,
    "uuid": "portal-uuid-1",
}

_PORTAL_DETAIL_GRAPHQL = {
    "id": "portal-uuid-1",
    "name": "Main Portal",
    "visibility": "public",
    "published": True,
    "pages": [
        {
            "id": "page-1",
            "title": "Home",
            "layout": [{"id": "row-1", "type": "row", "children": ["el-1"]}],
            "elements": [
                {
                    "id": "el-1",
                    "type": "forms",
                    "metadata": {"name": "Request form"},
                }
            ],
        }
    ],
    "subPortals": [{"id": "sub-1", "name": "Sub Portal 1", "published": False}],
}

_PORTAL_DETAIL = {
    **_PORTAL_DETAIL_GRAPHQL,
    "uuid": "portal-uuid-1",
    "pages": [
        {
            "id": "page-1",
            "uuid": "page-1",
            "title": "Home",
            "layout": [{"id": "row-1", "type": "row", "children": ["el-1"]}],
            "elements": [
                {
                    "id": "el-1",
                    "uuid": "el-1",
                    "type": "forms",
                    "metadata": {"name": "Request form"},
                }
            ],
        }
    ],
    "subPortals": [
        {"id": "sub-1", "uuid": "sub-1", "name": "Sub Portal 1", "published": False}
    ],
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_returns_portal_nodes() -> None:
    """list_portals unwraps Relay edges into a flat list of portal dicts."""
    response = {
        "interfaces": {
            "edges": [{"node": _PORTAL_LIST_GRAPHQL_NODE}],
        }
    }
    service, _public, _interfaces_executor = _make_interfaces_service(response)

    result = await service.list_portals(EXAMPLE_ORG_UUID)

    assert result == [_PORTAL_LIST_NODE]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_passes_org_uuid_and_portal_filter() -> None:
    """list_portals queries interfaces with org_uuid and filterBySubType portal."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )

    await service.list_portals(EXAMPLE_OTHER_ORG_UUID)

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert query_used is LIST_PORTALS_QUERY
    assert variables == {
        "org_uuid": EXAMPLE_OTHER_ORG_UUID,
        "filterBySubType": "portal",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_passes_search_term_when_provided() -> None:
    """Optional search_term is forwarded as searchTerm to the GraphQL query."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )

    await service.list_portals(EXAMPLE_ORG_UUID, search_term="intake")

    query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert query_used is LIST_PORTALS_QUERY
    assert variables == {
        "org_uuid": EXAMPLE_ORG_UUID,
        "filterBySubType": "portal",
        "searchTerm": "intake",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_empty_returns_empty_list() -> None:
    """When no portals exist, list_portals returns an empty list."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )

    result = await service.list_portals(EXAMPLE_ORG_UUID)

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_uuid_org_identifier_passes_through_unchanged() -> None:
    """UUID-shaped org identifiers skip resolve and go straight to Interfaces."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )
    public_executor.execute_query = AsyncMock()

    await service.list_portals(EXAMPLE_ORG_UUID)

    public_executor.execute_query.assert_not_called()
    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["org_uuid"] == EXAMPLE_ORG_UUID


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_numeric_org_id_resolves_via_main_graphql_client() -> None:
    """Numeric org ids resolve on the public GraphQL client before Interfaces list."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )
    public_executor.execute_query = AsyncMock(
        return_value={"organization": {"uuid": EXAMPLE_ORG_UUID}}
    )

    await service.list_portals(EXAMPLE_NUMERIC_ORG_ID)

    public_executor.execute_query.assert_called_once_with(
        RESOLVE_ORGANIZATION_UUID_QUERY,
        {"id": EXAMPLE_NUMERIC_ORG_ID},
    )
    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["org_uuid"] == EXAMPLE_ORG_UUID


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_accepts_int_org_id() -> None:
    """Integer org ids coerce to string before resolve and Interfaces list."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )
    public_executor.execute_query = AsyncMock(
        return_value={"organization": {"uuid": EXAMPLE_ORG_UUID}}
    )

    await service.list_portals(int(EXAMPLE_NUMERIC_ORG_ID))

    public_executor.execute_query.assert_called_once_with(
        RESOLVE_ORGANIZATION_UUID_QUERY,
        {"id": EXAMPLE_NUMERIC_ORG_ID},
    )
    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["org_uuid"] == EXAMPLE_ORG_UUID


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_rejects_empty_org_identifier() -> None:
    """Empty org identifiers raise ValueError before any GraphQL call."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )

    with pytest.raises(ValueError, match="must be non-empty"):
        await service.list_portals("   ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_rejects_invalid_org_identifier() -> None:
    """Non-UUID, non-numeric org identifiers raise ValueError."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )

    with pytest.raises(ValueError, match="must be a UUID or numeric id"):
        await service.list_portals("not-a-uuid-or-digits")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_portals_org_not_found_on_resolve_raises_value_error() -> None:
    """When resolve yields no uuid, list_portals raises ValueError."""
    service, public_executor, _interfaces_executor = _make_interfaces_service(
        {"interfaces": {"edges": []}},
    )
    public_executor.execute_query = AsyncMock(return_value={"organization": None})

    with pytest.raises(ValueError, match="Organization not found"):
        await service.list_portals(EXAMPLE_NUMERIC_ORG_ID)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_portal_returns_full_portal_shape() -> None:
    """get_portal returns portal metadata, pages, elements, and sub-portals."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"portalInterface": _PORTAL_DETAIL_GRAPHQL},
    )

    result = await service.get_portal("portal-uuid-1")

    assert result == _PORTAL_DETAIL
    assert result["published"] is True
    assert len(result["pages"]) == 1
    assert result["subPortals"][0]["uuid"] == "sub-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_portal_not_found_raises_value_error() -> None:
    """When portalInterface is null, get_portal raises ValueError with the UUID."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"portalInterface": None},
    )

    with pytest.raises(ValueError, match="portal-uuid-missing"):
        await service.get_portal("portal-uuid-missing")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_portal_uses_correct_variables() -> None:
    """get_portal passes the portal UUID as the uuid GraphQL variable."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"portalInterface": _PORTAL_DETAIL},
    )

    await service.get_portal("uuid-abc")

    query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert query_used is GET_PORTAL_QUERY
    assert variables == {"uuid": "uuid-abc"}


def _interfaces_page(nodes, *, has_next_page=False, end_cursor=None):
    """One ``interfaces`` connection page."""
    return {
        "interfaces": {
            "edges": [{"node": node} for node in nodes],
            "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
        }
    }


_HTML_INTERFACE_NODE = {
    "id": "html-uuid-1",
    "name": "Sales dashboard",
    "visibility": "internal",
    "contentModeHtml": True,
}

_SECOND_HTML_INTERFACE_NODE = {**_HTML_INTERFACE_NODE, "id": "html-uuid-2"}

_GRID_INTERFACE_NODE = {
    "id": "grid-uuid-1",
    "name": "Team board",
    "visibility": "internal",
    "contentModeHtml": False,
}

_LIST_INTERFACES_VARIABLES = {
    "org_uuid": EXAMPLE_ORG_UUID,
    "filterBySubType": "interface",
    "first": 50,
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_html_interfaces_returns_only_html_interfaces() -> None:
    """list_html_interfaces drops grid interfaces and aliases id as uuid."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        _interfaces_page([_HTML_INTERFACE_NODE, _GRID_INTERFACE_NODE]),
    )

    result = await service.list_html_interfaces(EXAMPLE_ORG_UUID)

    assert result == [{**_HTML_INTERFACE_NODE, "uuid": "html-uuid-1"}]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_html_interfaces_sends_interface_filter_page_size_and_search_term() -> (
    None
):
    service, _public, interfaces_executor = _make_interfaces_service(
        _interfaces_page([]),
    )

    await service.list_html_interfaces(EXAMPLE_ORG_UUID, search_term="sales")

    interfaces_executor.execute_query.assert_awaited_once_with(
        LIST_INTERFACES_QUERY, {**_LIST_INTERFACES_VARIABLES, "searchTerm": "sales"}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_html_interfaces_returns_html_interfaces_from_a_later_page() -> None:
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        _interfaces_page(
            [_HTML_INTERFACE_NODE], has_next_page=True, end_cursor="cursor-1"
        ),
        _interfaces_page([_GRID_INTERFACE_NODE, _SECOND_HTML_INTERFACE_NODE]),
    ]

    result = await service.list_html_interfaces(EXAMPLE_ORG_UUID)

    assert result == [
        {**_HTML_INTERFACE_NODE, "uuid": "html-uuid-1"},
        {**_SECOND_HTML_INTERFACE_NODE, "uuid": "html-uuid-2"},
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_html_interfaces_requests_the_next_page_after_the_end_cursor() -> (
    None
):
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        _interfaces_page([], has_next_page=True, end_cursor="cursor-1"),
        _interfaces_page([]),
    ]

    await service.list_html_interfaces(EXAMPLE_ORG_UUID)

    assert interfaces_executor.execute_query.await_args_list == [
        mock_call(LIST_INTERFACES_QUERY, _LIST_INTERFACES_VARIABLES),
        mock_call(
            LIST_INTERFACES_QUERY, {**_LIST_INTERFACES_VARIABLES, "after": "cursor-1"}
        ),
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_html_interfaces_stops_on_a_last_page_that_still_has_a_cursor() -> (
    None
):
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        _interfaces_page(
            [_HTML_INTERFACE_NODE], has_next_page=False, end_cursor="cursor-1"
        ),
    ]

    await service.list_html_interfaces(EXAMPLE_ORG_UUID)

    assert interfaces_executor.execute_query.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_html_interfaces_stops_when_a_next_page_has_no_cursor() -> None:
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        _interfaces_page([_HTML_INTERFACE_NODE], has_next_page=True, end_cursor=None),
    ]

    result = await service.list_html_interfaces(EXAMPLE_ORG_UUID)

    assert result == [{**_HTML_INTERFACE_NODE, "uuid": "html-uuid-1"}]
    assert interfaces_executor.execute_query.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_html_interfaces_numeric_org_id_resolves_via_main_graphql_client() -> (
    None
):
    """Numeric org ids resolve to the org uuid before the Interfaces query."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        _interfaces_page([]),
    )
    public_executor.execute_query = AsyncMock(
        return_value={"organization": {"uuid": EXAMPLE_ORG_UUID}}
    )

    await service.list_html_interfaces(EXAMPLE_NUMERIC_ORG_ID)

    public_executor.execute_query.assert_called_once_with(
        RESOLVE_ORGANIZATION_UUID_QUERY,
        {"id": EXAMPLE_NUMERIC_ORG_ID},
    )
    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["org_uuid"] == EXAMPLE_ORG_UUID


_CUSTOM_CODE_ELEMENT = {
    "id": "el-1",
    "type": "customCode",
    "dataSources": [
        {
            "id": "open-sales",
            "name": "Open sales",
            "filters": None,
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "repoName": "Sales",
            "repoType": "Pipe",
            "fieldKeys": ["amount"],
        }
    ],
    "htmlDocument": {
        "content": "<h1>Sales</h1>",
        "contentHash": "a1b2c3",
        "createdAt": "2026-10-20T12:00:00Z",
    },
}

_HTML_INTERFACE_DETAIL_GRAPHQL = {
    "id": "html-uuid-1",
    "name": "Sales dashboard",
    "visibility": "internal",
    "contentModeHtml": True,
    "pages": [{"id": "page-1", "title": "Page", "elements": [_CUSTOM_CODE_ELEMENT]}],
}

_HTML_GUIDELINES_GRAPHQL = {
    "allowedAttributePrefixes": ["data-"],
    "allowedDataAttributes": ["data-flow-variant"],
    "allowedDataPfyAttributes": ["data-pfy-source", "data-pfy-field"],
    "allowedPlainAttributes": ["class", "style"],
    "allowedTags": ["div", "span", "p"],
    "authoringNotes": ["No JavaScript."],
    "cssRules": [
        {"code": "CSS_IMPORT_FORBIDDEN", "message": "No @import.", "subject": "@import"}
    ],
    "designSystem": None,
    "errorCodes": [
        {"code": "TAG_NOT_ALLOWED", "description": "A tag outside allowedTags."}
    ],
    "filters": {
        "description": "A filter is a tree.",
        "example": {"id": "f1", "type": "root", "conjunction": "and", "filterSet": []},
        "fixedColumnNames": ["title", "created_at"],
        "knownOperators": [{"filterType": "text", "operators": ["eq", "contains"]}],
    },
    "forbiddenAttributes": [
        {
            "code": "ID_ATTRIBUTE_FORBIDDEN",
            "message": "Use data-pfy-id.",
            "subject": "id",
        }
    ],
    "forbiddenTags": [
        {"code": "SCRIPT_FORBIDDEN", "message": "No <script>.", "subject": "script"}
    ],
    "linkAttributes": ["src", "href"],
    "maxAttributesPerElement": 400,
    "maxContentBytes": 200000,
    "maxNestingDepth": 398,
    "urlRule": "Relative, data:, or blob: only.",
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_html_interface_returns_pages_with_html_documents() -> None:
    """Each element keeps its HTML document and declared sources, with uuid aliases."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interface": _HTML_INTERFACE_DETAIL_GRAPHQL},
    )

    result = await service.get_html_interface("html-uuid-1")

    assert result == {
        **_HTML_INTERFACE_DETAIL_GRAPHQL,
        "uuid": "html-uuid-1",
        "pages": [
            {
                "id": "page-1",
                "uuid": "page-1",
                "title": "Page",
                "elements": [{**_CUSTOM_CODE_ELEMENT, "uuid": "el-1"}],
            }
        ],
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_interface_html_guidelines_returns_the_full_shape() -> None:
    """get_interface_html_guidelines returns the guidelines payload unchanged."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interfaceHtmlGuidelines": _HTML_GUIDELINES_GRAPHQL},
    )

    result = await service.get_interface_html_guidelines()

    assert result == _HTML_GUIDELINES_GRAPHQL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_html_interface_parses_filters_back_into_a_dict() -> None:
    """``filters`` rides the wire as a JSON string; reads parse it so a value an
    agent reads can be sent back into create/write unchanged, as a dict."""
    source_with_string_filters = {
        "id": "open-sales",
        "name": "Open sales",
        "filters": '{"status":{"eq":"open"}}',
        "repoId": EXAMPLE_PIPE_REPO_ID,
        "repoName": "Sales",
        "repoType": "Pipe",
        "fieldKeys": ["amount"],
    }
    element = {**_CUSTOM_CODE_ELEMENT, "dataSources": [source_with_string_filters]}
    service, _public, _interfaces_executor = _make_interfaces_service(
        {
            "interface": {
                **_HTML_INTERFACE_DETAIL_GRAPHQL,
                "pages": [{"id": "page-1", "title": "Page", "elements": [element]}],
            }
        },
    )

    result = await service.get_html_interface("html-uuid-1")

    returned_filters = result["pages"][0]["elements"][0]["dataSources"][0]["filters"]
    assert returned_filters == {"status": {"eq": "open"}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_html_interface_queries_the_interface_by_uuid() -> None:
    service, _public, interfaces_executor = _make_interfaces_service(
        {"interface": _HTML_INTERFACE_DETAIL_GRAPHQL},
    )

    await service.get_html_interface("html-uuid-1")

    interfaces_executor.execute_query.assert_awaited_once_with(
        GET_HTML_INTERFACE_QUERY, {"uuid": "html-uuid-1"}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_html_interface_not_found_raises_value_error() -> None:
    """A null interface names the uuid that was not found."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interface": None},
    )

    with pytest.raises(ValueError, match="Interface 'html-uuid-missing' was not found"):
        await service.get_html_interface("html-uuid-missing")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("content_mode_html", [False, None])
async def test_get_html_interface_rejects_grid_interface(
    content_mode_html: bool | None,
) -> None:
    """A grid interface has no HTML document; the error points to get_portal."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {
            "interface": {
                **_HTML_INTERFACE_DETAIL_GRAPHQL,
                "contentModeHtml": content_mode_html,
            }
        },
    )

    with pytest.raises(ValueError, match="not an HTML interface.*get_portal"):
        await service.get_html_interface("html-uuid-1")


def _interface_repos_page(nodes, *, has_next_page=False, end_cursor=None):
    """One ``interfaceRepos`` connection page."""
    return {
        "interfaceRepos": {
            "edges": [{"node": node} for node in nodes],
            "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
        }
    }


_REQUESTS_REPO_NODE = {
    "id": EXAMPLE_PIPE_ID,
    "uuid": "repo-uuid-1",
    "suid": "Ab12Cd34",
    "name": "Purchase requests",
    "type": "Pipe",
    "icon": "cart",
    "color": "blue",
    "noun": "Request",
}

_SUPPLIERS_REPO_NODE = {
    **_REQUESTS_REPO_NODE,
    "id": EXAMPLE_PIPE_ID_2,
    "uuid": "repo-uuid-2",
    "name": "Suppliers",
    "type": "Table",
}

_LIST_INTERFACE_REPOS_VARIABLES = {"orgId": EXAMPLE_NUMERIC_ORG_ID, "first": 50}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_interface_repos_returns_the_repo_nodes() -> None:
    service, _public, _interfaces_executor = _make_interfaces_service(
        _interface_repos_page([_REQUESTS_REPO_NODE, _SUPPLIERS_REPO_NODE]),
    )

    result = await service.list_interface_repos(EXAMPLE_NUMERIC_ORG_ID)

    assert result == [_REQUESTS_REPO_NODE, _SUPPLIERS_REPO_NODE]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("organization_id", "filters", "sent_filters"),
    [
        (int(EXAMPLE_NUMERIC_ORG_ID), {}, {}),
        (f" {EXAMPLE_NUMERIC_ORG_ID} ", {}, {}),
        (
            EXAMPLE_NUMERIC_ORG_ID,
            {"interface_uuid": "html-uuid-1", "repo_name": "purchase"},
            {"interfaceUuid": "html-uuid-1", "repoName": "purchase"},
        ),
    ],
)
async def test_list_interface_repos_sends_the_numeric_org_id_and_given_filters(
    organization_id: str | int, filters: dict, sent_filters: dict
) -> None:
    service, _public, interfaces_executor = _make_interfaces_service(
        _interface_repos_page([]),
    )

    await service.list_interface_repos(organization_id, **filters)

    interfaces_executor.execute_query.assert_awaited_once_with(
        LIST_INTERFACE_REPOS_QUERY, {**_LIST_INTERFACE_REPOS_VARIABLES, **sent_filters}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_interface_repos_follows_the_cursor_to_later_pages() -> None:
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        _interface_repos_page(
            [_REQUESTS_REPO_NODE], has_next_page=True, end_cursor="cursor-1"
        ),
        _interface_repos_page([_SUPPLIERS_REPO_NODE]),
    ]

    result = await service.list_interface_repos(EXAMPLE_NUMERIC_ORG_ID)

    assert result == [_REQUESTS_REPO_NODE, _SUPPLIERS_REPO_NODE]
    assert interfaces_executor.execute_query.await_args_list == [
        mock_call(LIST_INTERFACE_REPOS_QUERY, _LIST_INTERFACE_REPOS_VARIABLES),
        mock_call(
            LIST_INTERFACE_REPOS_QUERY,
            {**_LIST_INTERFACE_REPOS_VARIABLES, "after": "cursor-1"},
        ),
    ]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "organization_id", [EXAMPLE_ORG_UUID, "", "  ", "org-1", "\u0661\u0662", True]
)
async def test_list_interface_repos_rejects_a_non_numeric_org_id(
    organization_id: str,
) -> None:
    """The listing takes the numeric organization id; anything else fails before a call."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        _interface_repos_page([]),
    )

    with pytest.raises(ValueError, match="numeric organization id"):
        await service.list_interface_repos(organization_id)

    interfaces_executor.execute_query.assert_not_awaited()
    public_executor.execute_query.assert_not_awaited()


_REPO_FIELD = {
    "id": EXAMPLE_FIELD_INTERNAL_ID,
    "uuid": "6a850d1c-0000-4000-8000-000000000016",
    "label": "Amount",
    "type": "currency",
    "phaseId": EXAMPLE_PHASE_ID,
    "archived": False,
    "required": True,
    "options": None,
    "description": None,
    "helpText": None,
    "connectedRepoId": None,
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_interface_repo_fields_returns_the_repo_fields() -> None:
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interfacesRepoStructure": {"fields": [_REPO_FIELD]}},
    )

    result = await service.get_interface_repo_fields("repo-uuid-1")

    assert result == [_REPO_FIELD]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("interface_uuid", "sent"),
    [
        (None, {"repoId": "repo-uuid-1"}),
        ("html-uuid-1", {"repoId": "repo-uuid-1", "interfaceId": "html-uuid-1"}),
    ],
)
async def test_get_interface_repo_fields_sends_the_repo_and_given_interface(
    interface_uuid: str | None, sent: dict
) -> None:
    service, _public, interfaces_executor = _make_interfaces_service(
        {"interfacesRepoStructure": {"fields": []}},
    )

    await service.get_interface_repo_fields(
        "repo-uuid-1", interface_uuid=interface_uuid
    )

    interfaces_executor.execute_query.assert_awaited_once_with(
        GET_INTERFACE_REPO_FIELDS_QUERY, sent
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_interface_repo_fields_no_structure_raises_value_error() -> None:
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"interfacesRepoStructure": None},
    )

    with pytest.raises(ValueError, match="repo-uuid-1"):
        await service.get_interface_repo_fields("repo-uuid-1")


def _selected_fields(query, *path: str) -> set[str]:
    """Names selected under ``path`` below the operation's root field."""
    node = query.document.definitions[0].selection_set.selections[0]
    for name in path:
        node = next(f for f in node.selection_set.selections if f.name.value == name)
    return {field.name.value for field in node.selection_set.selections}


def test_get_interface_repo_fields_selects_the_field_uuid():
    """A custom field's data source key is its uuid, so the read must return it."""
    assert "uuid" in _selected_fields(GET_INTERFACE_REPO_FIELDS_QUERY, "fields")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_interface_html_guidelines_sends_no_variables() -> None:
    """get_interface_html_guidelines takes no argument: the rules are org-independent."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"interfaceHtmlGuidelines": _HTML_GUIDELINES_GRAPHQL},
    )

    await service.get_interface_html_guidelines()

    query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert query_used is GET_INTERFACE_HTML_GUIDELINES_QUERY
    assert variables == {}


_portal_queries_module = importlib.import_module("pipefy_sdk.queries.portal_queries")


def _portal_mutation_constant(name: str):
    """Return the portal mutation constant when exported; else None (TDD placeholder)."""
    return getattr(_portal_queries_module, name, None)


def _assert_interfaces_mutation_query(query_used: object, constant_name: str) -> None:
    """Assert Interfaces mutation document matches the expected portal_queries constant."""
    expected = _portal_mutation_constant(constant_name)
    if expected is not None:
        assert query_used is expected
    else:
        operation_snippets = {
            "FIND_OR_CREATE_PORTAL_MUTATION": "findOrCreateInterfaceByTemplate",
            "UPDATE_INTERFACE_MUTATION": "updateInterface",
            "DELETE_INTERFACE_MUTATION": "deleteInterface",
            "CREATE_PAGE_MUTATION": "createPage",
            "UPDATE_PAGE_MUTATION": "updatePage",
            "DELETE_PAGE_MUTATION": "deletePage",
            "SORT_PAGES_MUTATION": "sortPages",
            "UPDATE_PAGE_LAYOUT_MUTATION": "updatePageLayout",
            "CREATE_ELEMENT_MUTATION": "createElement",
            "UPDATE_ELEMENT_MUTATION": "updateElement",
            "DELETE_ELEMENT_MUTATION": "deleteElement",
            "DUPLICATE_ELEMENT_MUTATION": "duplicateElement",
            "CREATE_SUB_PORTAL_MUTATION": "createSubPortal",
        }
        assert operation_snippets[constant_name] in str(query_used)


try:
    _portal_internal_queries_module = importlib.import_module(
        "pipefy_sdk.queries.portal_internal_queries"
    )
except ModuleNotFoundError:
    _portal_internal_queries_module = None


def _portal_internal_mutation_constant(name: str):
    """Return the Internal API mutation constant when exported; else None (TDD)."""
    if _portal_internal_queries_module is None:
        return None
    return getattr(_portal_internal_queries_module, name, None)


def _assert_internal_mutation_query(query_used: object, constant_name: str) -> None:
    """Assert Internal API mutation document matches the expected constant."""
    expected = _portal_internal_mutation_constant(constant_name)
    if expected is not None:
        assert query_used is expected
    else:
        operation_snippets = {
            "UPDATE_SUB_PORTAL_ELEMENT_MUTATION": "updateSubPortalElement",
            "DELETE_SUB_PORTAL_ELEMENT_MUTATION": "deleteSubPortalElement",
            "DELETE_SUB_PORTAL_INTERFACE_MUTATION": "deleteSubPortalInterface",
        }
        assert operation_snippets[constant_name] in str(query_used)


def _make_portal_service_with_clients(
    *,
    interfaces_return: dict | None = None,
    internal_return: dict | None = None,
) -> tuple[PortalService, MagicMock, MagicMock]:
    """PortalService with mocked Interfaces and Internal API clients."""
    interfaces = mock_executor(interfaces_return)
    internal = mock_executor(internal_return)
    service = PortalService(
        public_executor=mock_executor(),
        interfaces_executor=interfaces,
        internal_executor=internal,
    )
    return service, interfaces, internal


_CREATE_PORTAL_GRAPHQL_INTERFACE = {
    "id": "portal-created-uuid",
    "name": "Org Portal",
    "visibility": "internal",
    "subType": "portal",
}

_CREATE_PORTAL_RESPONSE = {
    "findOrCreateInterfaceByTemplate": {
        "interface": _CREATE_PORTAL_GRAPHQL_INTERFACE,
    }
}

_PERMISSION_DENIED_ERROR = PipefyGraphQLError(
    [
        {
            "message": "Permission Denied",
            "extensions": {"code": "PERMISSION_DENIED"},
        }
    ],
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_resolves_numeric_org_and_calls_find_or_create_template() -> (
    None
):
    """create_portal resolves numeric org id then findOrCreateInterfaceByTemplate."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        _CREATE_PORTAL_RESPONSE,
    )
    public_executor.execute_query = AsyncMock(
        return_value={"organization": {"uuid": EXAMPLE_ORG_UUID}}
    )

    result = await service.create_portal(EXAMPLE_NUMERIC_ORG_ID)

    public_executor.execute_query.assert_called_once_with(
        RESOLVE_ORGANIZATION_UUID_QUERY,
        {"id": EXAMPLE_NUMERIC_ORG_ID},
    )
    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "FIND_OR_CREATE_PORTAL_MUTATION")
    assert variables == {"input": {"orgUuid": EXAMPLE_ORG_UUID, "subType": "portal"}}
    assert result["uuid"] == "portal-created-uuid"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_uuid_org_skips_resolve() -> None:
    """UUID-shaped org identifiers skip resolve before findOrCreate mutation."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        _CREATE_PORTAL_RESPONSE,
    )
    public_executor.execute_query = AsyncMock()

    await service.create_portal(EXAMPLE_ORG_UUID)

    public_executor.execute_query.assert_not_called()
    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables == {"input": {"orgUuid": EXAMPLE_ORG_UUID, "subType": "portal"}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_idempotent_returns_same_interface_uuid() -> None:
    """Second create_portal call returns the same interface uuid (idempotent)."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_PORTAL_RESPONSE,
    )

    first = await service.create_portal(EXAMPLE_ORG_UUID)
    second = await service.create_portal(EXAMPLE_ORG_UUID)

    assert first["uuid"] == second["uuid"] == "portal-created-uuid"
    assert interfaces_executor.execute_query.call_count == 2
    for call in interfaces_executor.execute_query.call_args_list:
        _, variables = call[0]
        assert variables == {
            "input": {"orgUuid": EXAMPLE_ORG_UUID, "subType": "portal"}
        }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_passes_only_set_fields_under_input() -> None:
    """update_portal sends snake_case interface_uuid and only provided fields."""
    update_response = {
        "updateInterface": {
            "interface": {**_CREATE_PORTAL_GRAPHQL_INTERFACE, "name": "Renamed"},
        }
    }
    service, _public, interfaces_executor = _make_interfaces_service(update_response)

    await service.update_portal("portal-created-uuid", name="Renamed")

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "UPDATE_INTERFACE_MUTATION")
    assert variables == {
        "input": {"interface_uuid": "portal-created-uuid", "name": "Renamed"}
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_omits_unset_optional_fields() -> None:
    """Unset optional fields are not included in updateInterface input."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {
            "updateInterface": {
                "interface": {
                    **_CREATE_PORTAL_GRAPHQL_INTERFACE,
                    "visibility": "public",
                }
            }
        },
    )

    await service.update_portal(
        "portal-created-uuid",
        visibility="public",
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables == {
        "input": {
            "interface_uuid": "portal-created-uuid",
            "visibility": "public",
        }
    }
    assert "name" not in variables["input"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_rejects_invalid_visibility_before_graphql() -> None:
    """Invalid visibility values raise ValidationError before any GraphQL call."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updateInterface": {"interface": _CREATE_PORTAL_GRAPHQL_INTERFACE}},
    )

    with pytest.raises(ValidationError):
        await service.update_portal(
            "portal-created-uuid",
            visibility="public_visibility",
        )

    interfaces_executor.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_serializes_all_fields_with_camel_case_aliases() -> None:
    """update_portal sends displayPipefyHeader and omits unset fields."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {
            "updateInterface": {
                "interface": {
                    **_CREATE_PORTAL_GRAPHQL_INTERFACE,
                    "name": "Full Update",
                    "visibility": "public",
                }
            }
        },
    )

    await service.update_portal(
        "portal-created-uuid",
        name="Full Update",
        visibility="public",
        color="#aabbcc",
        icon="layout",
        display_pipefy_header=True,
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables == {
        "input": {
            "interface_uuid": "portal-created-uuid",
            "name": "Full Update",
            "visibility": "public",
            "color": "#aabbcc",
            "icon": "layout",
            "displayPipefyHeader": True,
        }
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_portal_calls_delete_interface_with_interface_uuid() -> None:
    """delete_portal uses deleteInterface with snake_case input.interface_uuid."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"deleteInterface": {"success": True}},
    )

    result = await service.delete_portal("portal-to-delete")

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "DELETE_INTERFACE_MUTATION")
    assert variables == {"input": {"interface_uuid": "portal-to-delete"}}
    assert result == {"deleteInterface": {"success": True}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_permission_denied_surfaces_actionable_message() -> None:
    """PERMISSION_DENIED from Interfaces maps to portal permission guidance."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_PORTAL_RESPONSE,
    )
    interfaces_executor.execute_query = AsyncMock(side_effect=_PERMISSION_DENIED_ERROR)

    with pytest.raises(PortalPermissionError, match=r"(create_portal|manage_portals)"):
        await service.create_portal(EXAMPLE_ORG_UUID)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_permission_denied_surfaces_actionable_message() -> None:
    """PERMISSION_DENIED on update maps to portal permission guidance."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updateInterface": {"interface": _CREATE_PORTAL_GRAPHQL_INTERFACE}},
    )
    interfaces_executor.execute_query = AsyncMock(side_effect=_PERMISSION_DENIED_ERROR)

    with pytest.raises(PortalPermissionError, match=r"(create_portal|manage_portals)"):
        await service.update_portal("portal-created-uuid", name="Renamed")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_portal_permission_denied_surfaces_actionable_message() -> None:
    """PERMISSION_DENIED on delete maps to portal permission guidance."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"deleteInterface": {"success": True}},
    )
    interfaces_executor.execute_query = AsyncMock(side_effect=_PERMISSION_DENIED_ERROR)

    with pytest.raises(PortalPermissionError, match=r"(create_portal|manage_portals)"):
        await service.delete_portal("portal-to-delete")


_INTERFACE_UUID = "portal-uuid-1"
_PAGE_ID = "page-uuid-1"
_PAGE_ID_2 = "page-uuid-2"
_PAGE_TITLE = "Portal Home"

_CREATE_PAGE_GRAPHQL = {
    "id": _PAGE_ID,
    "title": _PAGE_TITLE,
    "elements": [{"id": "el-1", "type": "text"}],
}

_CREATE_PAGE_RESPONSE = {
    "createPage": {"page": _CREATE_PAGE_GRAPHQL},
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_page_calls_create_page_with_interface_uuid_and_title() -> (
    None
):
    """create_portal_page uses createPage with interface_uuid and title."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_PAGE_RESPONSE,
    )

    result = await service.create_portal_page(_INTERFACE_UUID, _PAGE_TITLE)

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "CREATE_PAGE_MUTATION")
    assert variables == {
        "input": {"interface_uuid": _INTERFACE_UUID, "title": _PAGE_TITLE}
    }
    assert result["uuid"] == _PAGE_ID
    assert result["title"] == _PAGE_TITLE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_page_forwards_optional_fields() -> None:
    """Optional createPage fields are included when provided."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_PAGE_RESPONSE,
    )

    await service.create_portal_page(
        _INTERFACE_UUID,
        _PAGE_TITLE,
        description="Landing copy",
        index=1,
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables == {
        "input": {
            "interface_uuid": _INTERFACE_UUID,
            "title": _PAGE_TITLE,
            "description": "Landing copy",
            "index": 1,
        }
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_calls_update_page_with_required_ids() -> None:
    """update_portal_page uses updatePage with interface_uuid and page_id."""
    update_response = {
        "updatePage": {
            "page": {**_CREATE_PAGE_GRAPHQL, "title": "Renamed Page"},
        }
    }
    service, _public, interfaces_executor = _make_interfaces_service(update_response)

    result = await service.update_portal_page(
        _INTERFACE_UUID,
        _PAGE_ID,
        title="Renamed Page",
    )

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "UPDATE_PAGE_MUTATION")
    assert variables == {
        "input": {
            "interface_uuid": _INTERFACE_UUID,
            "page_id": _PAGE_ID,
            "title": "Renamed Page",
        }
    }
    assert result["title"] == "Renamed Page"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_omits_unset_optional_fields() -> None:
    """Unset optional updatePage fields are not sent to GraphQL."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updatePage": {"page": _CREATE_PAGE_GRAPHQL}},
    )

    await service.update_portal_page(
        _INTERFACE_UUID,
        _PAGE_ID,
        description="Only description changed",
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables == {
        "input": {
            "interface_uuid": _INTERFACE_UUID,
            "page_id": _PAGE_ID,
            "description": "Only description changed",
        }
    }
    assert "title" not in variables["input"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_portal_page_calls_delete_page_with_interface_and_page_ids() -> (
    None
):
    """delete_portal_page uses deletePage with interface_uuid and page_id."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"deletePage": {"success": True}},
    )

    result = await service.delete_portal_page(_INTERFACE_UUID, _PAGE_ID)

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "DELETE_PAGE_MUTATION")
    assert variables == {
        "input": {"interface_uuid": _INTERFACE_UUID, "page_id": _PAGE_ID}
    }
    assert result == {"deletePage": {"success": True}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sort_portal_pages_calls_sort_pages_with_page_ids_list() -> None:
    """sort_portal_pages uses sortPages with interface_uuid and page_ids."""
    page_ids = [_PAGE_ID_2, _PAGE_ID]
    service, _public, interfaces_executor = _make_interfaces_service(
        {"sortPages": {"success": True}},
    )

    result = await service.sort_portal_pages(_INTERFACE_UUID, page_ids)

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "SORT_PAGES_MUTATION")
    assert variables == {
        "input": {"interface_uuid": _INTERFACE_UUID, "page_ids": page_ids}
    }
    assert result == {"sortPages": {"success": True}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_layout_does_not_send_interface_uuid() -> None:
    """update_portal_page_layout uses updatePageLayout with page_id and layout only."""
    layout = [{"id": "row-1", "type": "row", "children": ["el-1"]}]
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updatePageLayout": {"success": True}},
    )

    result = await service.update_portal_page_layout(_PAGE_ID, layout)

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "UPDATE_PAGE_LAYOUT_MUTATION")
    assert variables == {
        "input": {
            "page_id": _PAGE_ID,
            "layout": json.dumps(layout, separators=(",", ":"), ensure_ascii=False),
        }
    }
    assert "interface_uuid" not in variables["input"]
    assert result == {"updatePageLayout": {"success": True}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_layout_accepts_empty_array() -> None:
    """A page with no elements has an empty grid."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updatePageLayout": {"success": True}},
    )

    await service.update_portal_page_layout(_PAGE_ID, [])

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["layout"] == "[]"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_layout_accepts_row_with_empty_children() -> None:
    """A row may list no elements; only a missing or non-string children value is rejected."""
    layout = [{"id": "row-1", "type": "row", "children": []}]
    expected = json.dumps(layout, separators=(",", ":"), ensure_ascii=False)
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updatePageLayout": {"success": True}},
    )

    await service.update_portal_page_layout(_PAGE_ID, layout)

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["layout"] == expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_layout_keeps_unknown_row_keys() -> None:
    """Round-trip must send keys get_portal stored besides id, type, and children."""
    layout = [{"id": "row-1", "type": "row", "children": ["el-1"], "minHeight": 2}]
    expected = json.dumps(layout, separators=(",", ":"), ensure_ascii=False)
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updatePageLayout": {"success": True}},
    )

    await service.update_portal_page_layout(_PAGE_ID, layout)

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["layout"] == expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_layout_sends_ids_stripped() -> None:
    """The API stores layout verbatim, so a padded id would never match its element."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updatePageLayout": {"success": True}},
    )

    await service.update_portal_page_layout(
        _PAGE_ID, [{"id": " row-1 ", "type": "row", "children": [" el-1 "]}]
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["layout"] == (
        '[{"id":"row-1","type":"row","children":["el-1"]}]'
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_page_layout_rejects_malformed_row_before_query() -> None:
    """The API stores layout JSON verbatim, so an incomplete row must not be sent."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updatePageLayout": {"success": True}},
    )

    with pytest.raises(ValueError, match="type 'row'"):
        await service.update_portal_page_layout(_PAGE_ID, [{}])

    interfaces_executor.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_page_permission_denied_surfaces_actionable_message() -> (
    None
):
    """PERMISSION_DENIED on createPage maps to portal permission guidance."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_PAGE_RESPONSE,
    )
    interfaces_executor.execute_query = AsyncMock(side_effect=_PERMISSION_DENIED_ERROR)

    with pytest.raises(PortalPermissionError, match=r"(create_portal|manage_portals)"):
        await service.create_portal_page(_INTERFACE_UUID, _PAGE_TITLE)


_ELEMENT_ID = "el-uuid-1"
_FORMS_METADATA = {"name": "Request form"}
_FORMS_DATA_SOURCES = [{"repoId": EXAMPLE_PIPE_REPO_ID}]

_CREATE_ELEMENT_GRAPHQL = {
    "id": _ELEMENT_ID,
    "type": "forms",
    "metadata": _FORMS_METADATA,
}

_CREATE_ELEMENT_RESPONSE = {
    "createElement": {"element": _CREATE_ELEMENT_GRAPHQL},
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_calls_create_element_with_validated_input() -> (
    None
):
    """create_portal_element validates via CreatePortalElementInput then createElement."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )

    await service.create_portal_element(
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=_FORMS_DATA_SOURCES,
    )

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "CREATE_ELEMENT_MUTATION")
    assert variables == {
        "input": {
            "page_id": _PAGE_ID,
            "type": "forms",
            "metadata": json.dumps(
                _FORMS_METADATA, separators=(",", ":"), ensure_ascii=False
            ),
            "data_sources": [{"repoId": EXAMPLE_PIPE_REPO_ID, "fieldKeys": []}],
        }
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_sends_layout_rows_as_interfaces_json() -> None:
    """layout rides on createElement as the serialized row array plus the client id."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )
    rows = [{"id": "row-1", "type": "row", "children": ["el-new"]}]

    await service.create_portal_element(
        _PAGE_ID,
        type="link",
        metadata={"linkName": "Docs", "linkUrl": "https://example.com"},
        element_id="el-new",
        layout=rows,
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["id"] == "el-new"
    assert variables["input"]["layout"] == json.dumps(
        rows, separators=(",", ":"), ensure_ascii=False
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_sends_element_id_matching_its_row() -> None:
    """The element is stored under the id sent, so it must match the stripped child."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )

    await service.create_portal_element(
        _PAGE_ID,
        type="link",
        metadata={"linkName": "Docs", "linkUrl": "https://example.com"},
        element_id=" el-new ",
        layout=[{"id": "row-1", "type": "row", "children": [" el-new "]}],
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["id"] == "el-new"
    assert variables["input"]["layout"] == (
        '[{"id":"row-1","type":"row","children":["el-new"]}]'
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_rejects_malformed_layout_before_query() -> None:
    """createElement.layout replaces the page grid, so a partial row stops locally."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )

    with pytest.raises(ValidationError, match="type 'row'"):
        await service.create_portal_element(
            _PAGE_ID,
            type="link",
            metadata={"linkName": "Docs", "linkUrl": "https://example.com"},
            element_id="el-new",
            layout=[{"children": ["el-new"]}],
        )

    interfaces_executor.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_always_sends_empty_data_sources_for_link() -> None:
    """Link creates must send data_sources: [] so Pipefy does not receive null."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )
    link_metadata = {"linkName": "Test", "linkUrl": "https://example.com"}

    await service.create_portal_element(_PAGE_ID, type="link", metadata=link_metadata)

    _query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["data_sources"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_logs_warning_for_unrecognized_data_source_keys(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Invalid data_sources entries are skipped with a warning (e.g. LLM-guessed pipe_id)."""
    caplog.set_level(logging.WARNING, logger="pipefy_sdk.services.portal_service")
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )

    await service.create_portal_element(
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=[{"pipe_id": "123"}],
    )

    assert any("Skipping portal data_sources" in r.message for r in caplog.records)
    _query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["data_sources"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_reads_only_declared_repo_id_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only the declared ``repoId`` key is honored; ``repo_uuid``/``repoUuid`` are skipped."""
    caplog.set_level(logging.WARNING, logger="pipefy_sdk.services.portal_service")
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )

    await service.create_portal_element(
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=[{"repo_uuid": "p-1"}, {"repoUuid": "p-2"}],
    )

    assert any("Skipping portal data_sources" in r.message for r in caplog.records)
    _query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["data_sources"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_graphql_error_is_not_portal_permission_error() -> (
    None
):
    """Non-permission Interfaces failures must not be wrapped as PortalPermissionError."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )
    interfaces_executor.execute_query = AsyncMock(
        side_effect=PipefyGraphQLError(
            [{"message": "Variable $input was provided invalid value"}],
        )
    )

    with pytest.raises(PipefyGraphQLError):
        await service.create_portal_element(
            _PAGE_ID,
            type="link",
            metadata={"linkName": "Test", "linkUrl": "https://example.com"},
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_portal_permission_mapping_only_inspects_the_first_error() -> None:
    """A PERMISSION_DENIED that is not the first error re-raises PipefyGraphQLError.

    Permission mapping delegates to ``classify_exception``, which classifies the
    first error only. Portal responses carry a single error in practice, so this
    narrowing (versus scanning every error) is not observable there. Pinning it
    keeps a future contributor from reading the first-error behavior as a bug.
    """
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )
    interfaces_executor.execute_query = AsyncMock(
        side_effect=PipefyGraphQLError(
            [
                {"message": "Bad input", "extensions": {"code": "BAD_REQUEST"}},
                {"message": "Denied", "extensions": {"code": "PERMISSION_DENIED"}},
            ],
        )
    )

    with pytest.raises(PipefyGraphQLError):
        await service.create_portal_element(
            _PAGE_ID,
            type="link",
            metadata={"linkName": "Test", "linkUrl": "https://example.com"},
        )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["FORBIDDEN", "UNAUTHORIZED"])
async def test_portal_permission_mapping_covers_permission_code_synonyms(
    code: str,
) -> None:
    """FORBIDDEN and UNAUTHORIZED also map to ``PortalPermissionError``.

    The shared ``classify_exception`` groups these with PERMISSION_DENIED, so
    delegating to it widened portal mapping beyond the one literal code the old
    hand-rolled scan matched. Portal returns PERMISSION_DENIED today; pinning the
    synonyms records that the widening is intended, not accidental.
    """
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )
    interfaces_executor.execute_query = AsyncMock(
        side_effect=PipefyGraphQLError(
            [{"message": "Denied", "extensions": {"code": code}}],
        )
    )

    with pytest.raises(PortalPermissionError, match=r"(create_portal|manage_portals)"):
        await service.create_portal_element(
            _PAGE_ID,
            type="link",
            metadata={"linkName": "Test", "linkUrl": "https://example.com"},
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_element_rejects_invalid_metadata_before_graphql() -> None:
    """CreatePortalElementInput validation must run before execute_query."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_ELEMENT_RESPONSE,
    )

    with pytest.raises(ValidationError, match="name"):
        await service.create_portal_element(
            _PAGE_ID,
            type="forms",
            metadata={},
        )

    interfaces_executor.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_calls_update_element_with_full_metadata() -> None:
    """update_portal_element sends element_id, page_id, and full metadata replace."""
    link_metadata = {
        "linkUrl": "https://example.com/pipefy",
        "linkName": "Open",
    }
    update_response = {"updateElement": {"success": True}}
    service, _public, interfaces_executor = _make_interfaces_service(update_response)

    result = await service.update_portal_element(
        _ELEMENT_ID,
        _PAGE_ID,
        type="link",
        metadata=link_metadata,
        data_sources=[],
    )

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "UPDATE_ELEMENT_MUTATION")
    assert variables == {
        "input": {
            "element_id": _ELEMENT_ID,
            "page_id": _PAGE_ID,
            "metadata": json.dumps(
                link_metadata, separators=(",", ":"), ensure_ascii=False
            ),
            "data_sources": [],
        }
    }
    assert result["metadata"]["linkUrl"] == "https://example.com/pipefy"


_PORTAL_UUID = "portal-uuid-1"
_SIBLING_ELEMENT_ID = "el-uuid-sibling"
_STORED_DATA_SOURCES = [
    {
        "repoId": EXAMPLE_PIPE_REPO_ID,
        "repoName": "Requests",
        "repoType": "Pipe",
        "fieldKeys": ["title"],
    }
]
_SIBLING_DATA_SOURCES = [
    {
        "repoId": "sibling-repo-uuid",
        "repoName": "Other",
        "repoType": "Pipe",
        "fieldKeys": [],
    }
]


def _forms_element(element_id: str, data_sources: list[dict], editable: bool) -> dict:
    return {
        "id": element_id,
        "type": "forms",
        "metadata": _FORMS_METADATA,
        "editable": editable,
        "dataSources": data_sources,
    }


def _portal_with_forms_element(target_editable: bool = True) -> dict:
    """``portalInterface`` payload: a sibling forms element, then the target.

    The sibling comes first, is bound to another pipe and stores the opposite
    ``editable``, so a lookup that does not match on ``element_id`` resends the
    sibling's bindings and flag.
    """
    return {
        "portalInterface": {
            "id": _PORTAL_UUID,
            "pages": [
                {"id": _PAGE_ID_2, "elements": []},
                {
                    "id": _PAGE_ID,
                    "elements": [
                        _forms_element(
                            _SIBLING_ELEMENT_ID,
                            _SIBLING_DATA_SOURCES,
                            not target_editable,
                        ),
                        _forms_element(
                            _ELEMENT_ID, _STORED_DATA_SOURCES, target_editable
                        ),
                    ],
                },
            ],
        }
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_sends_given_data_sources_without_reading() -> None:
    """Given data_sources replace the element's list; no portal read is needed."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updateElement": {"success": True}},
    )

    await service.update_portal_element(
        _ELEMENT_ID,
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=_FORMS_DATA_SOURCES,
        portal_uuid=_PORTAL_UUID,
    )

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "UPDATE_ELEMENT_MUTATION")
    assert variables["input"]["data_sources"] == [
        {"repoId": EXAMPLE_PIPE_REPO_ID, "fieldKeys": []}
    ]
    assert "editable" not in variables["input"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_empty_data_sources_unlink_with_portal_uuid() -> (
    None
):
    """``data_sources=[]`` unlinks even when portal_uuid is given; nothing is read."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updateElement": {"success": True}},
    )

    await service.update_portal_element(
        _ELEMENT_ID,
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=[],
        portal_uuid=_PORTAL_UUID,
    )

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "UPDATE_ELEMENT_MUTATION")
    assert variables["input"]["data_sources"] == []


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("stored_editable", [True, False])
async def test_update_portal_element_keeps_current_data_sources_when_omitted(
    stored_editable: bool,
) -> None:
    """Omitted data_sources are read from the portal and sent back, not cleared.

    The element's stored ``editable`` goes back with them, ``False`` included: the
    API rejects an update whose data source lists fieldKeys when ``editable`` is
    missing.
    """
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        _portal_with_forms_element(target_editable=stored_editable),
        {"updateElement": {"success": True}},
    ]

    await service.update_portal_element(
        _ELEMENT_ID,
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        portal_uuid=_PORTAL_UUID,
    )

    read_query, read_variables = interfaces_executor.execute_query.call_args_list[0][0]
    assert read_query is GET_PORTAL_QUERY
    assert read_variables == {"uuid": _PORTAL_UUID}
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "UPDATE_ELEMENT_MUTATION")
    assert variables["input"]["data_sources"] == [
        {"repoId": EXAMPLE_PIPE_REPO_ID, "fieldKeys": ["title"]}
    ]
    assert variables["input"]["editable"] is stored_editable


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_keep_path_sends_given_editable() -> None:
    """A caller's editable wins over the stored flag; the bindings are still kept."""
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        _portal_with_forms_element(),
        {"updateElement": {"success": True}},
    ]

    await service.update_portal_element(
        _ELEMENT_ID,
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        portal_uuid=_PORTAL_UUID,
        editable=False,
    )

    variables = interfaces_executor.execute_query.call_args[0][1]
    assert variables["input"]["editable"] is False
    assert variables["input"]["data_sources"] == [
        {"repoId": EXAMPLE_PIPE_REPO_ID, "fieldKeys": ["title"]}
    ]


_OPEN_FILTER = {
    "id": "root",
    "type": "root",
    "conjunction": "and",
    "filterSet": [
        {"id": "leaf", "columnName": "title", "operator": "not_empty", "value": None}
    ],
}
_OPEN_FILTER_JSON = (
    '{"id":"root","type":"root","conjunction":"and","filterSet":'
    '[{"id":"leaf","columnName":"title","operator":"not_empty","value":null}]}'
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_keep_path_resends_source_id_name_and_filters() -> (
    None
):
    """A kept source goes back with its handle, label and filters, as the API read them."""
    stored_source = {
        "id": "open-requests",
        "name": "Open requests",
        "filters": _OPEN_FILTER_JSON,
        "repoId": EXAMPLE_PIPE_REPO_ID,
        "repoName": "Requests",
        "repoType": "Pipe",
        "fieldKeys": ["title"],
    }
    portal = _portal_with_forms_element()
    target = portal["portalInterface"]["pages"][1]["elements"][1]
    target["dataSources"] = [stored_source]
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [
        portal,
        {"updateElement": {"success": True}},
    ]

    await service.update_portal_element(
        _ELEMENT_ID,
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        portal_uuid=_PORTAL_UUID,
    )

    variables = interfaces_executor.execute_query.call_args[0][1]
    assert variables["input"]["data_sources"] == [
        {
            "id": "open-requests",
            "name": "Open requests",
            "filters": _OPEN_FILTER_JSON,
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "fieldKeys": ["title"],
        }
    ]


_OPEN_REQUESTS_HANDLE = {
    "id": "open-requests",
    "name": "Open requests",
    "repoId": EXAMPLE_PIPE_REPO_ID,
    "fieldKeys": ["title"],
}


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filters", "sent_filters"),
    [
        (_OPEN_FILTER, {"filters": _OPEN_FILTER_JSON}),
        (None, {}),
    ],
    ids=["object sent as Interfaces Json", "null not sent"],
)
async def test_update_portal_element_sends_given_source_handle_and_filters(
    filters: dict | None, sent_filters: dict
) -> None:
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updateElement": {"success": True}},
    )

    await service.update_portal_element(
        _ELEMENT_ID,
        _PAGE_ID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=[{**_OPEN_REQUESTS_HANDLE, "filters": filters}],
    )

    variables = interfaces_executor.execute_query.call_args[0][1]
    assert variables["input"]["data_sources"] == [
        {**_OPEN_REQUESTS_HANDLE, **sent_filters}
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_requires_data_sources_or_portal_uuid() -> None:
    """Without either, the call is rejected before any request."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"updateElement": {"success": True}},
    )

    with pytest.raises(ValidationError, match="portal_uuid"):
        await service.update_portal_element(
            _ELEMENT_ID,
            _PAGE_ID,
            type="forms",
            metadata=_FORMS_METADATA,
        )

    interfaces_executor.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_failed_read_sends_no_mutation() -> None:
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = PipefyGraphQLError(
        [{"message": "Something went wrong"}]
    )

    with pytest.raises(PipefyGraphQLError):
        await service.update_portal_element(
            _ELEMENT_ID,
            _PAGE_ID,
            type="forms",
            metadata=_FORMS_METADATA,
            portal_uuid=_PORTAL_UUID,
        )

    interfaces_executor.execute_query.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_on_another_page_names_that_page() -> None:
    """The element must sit on page_id; the error names the page that holds it."""
    portal = _portal_with_forms_element()
    pages = portal["portalInterface"]["pages"]
    pages[0]["elements"], pages[1]["elements"] = pages[1]["elements"], []
    service, _public, interfaces_executor = _make_interfaces_service(portal)

    with pytest.raises(ValueError) as excinfo:
        await service.update_portal_element(
            _ELEMENT_ID,
            _PAGE_ID,
            type="forms",
            metadata=_FORMS_METADATA,
            portal_uuid=_PORTAL_UUID,
        )

    assert str(excinfo.value) == (
        f"Element '{_ELEMENT_ID}' is on page '{_PAGE_ID_2}' of portal "
        f"'{_PORTAL_UUID}', not on page '{_PAGE_ID}'. Pass page_id='{_PAGE_ID_2}'."
    )
    interfaces_executor.execute_query.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portal_element_on_no_page_points_to_data_sources() -> None:
    portal = _portal_with_forms_element()
    portal["portalInterface"]["pages"][1]["elements"].pop()
    service, _public, interfaces_executor = _make_interfaces_service(portal)

    with pytest.raises(ValueError) as excinfo:
        await service.update_portal_element(
            _ELEMENT_ID,
            _PAGE_ID,
            type="forms",
            metadata=_FORMS_METADATA,
            portal_uuid=_PORTAL_UUID,
        )

    assert str(excinfo.value) == (
        f"Element '{_ELEMENT_ID}' is on no page of portal '{_PORTAL_UUID}'. "
        "Check portal_uuid and element_id, or pass data_sources to skip the read."
    )
    interfaces_executor.execute_query.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_portal_element_calls_delete_element_with_ids() -> None:
    """delete_portal_element uses deleteElement with element_id and page_id."""
    service, _public, interfaces_executor = _make_interfaces_service(
        {"deleteElement": {"success": True}},
    )

    result = await service.delete_portal_element(_ELEMENT_ID, _PAGE_ID)

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "DELETE_ELEMENT_MUTATION")
    assert variables == {
        "input": {"element_id": _ELEMENT_ID, "page_id": _PAGE_ID},
    }
    assert result == {"deleteElement": {"success": True}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_portal_element_sends_pruned_layout_in_the_same_call() -> None:
    """deleteElement takes the pruned grid, so no orphan row outlives the element."""
    pruned = [{"id": "row-1", "type": "row", "children": ["el-other"], "minHeight": 2}]
    service, _public, interfaces_executor = _make_interfaces_service(
        {"deleteElement": {"success": True}},
    )

    await service.delete_portal_element(
        _ELEMENT_ID, _PAGE_ID, layout=parse_portal_page_layout(pruned)
    )

    interfaces_executor.execute_query.assert_called_once()
    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables == {
        "input": {
            "element_id": _ELEMENT_ID,
            "page_id": _PAGE_ID,
            "layout": json.dumps(pruned, separators=(",", ":"), ensure_ascii=False),
        },
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_portal_element_rejects_layout_listing_the_element() -> None:
    service, _public, interfaces_executor = _make_interfaces_service(
        {"deleteElement": {"success": True}},
    )
    layout = parse_portal_page_layout(
        [{"id": "row-1", "type": "row", "children": [_ELEMENT_ID]}]
    )

    with pytest.raises(ValidationError, match="still lists element_id"):
        await service.delete_portal_element(_ELEMENT_ID, _PAGE_ID, layout=layout)

    interfaces_executor.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_duplicate_portal_element_sends_camel_case_duplicate_input() -> None:
    """duplicateElement input uses elementUuid, interfaceUuid, pageUuid (camelCase)."""
    dup_response = {
        "duplicateElement": {
            "element": {"id": "el-copy", "type": "text", "metadata": {}},
        }
    }
    service, _public, interfaces_executor = _make_interfaces_service(dup_response)

    result = await service.duplicate_portal_element(
        element_id=_ELEMENT_ID,
        portal_uuid=_INTERFACE_UUID,
        page_id=_PAGE_ID,
    )

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "DUPLICATE_ELEMENT_MUTATION")
    assert variables == {
        "input": {
            "elementUuid": _ELEMENT_ID,
            "interfaceUuid": _INTERFACE_UUID,
            "pageUuid": _PAGE_ID,
        }
    }
    assert result["uuid"] == "el-copy"


_MAIN_PORTAL_UUID = "portal-main-uuid"
_SUB_PORTAL_UUID = "sub-portal-uuid"
_FORMS_ELEMENT_ID = "forms-element-uuid"
_SUB_PORTAL_NAME = "Intake sub-portal"

_CREATE_SUB_PORTAL_GRAPHQL = {
    "id": _SUB_PORTAL_UUID,
    "name": _SUB_PORTAL_NAME,
}

_CREATE_SUB_PORTAL_RESPONSE = {
    "createSubPortal": {"subPortal": _CREATE_SUB_PORTAL_GRAPHQL},
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_sub_portal_calls_create_sub_portal_on_interfaces() -> None:
    """create_sub_portal uses Interfaces createSubPortal with mainPortalUuid."""
    service, interfaces_client, internal_client = _make_portal_service_with_clients(
        interfaces_return=_CREATE_SUB_PORTAL_RESPONSE,
    )

    result = await service.create_sub_portal(_MAIN_PORTAL_UUID, name=_SUB_PORTAL_NAME)

    interfaces_client.execute_query.assert_called_once()
    internal_client.execute_query.assert_not_called()
    query_used, variables = interfaces_client.execute_query.call_args[0]
    _assert_interfaces_mutation_query(query_used, "CREATE_SUB_PORTAL_MUTATION")
    assert variables == {
        "input": {
            "mainPortalUuid": _MAIN_PORTAL_UUID,
            "name": _SUB_PORTAL_NAME,
        }
    }
    assert result["uuid"] == _SUB_PORTAL_UUID
    assert result["name"] == _SUB_PORTAL_NAME


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_sub_portal_omits_name_when_not_provided() -> None:
    """Optional name is omitted from createSubPortal input when None."""
    service, interfaces_client, _internal_client = _make_portal_service_with_clients(
        interfaces_return=_CREATE_SUB_PORTAL_RESPONSE,
    )

    await service.create_sub_portal(_MAIN_PORTAL_UUID)

    _, variables = interfaces_client.execute_query.call_args[0]
    assert variables == {"input": {"mainPortalUuid": _MAIN_PORTAL_UUID}}
    assert "name" not in variables["input"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_sub_portal_element_routes_through_internal_api() -> None:
    """update_sub_portal_element uses Internal API updateSubPortalElement."""
    internal_response = {"updateSubPortalElement": {"success": True}}
    service, interfaces_client, internal_client = _make_portal_service_with_clients(
        internal_return=internal_response,
    )

    result = await service.update_sub_portal_element(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
        _SUB_PORTAL_UUID,
    )

    interfaces_client.execute_query.assert_not_called()
    internal_client.execute_query.assert_called_once()
    query_used, variables = internal_client.execute_query.call_args[0]
    _assert_internal_mutation_query(query_used, "UPDATE_SUB_PORTAL_ELEMENT_MUTATION")
    assert variables == {
        "input": {
            "portalUuid": _MAIN_PORTAL_UUID,
            "elementId": _FORMS_ELEMENT_ID,
            "subPortalUuid": _SUB_PORTAL_UUID,
        }
    }
    assert result == internal_response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_sub_portal_delegates_to_update_sub_portal_element() -> None:
    """publish_sub_portal wires subPortalUuid via updateSubPortalElement (not createElement)."""
    internal_response = {"updateSubPortalElement": {"success": True}}
    service, interfaces_client, internal_client = _make_portal_service_with_clients(
        internal_return=internal_response,
    )

    result = await service.publish_sub_portal(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
        _SUB_PORTAL_UUID,
    )

    interfaces_client.execute_query.assert_not_called()
    internal_client.execute_query.assert_called_once()
    _, variables = internal_client.execute_query.call_args[0]
    assert variables["input"]["subPortalUuid"] == _SUB_PORTAL_UUID
    assert result == internal_response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unpublish_sub_portal_sends_null_sub_portal_uuid() -> None:
    """unpublish_sub_portal clears subPortalUuid (null); 6.7 integration confirms detach."""
    service, interfaces_client, internal_client = _make_portal_service_with_clients(
        internal_return={"updateSubPortalElement": {"success": True}},
    )

    await service.unpublish_sub_portal(_MAIN_PORTAL_UUID, _FORMS_ELEMENT_ID)

    interfaces_client.execute_query.assert_not_called()
    internal_client.execute_query.assert_called_once()
    _, variables = internal_client.execute_query.call_args[0]
    assert variables == {
        "input": {
            "portalUuid": _MAIN_PORTAL_UUID,
            "elementId": _FORMS_ELEMENT_ID,
            "subPortalUuid": None,
        }
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_sub_portal_element_routes_through_internal_api() -> None:
    """delete_sub_portal_element uses Internal API deleteSubPortalElement."""
    internal_response = {"deleteSubPortalElement": {"success": True}}
    service, interfaces_client, internal_client = _make_portal_service_with_clients(
        internal_return=internal_response,
    )

    result = await service.delete_sub_portal_element(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
    )

    interfaces_client.execute_query.assert_not_called()
    internal_client.execute_query.assert_called_once()
    query_used, variables = internal_client.execute_query.call_args[0]
    _assert_internal_mutation_query(query_used, "DELETE_SUB_PORTAL_ELEMENT_MUTATION")
    assert variables == {
        "input": {
            "portalUuid": _MAIN_PORTAL_UUID,
            "elementId": _FORMS_ELEMENT_ID,
        }
    }
    assert result == internal_response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_sub_portal_calls_delete_sub_portal_interface() -> None:
    """delete_sub_portal removes the sub-portal entity via deleteSubPortalInterface."""
    internal_response = {"deleteSubPortalInterface": {"success": True}}
    service, interfaces_client, internal_client = _make_portal_service_with_clients(
        internal_return=internal_response,
    )

    result = await service.delete_sub_portal(_SUB_PORTAL_UUID)

    interfaces_client.execute_query.assert_not_called()
    internal_client.execute_query.assert_called_once()
    query_used, variables = internal_client.execute_query.call_args[0]
    _assert_internal_mutation_query(query_used, "DELETE_SUB_PORTAL_INTERFACE_MUTATION")
    assert variables == {"input": {"uuid": _SUB_PORTAL_UUID}}
    assert result == internal_response


_INTERNAL_API_PERMISSION_DENIED_ERROR = PipefyGraphQLError(
    [
        {
            "message": "User does not have permission to manage portals",
            "extensions": {
                "code": "PERMISSION_DENIED",
                "correlation_id": "abc-123",
            },
        }
    ],
)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "call_args"),
    [
        (
            "update_sub_portal_element",
            (_MAIN_PORTAL_UUID, _FORMS_ELEMENT_ID, _SUB_PORTAL_UUID),
        ),
        (
            "publish_sub_portal",
            (_MAIN_PORTAL_UUID, _FORMS_ELEMENT_ID, _SUB_PORTAL_UUID),
        ),
        (
            "unpublish_sub_portal",
            (_MAIN_PORTAL_UUID, _FORMS_ELEMENT_ID),
        ),
        (
            "delete_sub_portal_element",
            (_MAIN_PORTAL_UUID, _FORMS_ELEMENT_ID),
        ),
        ("delete_sub_portal", (_SUB_PORTAL_UUID,)),
    ],
)
async def test_sub_portal_internal_api_permission_denied_surfaces_actionable_message(
    method_name: str,
    call_args: tuple[str, ...],
) -> None:
    """PERMISSION_DENIED from the Internal API maps to portal permission guidance."""
    service, _interfaces_client, internal_client = _make_portal_service_with_clients()
    internal_client.execute_query = AsyncMock(
        side_effect=_INTERNAL_API_PERMISSION_DENIED_ERROR
    )

    with pytest.raises(PortalPermissionError, match=r"(create_portal|manage_portals)"):
        await getattr(service, method_name)(*call_args)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sub_portal_internal_api_non_permission_error_propagates() -> None:
    """Non-permission Internal API errors must not become PortalPermissionError."""
    service, _interfaces_client, internal_client = _make_portal_service_with_clients()
    bad_request = PipefyGraphQLError(
        [{"message": "Bad request", "extensions": {"code": "BAD_REQUEST"}}]
    )
    internal_client.execute_query = AsyncMock(side_effect=bad_request)

    with pytest.raises(PipefyGraphQLError, match="Bad request"):
        await service.update_sub_portal_element(
            _MAIN_PORTAL_UUID,
            _FORMS_ELEMENT_ID,
            _SUB_PORTAL_UUID,
        )


def test_get_html_interface_selects_data_source_id_name_and_filters():
    interface = GET_HTML_INTERFACE_QUERY.document.definitions[
        0
    ].selection_set.selections[0]
    pages = next(
        field
        for field in interface.selection_set.selections
        if field.name.value == "pages"
    )
    elements = next(
        field
        for field in pages.selection_set.selections
        if field.name.value == "elements"
    )
    data_sources = next(
        field
        for field in elements.selection_set.selections
        if field.name.value == "dataSources"
    )
    assert {field.name.value for field in data_sources.selection_set.selections} >= {
        "id",
        "name",
        "filters",
    }


def _selection_names(selections):
    return {field.name.value for field in selections}


def _selected_field(selections, name):
    return next(field for field in selections if field.name.value == name)


def test_get_interface_html_guidelines_selects_every_guideline_field():
    """A forgotten or misspelled field here would still pass a mocked-response test."""
    guidelines = GET_INTERFACE_HTML_GUIDELINES_QUERY.document.definitions[
        0
    ].selection_set.selections[0]
    top_level = _selection_names(guidelines.selection_set.selections)

    assert top_level == {
        "allowedAttributePrefixes",
        "allowedDataAttributes",
        "allowedDataPfyAttributes",
        "allowedPlainAttributes",
        "allowedTags",
        "authoringNotes",
        "cssRules",
        "designSystem",
        "errorCodes",
        "filters",
        "forbiddenAttributes",
        "forbiddenTags",
        "linkAttributes",
        "maxAttributesPerElement",
        "maxContentBytes",
        "maxNestingDepth",
        "urlRule",
    }

    for name in ("cssRules", "forbiddenAttributes", "forbiddenTags"):
        rule = _selected_field(guidelines.selection_set.selections, name)
        assert _selection_names(rule.selection_set.selections) == {
            "code",
            "message",
            "subject",
        }

    error_codes = _selected_field(guidelines.selection_set.selections, "errorCodes")
    assert _selection_names(error_codes.selection_set.selections) == {
        "code",
        "description",
    }

    filters = _selected_field(guidelines.selection_set.selections, "filters")
    assert _selection_names(filters.selection_set.selections) == {
        "description",
        "example",
        "fixedColumnNames",
        "knownOperators",
    }
    known_operators = _selected_field(
        filters.selection_set.selections, "knownOperators"
    )
    assert _selection_names(known_operators.selection_set.selections) == {
        "filterType",
        "operators",
    }


def test_get_portal_selects_element_data_sources_and_editable():
    """update_portal_element reads these to keep the bindings a caller omits."""
    portal = GET_PORTAL_QUERY.document.definitions[0].selection_set.selections[0]
    pages = next(
        field
        for field in portal.selection_set.selections
        if field.name.value == "pages"
    )
    elements = next(
        field
        for field in pages.selection_set.selections
        if field.name.value == "elements"
    )
    data_sources = next(
        field
        for field in elements.selection_set.selections
        if field.name.value == "dataSources"
    )
    assert {field.name.value for field in data_sources.selection_set.selections} >= {
        "id",
        "name",
        "filters",
        "repoId",
        "fieldKeys",
    }
    assert "editable" in {
        field.name.value for field in elements.selection_set.selections
    }


def test_get_portal_selects_page_layout():
    from pipefy_sdk.queries.portal_queries import GET_PORTAL_QUERY

    portal = GET_PORTAL_QUERY.document.definitions[0].selection_set.selections[0]
    pages = next(
        field
        for field in portal.selection_set.selections
        if field.name.value == "pages"
    )
    assert "layout" in {field.name.value for field in pages.selection_set.selections}


_SCRIPT_VIOLATION = {
    "code": "SCRIPT_FORBIDDEN",
    "message": "Remove the script tag.",
    "selector": "script",
    "attribute": None,
}

_ONCLICK_VIOLATION = {
    "code": "EVENT_HANDLER_FORBIDDEN",
    "message": "Remove the onclick handler.",
    "selector": "button",
    "attribute": "onclick",
}

_WRITE_HTML_DOCUMENT_VARIABLES = {
    "input": {"page_id": "page-1", "element_id": "el-1", "content": "<h1>Sales</h1>"}
}


def _html_validation_failed_error(
    violations: object, *, code: str = "HTML_VALIDATION_FAILED"
) -> PipefyGraphQLError:
    return PipefyGraphQLError(
        [
            {
                "message": "Invalid HTML",
                "extensions": {"code": code, "violations": violations},
            }
        ]
    )


async def _write_sales_heading(service: PortalService) -> dict:
    return await service.write_html_document(
        page_id="page-1", element_id="el-1", content="<h1>Sales</h1>"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_html_document_returns_the_mutation_result() -> None:
    service, _interfaces, _internal = _make_portal_service_with_clients(
        interfaces_return={"writeHtmlDocument": {"success": True}},
    )

    result = await _write_sales_heading(service)

    assert result == {"writeHtmlDocument": {"success": True}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_html_document_sends_page_element_and_content_once() -> None:
    """writeHtmlDocument takes snake_case page_id and element_id under input."""
    service, interfaces, _internal = _make_portal_service_with_clients(
        interfaces_return={"writeHtmlDocument": {"success": True}},
    )

    await _write_sales_heading(service)

    interfaces.execute_query.assert_awaited_once_with(
        WRITE_HTML_DOCUMENT_MUTATION, _WRITE_HTML_DOCUMENT_VARIABLES
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["HTML_VALIDATION_FAILED", " html_validation_failed "])
async def test_write_html_document_raises_every_violation(code: str) -> None:
    """HTML_VALIDATION_FAILED becomes HtmlValidationError carrying each violation."""
    graphql_error = _html_validation_failed_error(
        [_SCRIPT_VIOLATION, _ONCLICK_VIOLATION], code=code
    )
    service, interfaces, _internal = _make_portal_service_with_clients()
    interfaces.execute_query.side_effect = graphql_error

    with pytest.raises(HtmlValidationError) as exc_info:
        await _write_sales_heading(service)

    assert exc_info.value.violations == (
        HtmlViolation(
            code="SCRIPT_FORBIDDEN",
            message="Remove the script tag.",
            selector="script",
            attribute=None,
        ),
        HtmlViolation(
            code="EVENT_HANDLER_FORBIDDEN",
            message="Remove the onclick handler.",
            selector="button",
            attribute="onclick",
        ),
    )
    assert exc_info.value.__cause__ is graphql_error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_html_document_skips_entries_that_are_not_violations() -> None:
    """Non-objects and entries without a code or message are dropped; blanks are absent."""
    service, interfaces, _internal = _make_portal_service_with_clients()
    interfaces.execute_query.side_effect = _html_validation_failed_error(
        [
            "script",
            {"message": "Missing its code."},
            {"code": "NO_MESSAGE"},
            {
                "code": "CONTENT_TOO_LARGE",
                "message": "The document is too large.",
                "selector": " ",
                "attribute": "",
            },
        ]
    )

    with pytest.raises(HtmlValidationError) as exc_info:
        await _write_sales_heading(service)

    assert exc_info.value.violations == (
        HtmlViolation(
            code="CONTENT_TOO_LARGE",
            message="The document is too large.",
            selector=None,
            attribute=None,
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_html_document_permission_denied_raises_portal_permission_error() -> (
    None
):
    service, interfaces, _internal = _make_portal_service_with_clients()
    interfaces.execute_query.side_effect = _PERMISSION_DENIED_ERROR

    with pytest.raises(PortalPermissionError):
        await _write_sales_heading(service)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "graphql_error",
    [
        PipefyGraphQLError(
            [
                {
                    "message": "AI-generated interfaces are not enabled.",
                    "extensions": {"code": "FEATURE_BLOCKED"},
                }
            ]
        ),
        PipefyGraphQLError([{"message": "Element el-1 does not belong to page-1."}]),
        _html_validation_failed_error([_SCRIPT_VIOLATION], code="RECORD_INVALID"),
        PipefyGraphQLError(
            [
                {
                    "message": "Invalid HTML",
                    "extensions": {"code": "HTML_VALIDATION_FAILED"},
                }
            ]
        ),
        _html_validation_failed_error("script"),
        _html_validation_failed_error(["script", None, {"code": "NO_MESSAGE"}]),
    ],
    ids=[
        "other-code",
        "no-code",
        "other-code-with-violations",
        "no-violations",
        "violations-not-a-list",
        "no-usable-violation",
    ],
)
async def test_write_html_document_keeps_the_api_error_without_usable_violations(
    graphql_error: PipefyGraphQLError,
) -> None:
    service, interfaces, _internal = _make_portal_service_with_clients()
    interfaces.execute_query.side_effect = graphql_error

    with pytest.raises(PipefyGraphQLError) as exc_info:
        await _write_sales_heading(service)

    assert exc_info.value is graphql_error


_HTML_PAGE_ID = "html-page-uuid-1"
_HTML_ELEMENT_ID = "html-element-uuid-1"
_HTML_ELEMENT_METADATA = {"name": "Requests board"}
_REQUEST_AMOUNT_FIELD_UUID = "6a850d1c-0000-4000-8000-000000000016"
_OPEN_REQUESTS_SOURCE = {
    "id": "open-requests",
    "name": "Open requests",
    "repoId": EXAMPLE_PIPE_REPO_ID,
    "fieldKeys": ["title", _REQUEST_AMOUNT_FIELD_UUID],
    "filters": _OPEN_FILTER,
}
_ALL_SUPPLIERS_SOURCE = {
    "id": "all-suppliers",
    "name": "All suppliers",
    "repoId": "repo-uuid-2",
    "fieldKeys": ["title"],
}


def _html_interface_with_custom_code(
    *, editable: bool = False, element_type: str = "customCode"
) -> dict:
    """``interface`` payload: the target on its page, after a sibling on another page."""
    return {
        "interface": {
            "id": "html-uuid-1",
            "name": "Requests",
            "visibility": "internal",
            "contentModeHtml": True,
            "pages": [
                {
                    "id": _PAGE_ID_2,
                    "title": "Other",
                    "elements": [
                        {
                            "id": "sibling-element",
                            "type": "customCode",
                            "metadata": {"name": "Other"},
                            "editable": not editable,
                            "dataSources": [],
                            "htmlDocument": None,
                        }
                    ],
                },
                {
                    "id": _HTML_PAGE_ID,
                    "title": "Requests",
                    "elements": [
                        {
                            "id": _HTML_ELEMENT_ID,
                            "type": element_type,
                            "metadata": _HTML_ELEMENT_METADATA,
                            "editable": editable,
                            "dataSources": [],
                            "htmlDocument": None,
                        }
                    ],
                },
            ],
        }
    }


_UPDATE_SUCCEEDED = {"updateElement": {"success": True}}


def _set_sources_service(
    read: dict, update: dict | Exception = _UPDATE_SUCCEEDED
) -> tuple[PortalService, MagicMock]:
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = [read, update]
    return service, interfaces_executor


def _sent_update_input(interfaces_executor: MagicMock) -> dict:
    """The ``input`` of the ``updateElement`` call, the last one sent."""
    return interfaces_executor.execute_query.await_args_list[-1].args[1]["input"]


async def _set_open_requests_and_suppliers(service: PortalService) -> dict:
    return await service.set_interface_sources(
        _HTML_PAGE_ID,
        _HTML_ELEMENT_ID,
        [_OPEN_REQUESTS_SOURCE, _ALL_SUPPLIERS_SOURCE],
        interface_uuid="html-uuid-1",
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("stored_editable", [False, True])
async def test_set_interface_sources_replaces_sources_keeping_metadata_and_editable(
    stored_editable: bool,
) -> None:
    """The API fails a write with field keys and no editable, so the flag goes back."""
    service, interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code(editable=stored_editable)
    )

    await _set_open_requests_and_suppliers(service)

    assert interfaces_executor.execute_query.await_args_list == [
        mock_call(GET_HTML_INTERFACE_QUERY, {"uuid": "html-uuid-1"}),
        mock_call(
            UPDATE_ELEMENT_MUTATION,
            {
                "input": {
                    "element_id": _HTML_ELEMENT_ID,
                    "page_id": _HTML_PAGE_ID,
                    "metadata": '{"name":"Requests board"}',
                    "editable": stored_editable,
                    "data_sources": [
                        {**_OPEN_REQUESTS_SOURCE, "filters": _OPEN_FILTER_JSON},
                        _ALL_SUPPLIERS_SOURCE,
                    ],
                }
            },
        ),
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_interface_sources_takes_parsed_sources() -> None:
    service, interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code()
    )

    await service.set_interface_sources(
        _HTML_PAGE_ID,
        _HTML_ELEMENT_ID,
        [InterfaceDataSource.model_validate(_ALL_SUPPLIERS_SOURCE)],
        interface_uuid="html-uuid-1",
    )

    assert _sent_update_input(interfaces_executor)["data_sources"] == [
        _ALL_SUPPLIERS_SOURCE
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_interface_sources_returns_the_source_handles_set() -> None:
    service, _interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code()
    )

    result = await _set_open_requests_and_suppliers(service)

    assert result == {
        "id": _HTML_ELEMENT_ID,
        "uuid": _HTML_ELEMENT_ID,
        "dataSources": [
            _OPEN_REQUESTS_SOURCE,
            {**_ALL_SUPPLIERS_SOURCE, "filters": None},
        ],
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_interface_sources_empty_list_removes_every_source() -> None:
    service, interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code()
    )

    await service.set_interface_sources(
        _HTML_PAGE_ID, _HTML_ELEMENT_ID, [], interface_uuid="html-uuid-1"
    )

    assert _sent_update_input(interfaces_executor)["data_sources"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_interface_sources_rejects_invalid_sources_before_any_call() -> None:
    service, interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code()
    )

    with pytest.raises(ValidationError, match="own id"):
        await service.set_interface_sources(
            _HTML_PAGE_ID,
            _HTML_ELEMENT_ID,
            [_OPEN_REQUESTS_SOURCE, {**_ALL_SUPPLIERS_SOURCE, "id": "open-requests"}],
            interface_uuid="html-uuid-1",
        )

    interfaces_executor.execute_query.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("page_id", "element_id", "element_type", "message"),
    [
        (_PAGE_ID_2, _HTML_ELEMENT_ID, "customCode", f"page_id='{_HTML_PAGE_ID}'"),
        (
            _HTML_PAGE_ID,
            "missing-element",
            "customCode",
            "no page of interface 'html-uuid-1'",
        ),
        (_HTML_PAGE_ID, _HTML_ELEMENT_ID, "table", "customCode element"),
    ],
    ids=["on another page", "on no page", "not customCode"],
)
async def test_set_interface_sources_wrong_element_reads_but_sends_no_update(
    page_id: str, element_id: str, element_type: str, message: str
) -> None:
    service, interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code(element_type=element_type)
    )

    with pytest.raises(ValueError, match=message):
        await service.set_interface_sources(
            page_id, element_id, [_ALL_SUPPLIERS_SOURCE], interface_uuid="html-uuid-1"
        )

    interfaces_executor.execute_query.assert_awaited_once_with(
        GET_HTML_INTERFACE_QUERY, {"uuid": "html-uuid-1"}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_interface_sources_unsuccessful_update_raises_value_error() -> None:
    service, _interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code(), {"updateElement": {"success": False}}
    )

    with pytest.raises(ValueError, match="success=false"):
        await _set_open_requests_and_suppliers(service)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_interface_sources_permission_denied_raises_portal_permission_error() -> (
    None
):
    service, _interfaces_executor = _set_sources_service(
        _html_interface_with_custom_code(), _PERMISSION_DENIED_ERROR
    )

    with pytest.raises(PortalPermissionError):
        await _set_open_requests_and_suppliers(service)


def test_get_html_interface_selects_element_metadata_and_editable():
    """set_interface_sources sends both back, since the update replaces them."""
    assert {"metadata", "editable"} <= _selected_fields(
        GET_HTML_INTERFACE_QUERY, "pages", "elements"
    )


_CREATE_INTERFACE_RESPONSE = {
    "createInterface": {
        "interface": {
            "id": "new-interface-uuid",
            "name": "Open purchase requests",
            "visibility": "internal",
            "contentModeHtml": True,
            "pages": [
                {
                    "id": "new-page-uuid",
                    "title": "Open purchase requests",
                    "elements": [{"id": "new-element-uuid", "type": "customCode"}],
                }
            ],
        },
        "success": True,
    }
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_calls_create_interface_with_validated_input() -> None:
    """create_interface sends one page with one customCode element, data_sources: []."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_INTERFACE_RESPONSE,
    )

    await service.create_interface(EXAMPLE_ORG_UUID, "Open purchase requests")

    interfaces_executor.execute_query.assert_called_once()
    query_used, variables = interfaces_executor.execute_query.call_args[0]
    assert query_used is CREATE_INTERFACE_MUTATION
    assert variables == {
        "input": {
            "org_uuid": EXAMPLE_ORG_UUID,
            "name": "Open purchase requests",
            "contentModeHtml": True,
            "pages": [
                {
                    "title": "Open purchase requests",
                    "layout": "[]",
                    "elements": [
                        {
                            "type": "customCode",
                            "metadata": "{}",
                            "dataSources": [],
                        }
                    ],
                }
            ],
        }
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_returns_uuid_alias() -> None:
    """The interface, its page and its element all get the uuid alias."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        _CREATE_INTERFACE_RESPONSE,
    )

    result = await service.create_interface(EXAMPLE_ORG_UUID, "Open purchase requests")

    assert result["uuid"] == "new-interface-uuid"
    assert result["name"] == "Open purchase requests"
    assert result["pages"][0]["uuid"] == "new-page-uuid"
    assert result["pages"][0]["elements"][0]["uuid"] == "new-element-uuid"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_sends_the_full_data_source_shape() -> None:
    """id, name and filters ride on the element's data source, not just repoId/fieldKeys.

    A ``customCode`` element requires id/name on every source, so dropping them
    (as the normalizer shared with create_portal_element/update_portal_element
    does) would make the backend reject any non-empty data_sources outright.
    """
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_INTERFACE_RESPONSE,
    )

    await service.create_interface(
        EXAMPLE_ORG_UUID,
        "Open purchase requests",
        data_sources=[
            {
                "id": "source-1",
                "name": "Purchase requests",
                "repoId": EXAMPLE_PIPE_REPO_ID,
                "fieldKeys": ["status"],
                "filters": {"status": {"eq": "open"}},
            }
        ],
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["pages"][0]["elements"][0]["dataSources"] == [
        {
            "id": "source-1",
            "name": "Purchase requests",
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "fieldKeys": ["status"],
            "filters": json.dumps(
                {"status": {"eq": "open"}}, separators=(",", ":"), ensure_ascii=False
            ),
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_rejects_invalid_data_sources_before_any_call() -> None:
    """A duplicate id across sources is rejected before resolving the org or calling createInterface."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        _CREATE_INTERFACE_RESPONSE,
    )

    with pytest.raises(ValidationError, match="own id"):
        await service.create_interface(
            EXAMPLE_ORG_UUID,
            "Open purchase requests",
            data_sources=[
                {
                    "id": "source-1",
                    "name": "Open requests",
                    "repoId": EXAMPLE_PIPE_REPO_ID,
                    "fieldKeys": ["status"],
                },
                {
                    "id": "source-1",
                    "name": "All suppliers",
                    "repoId": "repo-uuid-2",
                    "fieldKeys": ["title"],
                },
            ],
        )

    public_executor.execute_query.assert_not_awaited()
    interfaces_executor.execute_query.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_takes_parsed_data_sources() -> None:
    """A caller may pass already-validated InterfaceDataSource instances, not just dicts."""
    service, _public, interfaces_executor = _make_interfaces_service(
        _CREATE_INTERFACE_RESPONSE,
    )
    source = InterfaceDataSource.model_validate(
        {
            "id": "source-1",
            "name": "Purchase requests",
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "fieldKeys": ["status"],
        }
    )

    await service.create_interface(
        EXAMPLE_ORG_UUID, "Open purchase requests", data_sources=[source]
    )

    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["pages"][0]["elements"][0]["dataSources"] == [
        {
            "id": "source-1",
            "name": "Purchase requests",
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "fieldKeys": ["status"],
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_numeric_org_id_resolves_via_main_graphql_client() -> (
    None
):
    """Numeric org ids resolve on the public GraphQL client before createInterface."""
    service, public_executor, interfaces_executor = _make_interfaces_service(
        _CREATE_INTERFACE_RESPONSE,
    )
    public_executor.execute_query = AsyncMock(
        return_value={"organization": {"uuid": EXAMPLE_ORG_UUID}}
    )

    await service.create_interface(EXAMPLE_NUMERIC_ORG_ID, "Open purchase requests")

    public_executor.execute_query.assert_called_once_with(
        RESOLVE_ORGANIZATION_UUID_QUERY,
        {"id": EXAMPLE_NUMERIC_ORG_ID},
    )
    _, variables = interfaces_executor.execute_query.call_args[0]
    assert variables["input"]["org_uuid"] == EXAMPLE_ORG_UUID


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_raises_when_response_has_no_interface() -> None:
    """A malformed createInterface response (no interface) raises ValueError."""
    service, _public, _interfaces_executor = _make_interfaces_service(
        {"createInterface": {"success": True}},
    )

    with pytest.raises(ValueError, match="createInterface returned no interface"):
        await service.create_interface(EXAMPLE_ORG_UUID, "Open purchase requests")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_interface_permission_denied_raises_portal_permission_error() -> (
    None
):
    """A permission-denied createInterface failure maps like every other portal write."""
    service, _public, interfaces_executor = _make_interfaces_service(None)
    interfaces_executor.execute_query.side_effect = _PERMISSION_DENIED_ERROR

    with pytest.raises(PortalPermissionError):
        await service.create_interface(EXAMPLE_ORG_UUID, "Open purchase requests")
