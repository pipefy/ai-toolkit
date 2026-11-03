"""Tests for portal MCP tools (mocked PipefyClient)."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from _mcp_compat import (
    create_connected_server_and_client_session as create_client_session,
)
from _shared.fixture_ids import EXAMPLE_NUMERIC_ORG_ID, EXAMPLE_PIPE_REPO_ID
from gql.transport.exceptions import TransportError
from pipefy_sdk import PipefyClient, PipefyGraphQLError
from pipefy_sdk.exceptions import (
    HtmlValidationError,
    HtmlViolation,
    PortalPermissionError,
)
from pipefy_sdk.models.portal import (
    InterfaceDataSource,
    OpenRecordAction,
    TriggerAutomationAction,
    parse_portal_page_layout,
)

from pipefy_mcp.core.tool_error_envelope import tool_error_message
from pipefy_mcp.tools.portal_tools import PortalTools
from tools.conftest import assert_invalid_arguments_envelope, build_tool_test_server
from tools.destructive_confirm_test_support import confirm_after_preview

_PORTAL_LIST_NODE = {
    "id": "portal-uuid-1",
    "uuid": "portal-uuid-1",
    "name": "Main Portal",
    "visibility": "internal",
    "subType": "portal",
}

_PORTAL_DETAIL = {
    "id": "portal-uuid-1",
    "uuid": "portal-uuid-1",
    "name": "Main Portal",
    "visibility": "public",
    "published": True,
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
    "subPortals": [{"id": "sub-1", "uuid": "sub-1", "name": "Sub Portal 1"}],
}

_CREATED_PORTAL = {
    "id": "portal-created-uuid",
    "uuid": "portal-created-uuid",
    "name": "Org Portal",
    "visibility": "internal",
    "subType": "portal",
}

_PORTAL_PERMISSION_DENIED_MSG = (
    "Permission denied. Request organization permissions such as "
    "`create_portal` or `manage_portals` from your admin."
)

_INTERNAL_API_PERMISSION_DENIED_ERROR = PipefyGraphQLError(
    [
        {
            "message": "User does not have permission to manage portals",
            "extensions": {"code": "PERMISSION_DENIED", "correlation_id": "abc-123"},
        }
    ]
)

_PORTAL_UUID = "portal-uuid-1"
_PAGE_UUID = "page-uuid-1"
_PAGE_UUID_2 = "page-uuid-2"
_PAGE_TITLE = "Portal Home"

_CREATED_PAGE = {
    "id": _PAGE_UUID,
    "uuid": _PAGE_UUID,
    "title": _PAGE_TITLE,
    "elements": [{"id": "el-1", "uuid": "el-1", "type": "text"}],
}

_PAGE_LAYOUT = [{"id": "row-1", "type": "row", "children": ["el-1"]}]

_ELEMENT_UUID = "el-uuid-1"
_FORMS_METADATA = {"name": "Request form"}
_FORMS_DATA_SOURCES = [{"repoId": EXAMPLE_PIPE_REPO_ID}]

_CREATED_ELEMENT = {
    "id": _ELEMENT_UUID,
    "uuid": _ELEMENT_UUID,
    "type": "forms",
    "metadata": _FORMS_METADATA,
}

_MAIN_PORTAL_UUID = _PORTAL_UUID
_SUB_PORTAL_UUID = "sub-portal-uuid-1"
_FORMS_ELEMENT_ID = "el-forms-1"
_SUB_PORTAL_NAME = "Sub Portal 1"

_CREATED_SUB_PORTAL = {
    "id": _SUB_PORTAL_UUID,
    "uuid": _SUB_PORTAL_UUID,
    "name": _SUB_PORTAL_NAME,
}

_SUB_PORTAL_WRITE_TOOL_NAMES = [
    "create_sub_portal",
    "update_sub_portal_element",
    "publish_sub_portal",
    "unpublish_sub_portal",
    "delete_sub_portal_element",
    "delete_sub_portal",
]


@pytest.fixture
def mock_portal_client():
    client = MagicMock(PipefyClient)
    client.list_portals = AsyncMock()
    client.get_portal = AsyncMock()
    client.get_interface_html_guidelines = AsyncMock()
    client.list_interface_repos = AsyncMock()
    client.get_interface_repo_fields = AsyncMock()
    client.set_interface_sources = AsyncMock()
    client.set_interface_actions = AsyncMock()
    client.list_html_interfaces = AsyncMock()
    client.get_html_interface = AsyncMock()
    client.write_html_document = AsyncMock()
    client.create_interface = AsyncMock()
    client.create_portal = AsyncMock()
    client.update_portal = AsyncMock()
    client.delete_portal = AsyncMock()
    client.create_portal_page = AsyncMock()
    client.update_portal_page = AsyncMock()
    client.delete_portal_page = AsyncMock()
    client.sort_portal_pages = AsyncMock()
    client.update_portal_page_layout = AsyncMock()
    client.create_portal_element = AsyncMock()
    client.update_portal_element = AsyncMock()
    client.delete_portal_element = AsyncMock()
    client.duplicate_portal_element = AsyncMock()
    client.create_sub_portal = AsyncMock()
    client.update_sub_portal_element = AsyncMock()
    client.publish_sub_portal = AsyncMock()
    client.unpublish_sub_portal = AsyncMock()
    client.delete_sub_portal_element = AsyncMock()
    client.delete_sub_portal = AsyncMock()
    return client


@pytest.fixture
def portal_mcp_server(mock_portal_client):
    return build_tool_test_server(
        "Pipefy Portal Tools Test", PortalTools.register, mock_portal_client
    )


@pytest.fixture
def portal_session(portal_mcp_server, request):
    elicitation = getattr(request, "param", None)
    return create_client_session(
        portal_mcp_server,
        read_timeout_seconds=timedelta(seconds=10),
        raise_exceptions=True,
        elicitation_callback=elicitation,
    )


@pytest.mark.anyio
async def test_list_portals_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_portals = AsyncMock(return_value=[_PORTAL_LIST_NODE])

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals", {"organization_uuid": "org-abc-123"}
        )

    assert result.is_error is False
    mock_portal_client.list_portals.assert_awaited_once_with(
        "org-abc-123", search_term=None
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert "result" in payload
    assert payload["data"]["portals"] == [_PORTAL_LIST_NODE]
    assert payload["data"]["portals"][0]["name"] == "Main Portal"


@pytest.mark.anyio
async def test_list_portals_coerces_int_organization_uuid(
    portal_session, mock_portal_client, extract_payload
):
    """mcporter CLI sends numeric IDs as int; PipefyId must coerce to str."""
    mock_portal_client.list_portals = AsyncMock(return_value=[])

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals",
            {"organization_uuid": int(EXAMPLE_NUMERIC_ORG_ID)},
        )

    assert result.is_error is False
    mock_portal_client.list_portals.assert_awaited_once_with(
        EXAMPLE_NUMERIC_ORG_ID, search_term=None
    )
    payload = extract_payload(result)
    assert payload["success"] is True


@pytest.mark.anyio
async def test_list_portals_passes_search_term(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_portals = AsyncMock(return_value=[])

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals",
            {"organization_uuid": "org-abc-123", "search_term": "intake"},
        )

    assert result.is_error is False
    mock_portal_client.list_portals.assert_awaited_once_with(
        "org-abc-123", search_term="intake"
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["portals"] == []


@pytest.mark.anyio
async def test_list_portals_empty_returns_empty_list(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_portals = AsyncMock(return_value=[])

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals", {"organization_uuid": "org-empty"}
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["portals"] == []


@pytest.mark.anyio
async def test_list_portals_value_error_returns_error_envelope(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_portals = AsyncMock(
        side_effect=ValueError("Organization 'org-bad' was not found.")
    )

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals", {"organization_uuid": "org-bad"}
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "not found" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_get_portal_success(portal_session, mock_portal_client, extract_payload):
    mock_portal_client.get_portal = AsyncMock(return_value=_PORTAL_DETAIL)

    async with portal_session as session:
        result = await session.call_tool("get_portal", {"portal_uuid": "portal-uuid-1"})

    assert result.is_error is False
    mock_portal_client.get_portal.assert_awaited_once_with("portal-uuid-1")
    payload = extract_payload(result)
    assert payload["success"] is True
    assert "result" in payload
    assert payload["data"]["uuid"] == "portal-uuid-1"
    assert payload["data"]["published"] is True
    assert payload["data"]["pages"][0]["title"] == "Home"
    assert payload["data"]["pages"][0]["layout"] == _PAGE_LAYOUT
    assert payload["data"]["subPortals"][0]["name"] == "Sub Portal 1"


@pytest.mark.anyio
async def test_get_portal_not_found_returns_error_envelope(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.get_portal = AsyncMock(
        side_effect=ValueError("Portal 'portal-missing' was not found.")
    )

    async with portal_session as session:
        result = await session.call_tool(
            "get_portal", {"portal_uuid": "portal-missing"}
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "not found" in tool_error_message(payload).lower()


_HTML_GUIDELINES = {
    "allowedTags": ["div", "span", "p"],
    "forbiddenTags": [
        {"code": "SCRIPT_FORBIDDEN", "message": "No <script>.", "subject": "script"}
    ],
    "forbiddenAttributes": [
        {
            "code": "ID_ATTRIBUTE_FORBIDDEN",
            "message": "Use data-pfy-id.",
            "subject": "id",
        }
    ],
    "cssRules": [
        {"code": "CSS_IMPORT_FORBIDDEN", "message": "No @import.", "subject": "@import"}
    ],
    "errorCodes": [
        {"code": "TAG_NOT_ALLOWED", "description": "A tag outside allowedTags."}
    ],
    "filters": {
        "description": "A filter is a tree.",
        "example": {"id": "f1", "type": "root", "conjunction": "and", "filterSet": []},
        "fixedColumnNames": ["title"],
        "knownOperators": [{"filterType": "text", "operators": ["eq"]}],
    },
    "designSystem": None,
    "maxContentBytes": 200000,
    "maxNestingDepth": 398,
    "maxAttributesPerElement": 400,
}


@pytest.mark.anyio
async def test_get_interface_html_guidelines_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.get_interface_html_guidelines = AsyncMock(
        return_value=_HTML_GUIDELINES
    )

    async with portal_session as session:
        result = await session.call_tool("get_interface_html_guidelines", {})

    assert result.is_error is False
    mock_portal_client.get_interface_html_guidelines.assert_awaited_once_with(
        include_design_system=False
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert "result" in payload
    assert payload["data"]["allowedTags"] == ["div", "span", "p"]
    assert payload["data"]["filters"]["knownOperators"][0]["filterType"] == "text"


_SAMPLE_DESIGN_SYSTEM = {
    "name": "Flow",
    "version": "0.1.0-alpha.17",
    "instructions": ["Use classes verbatim; never invent one."],
    "tokens": ["--background", "--foreground"],
    "icons": ["arrow-down", "check"],
    "components": [
        {
            "name": "button",
            "category": "Primitives",
            "classes": ["cn-button-variant-default", "cn-button-variant-destructive"],
            "use": ["Actions that change something."],
            "avoid": ["An icon button without aria-label."],
            "examples": [
                {
                    "title": "Destructive",
                    "html": (
                        '<button class="cn-button-variant-destructive" '
                        'aria-label="Delete record">Delete</button>'
                    ),
                },
            ],
        },
    ],
}


@pytest.mark.anyio
async def test_get_interface_html_guidelines_round_trips_a_sample_design_system(
    portal_session, mock_portal_client, extract_payload
):
    guidelines = {**_HTML_GUIDELINES, "designSystem": _SAMPLE_DESIGN_SYSTEM}
    mock_portal_client.get_interface_html_guidelines = AsyncMock(
        return_value=guidelines
    )

    async with portal_session as session:
        result = await session.call_tool(
            "get_interface_html_guidelines", {"include_design_system": True}
        )

    assert result.is_error is False
    mock_portal_client.get_interface_html_guidelines.assert_awaited_once_with(
        include_design_system=True
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["designSystem"] == _SAMPLE_DESIGN_SYSTEM
    component = payload["data"]["designSystem"]["components"][0]
    assert component["examples"][0]["html"] == (
        '<button class="cn-button-variant-destructive" aria-label="Delete record">Delete</button>'
    )
    assert json.loads(payload["result"])["designSystem"] == _SAMPLE_DESIGN_SYSTEM


@pytest.mark.anyio
async def test_get_interface_html_guidelines_leaves_out_the_design_system_by_default(
    portal_session, mock_portal_client, extract_payload
):
    """The catalog is most of the response; without it the rules fit a client's view."""
    guidelines = {k: v for k, v in _HTML_GUIDELINES.items() if k != "designSystem"}
    mock_portal_client.get_interface_html_guidelines = AsyncMock(
        return_value=guidelines
    )

    async with portal_session as session:
        result = await session.call_tool("get_interface_html_guidelines", {})

    mock_portal_client.get_interface_html_guidelines.assert_awaited_once_with(
        include_design_system=False
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert "designSystem" not in payload["data"]


@pytest.mark.anyio
async def test_get_interface_html_guidelines_transport_error_returns_error_envelope(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.get_interface_html_guidelines = AsyncMock(
        side_effect=TransportError("connection reset")
    )

    async with portal_session as session:
        result = await session.call_tool("get_interface_html_guidelines", {})

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False


_HTML_INTERFACE = {
    "id": "html-uuid-1",
    "uuid": "html-uuid-1",
    "name": "Open purchase requests",
    "visibility": "internal",
    "contentModeHtml": True,
    "pages": [
        {
            "id": _PAGE_UUID,
            "uuid": _PAGE_UUID,
            "title": "Open purchase requests",
            "elements": [
                {
                    "id": "el-custom-1",
                    "uuid": "el-custom-1",
                    "type": "customCode",
                    "htmlDocument": {
                        "content": "<div>Hello</div>",
                        "contentHash": "abc123",
                        "createdAt": "2026-10-22T00:00:00Z",
                    },
                }
            ],
        }
    ],
}

_CREATED_HTML_INTERFACE = {
    "id": "html-uuid-new",
    "uuid": "html-uuid-new",
    "name": "Open purchase requests",
    "visibility": "internal",
    "contentModeHtml": True,
    "pages": [
        {
            "id": "page-new-1",
            "uuid": "page-new-1",
            "title": "Open purchase requests",
            "elements": [{"id": "el-new-1", "uuid": "el-new-1", "type": "customCode"}],
        }
    ],
}


@pytest.mark.anyio
async def test_list_interfaces_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_html_interfaces = AsyncMock(
        return_value=[
            {
                "id": "html-uuid-1",
                "uuid": "html-uuid-1",
                "name": "Open purchase requests",
                "visibility": "internal",
                "contentModeHtml": True,
            }
        ]
    )

    async with portal_session as session:
        result = await session.call_tool(
            "list_interfaces", {"organization_uuid": "org-abc-123"}
        )

    assert result.is_error is False
    mock_portal_client.list_html_interfaces.assert_awaited_once_with(
        "org-abc-123", search_term=None
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["interfaces"][0]["name"] == "Open purchase requests"


@pytest.mark.anyio
async def test_get_interface_html_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.get_html_interface = AsyncMock(return_value=_HTML_INTERFACE)

    async with portal_session as session:
        result = await session.call_tool(
            "get_interface_html", {"interface_uuid": "html-uuid-1"}
        )

    assert result.is_error is False
    mock_portal_client.get_html_interface.assert_awaited_once_with("html-uuid-1")
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["uuid"] == "html-uuid-1"
    assert (
        payload["data"]["pages"][0]["elements"][0]["htmlDocument"]["content"]
        == "<div>Hello</div>"
    )


@pytest.mark.anyio
async def test_get_interface_html_not_found_returns_error_envelope(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.get_html_interface = AsyncMock(
        side_effect=ValueError("Interface 'html-missing' was not found.")
    )

    async with portal_session as session:
        result = await session.call_tool(
            "get_interface_html", {"interface_uuid": "html-missing"}
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "not found" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_get_interface_html_not_found_graphql_error_names_the_interface(
    portal_session, mock_portal_client, extract_payload
):
    """A raw not-found GraphQL error must not reach the agent verbatim."""
    mock_portal_client.get_html_interface = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the interface"}])
    )

    async with portal_session as session:
        result = await session.call_tool(
            "get_interface_html", {"interface_uuid": "html-missing"}
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert tool_error_message(payload) == "No HTML interface has uuid 'html-missing'."


@pytest.mark.anyio
async def test_write_interface_html_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.write_html_document = AsyncMock(return_value={"success": True})

    async with portal_session as session:
        result = await session.call_tool(
            "write_interface_html",
            {
                "page_id": _PAGE_UUID,
                "element_id": "el-custom-1",
                "content": "<div>Hello</div>",
            },
        )

    assert result.is_error is False
    mock_portal_client.write_html_document.assert_awaited_once_with(
        page_id=_PAGE_UUID, element_id="el-custom-1", content="<div>Hello</div>"
    )
    payload = extract_payload(result)
    assert payload["success"] is True


@pytest.mark.anyio
async def test_write_interface_html_rejects_blank_content(
    portal_session, mock_portal_client
):
    async with portal_session as session:
        result = await session.call_tool(
            "write_interface_html",
            {"page_id": _PAGE_UUID, "element_id": "el-custom-1", "content": "   "},
        )

    assert_invalid_arguments_envelope(result)
    mock_portal_client.write_html_document.assert_not_awaited()


@pytest.mark.anyio
async def test_write_interface_html_validation_failed_lists_every_violation(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.write_html_document = AsyncMock(
        side_effect=HtmlValidationError(
            (
                HtmlViolation(
                    code="SCRIPT_FORBIDDEN",
                    message="<script> is not allowed.",
                    selector="body > script",
                    attribute=None,
                ),
            )
        )
    )

    async with portal_session as session:
        result = await session.call_tool(
            "write_interface_html",
            {
                "page_id": _PAGE_UUID,
                "element_id": "el-custom-1",
                "content": "<script>bad()</script>",
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "script" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_create_html_interface_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_interface = AsyncMock(
        return_value=_CREATED_HTML_INTERFACE
    )
    mock_portal_client.write_html_document = AsyncMock(return_value={"success": True})

    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
            },
        )

    assert result.is_error is False
    mock_portal_client.create_interface.assert_awaited_once_with(
        "org-abc-123", "Open purchase requests", color="blue", data_sources=[]
    )
    mock_portal_client.write_html_document.assert_awaited_once_with(
        page_id="page-new-1", element_id="el-new-1", content="<div>Hello</div>"
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["uuid"] == "html-uuid-new"


@pytest.mark.anyio
async def test_create_html_interface_invalid_color_returns_validation_envelope(
    portal_session, mock_portal_client
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
                "color": "chartreuse",
            },
        )

    assert_invalid_arguments_envelope(result)
    mock_portal_client.create_interface.assert_not_awaited()


@pytest.mark.anyio
async def test_create_html_interface_rejects_blank_html(
    portal_session, mock_portal_client
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "   ",
            },
        )

    assert_invalid_arguments_envelope(result)
    mock_portal_client.create_interface.assert_not_awaited()


@pytest.mark.anyio
async def test_create_html_interface_write_failure_returns_ids_to_retry(
    portal_session, mock_portal_client, extract_payload
):
    """A failed second call must not be retried as a second create_html_interface."""
    mock_portal_client.create_interface = AsyncMock(
        return_value=_CREATED_HTML_INTERFACE
    )
    mock_portal_client.write_html_document = AsyncMock(
        side_effect=ValueError("Page does not have this element.")
    )

    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    details = payload["error"]["details"]
    assert details["uuid"] == "html-uuid-new"
    assert details["page_id"] == "page-new-1"
    assert details["element_id"] == "el-new-1"
    message = tool_error_message(payload)
    assert "already created" in message
    assert "write_interface_html" in message
    assert "page_id='page-new-1'" in message
    assert "element_id='el-new-1'" in message
    assert "do not call create_html_interface again" in message


@pytest.mark.anyio
async def test_create_html_interface_no_page_returned_warns_before_retry(
    portal_session, mock_portal_client, extract_payload
):
    """createInterface succeeding with no usable page must not be retried blindly."""
    mock_portal_client.create_interface = AsyncMock(
        return_value={**_CREATED_HTML_INTERFACE, "pages": []}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["details"]["uuid"] == "html-uuid-new"
    message = tool_error_message(payload)
    assert "may already exist" in message
    assert "get_interface_html" in message
    assert "instead of calling create_html_interface again" in message
    mock_portal_client.write_html_document.assert_not_awaited()


@pytest.mark.anyio
async def test_create_html_interface_forwards_data_sources(
    portal_session, mock_portal_client
):
    mock_portal_client.create_interface = AsyncMock(
        return_value=_CREATED_HTML_INTERFACE
    )
    mock_portal_client.write_html_document = AsyncMock(return_value={"success": True})
    data_sources = [
        {
            "id": "open-requests",
            "name": "Open requests",
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "fieldKeys": ["status"],
        }
    ]

    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
                "data_sources": data_sources,
            },
        )

    assert result.is_error is False
    mock_portal_client.create_interface.assert_awaited_once_with(
        "org-abc-123",
        "Open purchase requests",
        color="blue",
        data_sources=[InterfaceDataSource.model_validate(data_sources[0])],
    )


@pytest.mark.anyio
async def test_create_html_interface_invalid_data_source_returns_error_envelope(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
                "data_sources": [{"id": "x", "name": "X"}],
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "repoId" in tool_error_message(payload)
    mock_portal_client.create_interface.assert_not_awaited()


@pytest.mark.anyio
async def test_create_html_interface_rejects_an_eleventh_data_source(
    portal_session, mock_portal_client
):
    data_sources = [
        {
            "id": f"source-{i}",
            "name": f"Source {i}",
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "fieldKeys": ["status"],
        }
        for i in range(11)
    ]

    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
                "data_sources": data_sources,
            },
        )

    assert_invalid_arguments_envelope(result)
    mock_portal_client.create_interface.assert_not_awaited()


@pytest.mark.anyio
async def test_list_portals_transport_error_returns_error_envelope(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_portals = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "timeout"}])
    )

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals", {"organization_uuid": "org-abc-123"}
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    err = payload.get("error")
    assert isinstance(err, dict) and "message" in err


@pytest.mark.anyio
@pytest.mark.parametrize("exc_message", ["", "   "])
async def test_list_portals_empty_exception_message_uses_fallback(
    portal_session, mock_portal_client, extract_payload, exc_message
):
    mock_portal_client.list_portals = AsyncMock(side_effect=RuntimeError(exc_message))

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals", {"organization_uuid": "org-abc-123"}
        )

    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload)
    assert message == "Portal request failed."
    assert "do not blind-retry" not in message


@pytest.mark.anyio
@pytest.mark.parametrize("exc_message", ["", "   "])
async def test_list_portals_whitespace_permission_denied_uses_guidance(
    portal_session, mock_portal_client, extract_payload, exc_message
):
    mock_portal_client.list_portals = AsyncMock(
        side_effect=PipefyGraphQLError(
            [
                {
                    "message": exc_message,
                    "extensions": {"code": "PERMISSION_DENIED"},
                }
            ]
        )
    )

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals", {"organization_uuid": "org-abc-123"}
        )

    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload)
    assert "create_portal" in message
    assert "manage_portals" in message
    assert "do not blind-retry" not in message


@pytest.mark.anyio
async def test_list_portals_preserves_non_empty_exception_message(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_portals = AsyncMock(side_effect=RuntimeError("portal boom"))

    async with portal_session as session:
        result = await session.call_tool(
            "list_portals", {"organization_uuid": "org-abc-123"}
        )

    payload = extract_payload(result)
    assert payload["success"] is False
    assert "portal boom" in tool_error_message(payload)


@pytest.mark.anyio
async def test_get_portal_transport_error_returns_error_envelope(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.get_portal = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "timeout"}])
    )

    async with portal_session as session:
        result = await session.call_tool("get_portal", {"portal_uuid": "portal-uuid-1"})

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    err = payload.get("error")
    assert isinstance(err, dict) and "message" in err


@pytest.mark.anyio
async def test_read_tools_have_readonly_hint(portal_session):
    read_tool_names = ["list_portals", "get_portal"]

    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    for name in read_tool_names:
        tool = tool_map[name]
        assert tool.annotations is not None, f"{name} missing annotations"
        assert tool.annotations.read_only_hint is True, (
            f"{name} should be readOnlyHint=True"
        )


# ---------------------------------------------------------------------------
# Portal metadata CRUD write tools
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_portal_coerces_int_organization_uuid(
    portal_session, mock_portal_client, extract_payload
):
    """mcporter CLI sends numeric IDs as int; PipefyId must coerce to str."""
    mock_portal_client.create_portal = AsyncMock(return_value=_CREATED_PORTAL)

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal",
            {"organization_uuid": int(EXAMPLE_NUMERIC_ORG_ID)},
        )

    assert result.is_error is False
    mock_portal_client.create_portal.assert_awaited_once_with(EXAMPLE_NUMERIC_ORG_ID)
    payload = extract_payload(result)
    assert payload["success"] is True


@pytest.mark.anyio
async def test_create_portal_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_portal = AsyncMock(return_value=_CREATED_PORTAL)

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal", {"organization_uuid": EXAMPLE_NUMERIC_ORG_ID}
        )

    assert result.is_error is False
    mock_portal_client.create_portal.assert_awaited_once_with(EXAMPLE_NUMERIC_ORG_ID)
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["uuid"] == "portal-created-uuid"
    assert payload["data"]["name"] == "Org Portal"


@pytest.mark.anyio
async def test_create_portal_permission_denied_returns_actionable_error(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_portal = AsyncMock(
        side_effect=ValueError(_PORTAL_PERMISSION_DENIED_MSG)
    )

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal", {"organization_uuid": "org-abc-123"}
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
async def test_update_portal_success(
    portal_session, mock_portal_client, extract_payload
):
    updated = {**_CREATED_PORTAL, "name": "Renamed Portal", "visibility": "public"}
    mock_portal_client.update_portal = AsyncMock(return_value=updated)

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal",
            {
                "portal_uuid": "portal-created-uuid",
                "name": "Renamed Portal",
                "visibility": "public",
            },
        )

    assert result.is_error is False
    mock_portal_client.update_portal.assert_awaited_once_with(
        "portal-created-uuid",
        name="Renamed Portal",
        visibility="public",
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["name"] == "Renamed Portal"
    assert payload["data"]["visibility"] == "public"


@pytest.mark.anyio
async def test_update_portal_invalid_visibility_returns_validation_envelope(
    portal_session, mock_portal_client
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal",
            {
                "portal_uuid": "portal-created-uuid",
                "visibility": "public_visibility",
            },
        )

    assert_invalid_arguments_envelope(result)
    mock_portal_client.update_portal.assert_not_called()


@pytest.mark.anyio
async def test_update_portal_rejects_when_no_fields_to_update(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal",
            {"portal_uuid": "portal-created-uuid"},
        )

    mock_portal_client.update_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "at least one" in tool_error_message(payload)


@pytest.mark.anyio
async def test_update_portal_rejects_blank_name(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal",
            {"portal_uuid": "portal-created-uuid", "name": "   "},
        )

    mock_portal_client.update_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "name" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_get_portal_rejects_empty_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool("get_portal", {"portal_uuid": "  "})

    mock_portal_client.get_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "portal_uuid" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_delete_portal_rejects_empty_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_portal",
            {"portal_uuid": "", "confirm": True},
        )

    mock_portal_client.delete_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "portal_uuid" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_update_portal_permission_denied_returns_actionable_error(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.update_portal = AsyncMock(
        side_effect=ValueError(_PORTAL_PERMISSION_DENIED_MSG)
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal",
            {
                "portal_uuid": "portal-created-uuid",
                "name": "Renamed Portal",
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
async def test_delete_portal_preview_does_not_delete(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_portal", {"portal_uuid": "portal-to-delete"}
        )

    assert result.is_error is False
    mock_portal_client.delete_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["requires_confirmation"] is True
    assert payload["resource"] == "portal (UUID: portal-to-delete)"
    assert "confirm=True" in payload["message"]


@pytest.mark.anyio
async def test_delete_portal_success(portal_session, mock_portal_client):
    mock_portal_client.delete_portal = AsyncMock(
        return_value={"deleteInterface": {"success": True}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal",
            {"portal_uuid": "portal-to-delete", "confirm": True},
        )

    mock_portal_client.delete_portal.assert_awaited_once_with("portal-to-delete")
    assert payload["success"] is True
    assert payload["data"]["deleteInterface"]["success"] is True


@pytest.mark.anyio
async def test_delete_portal_fails_when_success_false(
    portal_session, mock_portal_client
):
    mock_portal_client.delete_portal = AsyncMock(
        return_value={"deleteInterface": {"success": False}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal",
            {"portal_uuid": "portal-to-delete", "confirm": True},
        )

    mock_portal_client.delete_portal.assert_awaited_once_with("portal-to-delete")
    assert payload["success"] is False
    assert "failed to delete portal" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_delete_portal_permission_denied_returns_actionable_error(
    portal_session, mock_portal_client
):
    mock_portal_client.delete_portal = AsyncMock(
        side_effect=ValueError(_PORTAL_PERMISSION_DENIED_MSG)
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal",
            {"portal_uuid": "portal-to-delete", "confirm": True},
        )

    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
async def test_delete_portal_has_destructive_hint(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    delete_tool = tool_map["delete_portal"]
    assert delete_tool.annotations is not None
    assert delete_tool.annotations.destructive_hint is True
    assert delete_tool.annotations.read_only_hint is not True


# ---------------------------------------------------------------------------
# Portal page write tools
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_portal_page_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_portal_page = AsyncMock(return_value=_CREATED_PAGE)

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_page",
            {"portal_uuid": _PORTAL_UUID, "title": _PAGE_TITLE},
        )

    assert result.is_error is False
    mock_portal_client.create_portal_page.assert_awaited_once_with(
        _PORTAL_UUID,
        _PAGE_TITLE,
        description=None,
        index=None,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["uuid"] == _PAGE_UUID
    assert payload["data"]["title"] == _PAGE_TITLE


@pytest.mark.anyio
async def test_create_portal_page_passes_optional_fields(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_portal_page = AsyncMock(return_value=_CREATED_PAGE)

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_page",
            {
                "portal_uuid": _PORTAL_UUID,
                "title": _PAGE_TITLE,
                "description": "Landing copy",
                "index": 1,
            },
        )

    assert result.is_error is False
    mock_portal_client.create_portal_page.assert_awaited_once_with(
        _PORTAL_UUID,
        _PAGE_TITLE,
        description="Landing copy",
        index=1,
    )
    payload = extract_payload(result)
    assert payload["success"] is True


@pytest.mark.anyio
async def test_create_portal_page_permission_denied_returns_actionable_error(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_portal_page = AsyncMock(
        side_effect=ValueError(_PORTAL_PERMISSION_DENIED_MSG)
    )

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_page",
            {"portal_uuid": _PORTAL_UUID, "title": _PAGE_TITLE},
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
async def test_create_portal_page_rejects_negative_index(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_page",
            {"portal_uuid": _PORTAL_UUID, "title": _PAGE_TITLE, "index": -1},
        )

    mock_portal_client.create_portal_page.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "index" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_create_portal_page_rejects_empty_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_page",
            {"portal_uuid": "  ", "title": _PAGE_TITLE},
        )

    mock_portal_client.create_portal_page.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "portal_uuid" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_update_portal_page_success(
    portal_session, mock_portal_client, extract_payload
):
    updated_page = {**_CREATED_PAGE, "title": "Renamed Page"}
    mock_portal_client.update_portal_page = AsyncMock(return_value=updated_page)

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page",
            {
                "portal_uuid": _PORTAL_UUID,
                "page_id": _PAGE_UUID,
                "title": "Renamed Page",
            },
        )

    assert result.is_error is False
    mock_portal_client.update_portal_page.assert_awaited_once_with(
        _PORTAL_UUID,
        _PAGE_UUID,
        title="Renamed Page",
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["title"] == "Renamed Page"


@pytest.mark.anyio
async def test_update_portal_page_rejects_negative_index(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page",
            {
                "portal_uuid": _PORTAL_UUID,
                "page_id": _PAGE_UUID,
                "index": -1,
            },
        )

    mock_portal_client.update_portal_page.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "index" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_update_portal_page_rejects_when_no_fields_to_update(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page",
            {"portal_uuid": _PORTAL_UUID, "page_id": _PAGE_UUID},
        )

    mock_portal_client.update_portal_page.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "at least one" in tool_error_message(payload)


@pytest.mark.anyio
async def test_delete_portal_page_preview_does_not_delete(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_portal_page",
            {"portal_uuid": _PORTAL_UUID, "page_id": _PAGE_UUID},
        )

    assert result.is_error is False
    mock_portal_client.delete_portal_page.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["requires_confirmation"] is True
    assert _PAGE_UUID in payload["resource"]
    assert "confirm=True" in payload["message"]


@pytest.mark.anyio
async def test_delete_portal_page_success(portal_session, mock_portal_client):
    mock_portal_client.delete_portal_page = AsyncMock(
        return_value={"deletePage": {"success": True}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal_page",
            {
                "portal_uuid": _PORTAL_UUID,
                "page_id": _PAGE_UUID,
                "confirm": True,
            },
        )

    mock_portal_client.delete_portal_page.assert_awaited_once_with(
        _PORTAL_UUID, _PAGE_UUID
    )
    assert payload["success"] is True
    assert payload["data"]["deletePage"]["success"] is True


@pytest.mark.anyio
async def test_delete_portal_page_fails_when_success_false(
    portal_session, mock_portal_client
):
    mock_portal_client.delete_portal_page = AsyncMock(
        return_value={"deletePage": {"success": False}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal_page",
            {
                "portal_uuid": _PORTAL_UUID,
                "page_id": _PAGE_UUID,
                "confirm": True,
            },
        )

    assert payload["success"] is False
    assert "failed to delete" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_delete_portal_page_has_destructive_hint(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    delete_tool = tool_map["delete_portal_page"]
    assert delete_tool.annotations is not None
    assert delete_tool.annotations.destructive_hint is True
    assert delete_tool.annotations.read_only_hint is not True


@pytest.mark.anyio
async def test_sort_portal_pages_success(
    portal_session, mock_portal_client, extract_payload
):
    page_ids = [_PAGE_UUID_2, _PAGE_UUID]
    mock_portal_client.sort_portal_pages = AsyncMock(
        return_value={"sortPages": {"success": True}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "sort_portal_pages",
            {"portal_uuid": _PORTAL_UUID, "page_ids": page_ids},
        )

    assert result.is_error is False
    mock_portal_client.sort_portal_pages.assert_awaited_once_with(
        _PORTAL_UUID, page_ids
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["sortPages"]["success"] is True


@pytest.mark.anyio
async def test_sort_portal_pages_rejects_empty_page_ids(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "sort_portal_pages",
            {"portal_uuid": _PORTAL_UUID, "page_ids": []},
        )

    mock_portal_client.sort_portal_pages.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "page_ids" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_sort_portal_pages_rejects_duplicate_page_ids(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "sort_portal_pages",
            {"portal_uuid": _PORTAL_UUID, "page_ids": [_PAGE_UUID, _PAGE_UUID]},
        )

    mock_portal_client.sort_portal_pages.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "duplicate" in tool_error_message(payload).lower()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_page_ids",
    [
        ["   "],
        [True],
        [None],
        [{"id": "x"}],
    ],
)
async def test_sort_portal_pages_rejects_invalid_page_id_items(
    portal_session,
    mock_portal_client,
    extract_payload,
    invalid_page_ids,
):
    async with portal_session as session:
        result = await session.call_tool(
            "sort_portal_pages",
            {"portal_uuid": _PORTAL_UUID, "page_ids": invalid_page_ids},
        )

    mock_portal_client.sort_portal_pages.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "page_ids" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_sort_portal_pages_fails_when_success_false(
    portal_session, mock_portal_client, extract_payload
):
    page_ids = [_PAGE_UUID_2, _PAGE_UUID]
    mock_portal_client.sort_portal_pages = AsyncMock(
        return_value={"sortPages": {"success": False}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "sort_portal_pages",
            {"portal_uuid": _PORTAL_UUID, "page_ids": page_ids},
        )

    assert result.is_error is False
    mock_portal_client.sort_portal_pages.assert_awaited_once_with(
        _PORTAL_UUID, page_ids
    )
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "failed to reorder" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_update_portal_page_layout_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.update_portal_page_layout = AsyncMock(
        return_value={"updatePageLayout": {"success": True}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page_layout",
            {"page_id": _PAGE_UUID, "layout": _PAGE_LAYOUT},
        )

    assert result.is_error is False
    mock_portal_client.update_portal_page_layout.assert_awaited_once_with(
        _PAGE_UUID, parse_portal_page_layout(_PAGE_LAYOUT)
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["updatePageLayout"]["success"] is True


@pytest.mark.anyio
async def test_update_portal_page_layout_accepts_empty_array(
    portal_session, mock_portal_client
):
    mock_portal_client.update_portal_page_layout = AsyncMock(
        return_value={"updatePageLayout": {"success": True}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page_layout",
            {"page_id": _PAGE_UUID, "layout": []},
        )

    assert result.is_error is False
    mock_portal_client.update_portal_page_layout.assert_awaited_once_with(
        _PAGE_UUID, []
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "layout",
    [
        [{}],
        [{"children": ["el-new"]}],
        [{"id": "row-1", "type": "column", "children": ["el-new"]}],
    ],
)
async def test_update_portal_page_layout_rejects_malformed_rows(
    portal_session, mock_portal_client, extract_payload, layout
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page_layout",
            {"page_id": _PAGE_UUID, "layout": layout},
        )

    mock_portal_client.update_portal_page_layout.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "type 'row'" in tool_error_message(payload)


@pytest.mark.anyio
async def test_update_portal_page_layout_fails_when_success_false(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.update_portal_page_layout = AsyncMock(
        return_value={"updatePageLayout": {"success": False}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page_layout",
            {"page_id": _PAGE_UUID, "layout": _PAGE_LAYOUT},
        )

    assert result.is_error is False
    mock_portal_client.update_portal_page_layout.assert_awaited_once_with(
        _PAGE_UUID, parse_portal_page_layout(_PAGE_LAYOUT)
    )
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "failed to update layout" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_update_portal_page_layout_permission_denied_returns_actionable_error(
    portal_session, mock_portal_client, extract_payload
):
    exc = PipefyGraphQLError([{"message": "forbidden"}])
    exc.errors = [{"extensions": {"code": "PERMISSION_DENIED"}}]
    mock_portal_client.update_portal_page_layout = AsyncMock(side_effect=exc)

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page_layout",
            {"page_id": _PAGE_UUID, "layout": _PAGE_LAYOUT},
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
async def test_update_portal_page_layout_transport_error_returns_envelope(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.update_portal_page_layout = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "timeout"}])
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page_layout",
            {"page_id": _PAGE_UUID, "layout": _PAGE_LAYOUT},
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    err = payload.get("error")
    assert isinstance(err, dict) and "message" in err


@pytest.mark.anyio
async def test_page_write_tools_are_not_readonly(portal_session):
    write_tool_names = [
        "create_portal_page",
        "update_portal_page",
        "delete_portal_page",
        "sort_portal_pages",
        "update_portal_page_layout",
    ]

    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    for name in write_tool_names:
        tool = tool_map[name]
        assert tool.annotations is not None, f"{name} missing annotations"
        assert tool.annotations.read_only_hint is not True, (
            f"{name} should not be readOnlyHint=True"
        )


# ---------------------------------------------------------------------------
# Portal element write tools
# ---------------------------------------------------------------------------

_ELEMENT_WRITE_TOOL_NAMES = [
    "create_portal_element",
    "update_portal_element",
    "delete_portal_element",
    "duplicate_portal_element",
]


@pytest.mark.anyio
async def test_create_portal_element_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_portal_element = AsyncMock(return_value=_CREATED_ELEMENT)

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_element",
            {
                "page_id": _PAGE_UUID,
                "type": "forms",
                "metadata": _FORMS_METADATA,
                "data_sources": _FORMS_DATA_SOURCES,
            },
        )

    assert result.is_error is False
    mock_portal_client.create_portal_element.assert_awaited_once_with(
        _PAGE_UUID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=_FORMS_DATA_SOURCES,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["uuid"] == _ELEMENT_UUID
    assert payload["data"]["type"] == "forms"


_PLACING_LINK_METADATA = {"linkName": "Docs", "linkUrl": "https://example.com"}
_PLACING_LAYOUT = [
    {"id": "row-1", "type": "row", "children": ["el-1"]},
    {"id": "row-2", "type": "row", "children": ["el-new"]},
]


@pytest.mark.anyio
async def test_create_portal_element_with_layout_places_element(
    portal_session, mock_portal_client
):
    mock_portal_client.create_portal_element = AsyncMock(return_value=_CREATED_ELEMENT)

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_element",
            {
                "page_id": _PAGE_UUID,
                "type": "link",
                "metadata": _PLACING_LINK_METADATA,
                "element_id": "el-new",
                "layout": _PLACING_LAYOUT,
            },
        )

    assert result.is_error is False
    mock_portal_client.create_portal_element.assert_awaited_once_with(
        _PAGE_UUID,
        type="link",
        metadata=_PLACING_LINK_METADATA,
        data_sources=[],
        element_id="el-new",
        layout=parse_portal_page_layout(_PLACING_LAYOUT),
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"element_id": "el-new", "layout": {"rows": _PLACING_LAYOUT}},
        {"layout": _PLACING_LAYOUT},
        {"element_id": "el-elsewhere", "layout": _PLACING_LAYOUT},
        {"element_id": "el-new", "layout": [{"children": ["el-new"]}]},
    ],
    ids=[
        "object-wrapper",
        "missing-element-id",
        "element-not-in-rows",
        "incomplete-row",
    ],
)
async def test_create_portal_element_rejects_unplaceable_layout_before_client(
    portal_session, mock_portal_client, extract_payload, arguments
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_element",
            {
                "page_id": _PAGE_UUID,
                "type": "link",
                "metadata": _PLACING_LINK_METADATA,
                **arguments,
            },
        )

    mock_portal_client.create_portal_element.assert_not_called()
    assert extract_payload(result)["success"] is False


@pytest.mark.anyio
async def test_create_portal_element_rejects_invalid_metadata_before_client(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_element",
            {
                "page_id": _PAGE_UUID,
                "type": "forms",
                "metadata": {},
            },
        )

    mock_portal_client.create_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    message = tool_error_message(payload).lower()
    assert "name" in message


@pytest.mark.anyio
async def test_create_portal_element_rejects_unknown_type_before_client(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_element",
            {
                "page_id": _PAGE_UUID,
                "type": "not_a_portal_element_type",
                "metadata": {},
            },
        )

    mock_portal_client.create_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"


@pytest.mark.anyio
async def test_create_portal_element_rejects_blank_page_id(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_element",
            {
                "page_id": "  ",
                "type": "forms",
                "metadata": _FORMS_METADATA,
            },
        )

    mock_portal_client.create_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "page_id" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_create_portal_element_permission_denied_returns_actionable_error(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_portal_element = AsyncMock(
        side_effect=ValueError(_PORTAL_PERMISSION_DENIED_MSG)
    )

    async with portal_session as session:
        result = await session.call_tool(
            "create_portal_element",
            {
                "page_id": _PAGE_UUID,
                "type": "forms",
                "metadata": _FORMS_METADATA,
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
async def test_create_portal_element_docstring_mentions_portal_tool_in_ui(
    portal_session,
):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    create_tool = tool_map["create_portal_element"]
    description = (create_tool.description or "").lower()
    assert "tool" in description or "widget" in description


@pytest.mark.anyio
async def test_update_portal_element_success(
    portal_session, mock_portal_client, extract_payload
):
    link_metadata = {
        "linkUrl": "https://example.com/pipefy",
        "linkName": "Open",
    }
    updated_element = {
        **_CREATED_ELEMENT,
        "type": "link",
        "metadata": link_metadata,
    }
    mock_portal_client.update_portal_element = AsyncMock(return_value=updated_element)

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "type": "link",
                "metadata": link_metadata,
                "data_sources": [],
            },
        )

    assert result.is_error is False
    mock_portal_client.update_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID,
        _PAGE_UUID,
        type="link",
        metadata=link_metadata,
        data_sources=[],
        portal_uuid=None,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["metadata"]["linkUrl"] == "https://example.com/pipefy"


@pytest.mark.anyio
async def test_update_portal_element_keeps_data_sources_with_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    """Omitted data_sources reach the SDK as None, with the portal to read them from."""
    mock_portal_client.update_portal_element = AsyncMock(
        return_value={**_CREATED_ELEMENT, "metadata": _FORMS_METADATA}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "type": "forms",
                "metadata": _FORMS_METADATA,
                "portal_uuid": f" {_PORTAL_UUID} ",
            },
        )

    assert extract_payload(result)["success"] is True
    mock_portal_client.update_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID,
        _PAGE_UUID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=None,
        portal_uuid=_PORTAL_UUID,
    )


@pytest.mark.anyio
async def test_update_portal_element_rejects_missing_data_sources_and_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    """Without data_sources or portal_uuid, the call is rejected before any request."""
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "type": "forms",
                "metadata": _FORMS_METADATA,
            },
        )

    mock_portal_client.update_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "portal_uuid" in tool_error_message(payload)


@pytest.mark.anyio
async def test_update_portal_element_rejects_blank_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "type": "forms",
                "metadata": _FORMS_METADATA,
                "portal_uuid": "   ",
            },
        )

    mock_portal_client.update_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "portal_uuid" in tool_error_message(payload)


@pytest.mark.anyio
async def test_update_portal_element_reports_element_not_on_page(
    portal_session, mock_portal_client, extract_payload
):
    """The SDK's keep-path lookup error reaches the agent as is."""
    message = (
        f"Element '{_ELEMENT_UUID}' is on no page of portal '{_PORTAL_UUID}'. "
        "Check portal_uuid and element_id, or pass data_sources to skip the read."
    )
    mock_portal_client.update_portal_element = AsyncMock(
        side_effect=ValueError(message)
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "type": "forms",
                "metadata": _FORMS_METADATA,
                "portal_uuid": _PORTAL_UUID,
            },
        )

    payload = extract_payload(result)
    assert payload["success"] is False
    assert tool_error_message(payload) == message


@pytest.mark.anyio
async def test_update_portal_element_rejects_invalid_metadata_before_client(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "type": "link",
                "metadata": {},
            },
        )

    mock_portal_client.update_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "linkname" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_delete_portal_element_preview_does_not_delete(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_portal_element",
            {"element_id": _ELEMENT_UUID, "page_id": _PAGE_UUID},
        )

    assert result.is_error is False
    mock_portal_client.delete_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["requires_confirmation"] is True
    assert _ELEMENT_UUID in payload["resource"]
    assert "confirm=True" in payload["message"]


@pytest.mark.anyio
async def test_delete_portal_element_success(portal_session, mock_portal_client):
    mock_portal_client.delete_portal_element = AsyncMock(
        return_value={"deleteElement": {"success": True}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "confirm": True,
            },
        )

    mock_portal_client.delete_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID, _PAGE_UUID
    )
    assert payload["success"] is True
    assert payload["data"]["deleteElement"]["success"] is True


@pytest.mark.anyio
async def test_delete_portal_element_fails_when_success_false(
    portal_session, mock_portal_client
):
    mock_portal_client.delete_portal_element = AsyncMock(
        return_value={"deleteElement": {"success": False}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "confirm": True,
            },
        )

    assert payload["success"] is False
    assert "failed to delete" in tool_error_message(payload).lower()


_PRUNED_LAYOUT = [{"id": "row-1", "type": "row", "children": ["el-1"]}]


@pytest.mark.anyio
async def test_delete_portal_element_forwards_pruned_layout(
    portal_session, mock_portal_client
):
    mock_portal_client.delete_portal_element = AsyncMock(
        return_value={"deleteElement": {"success": True}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "layout": _PRUNED_LAYOUT,
                "confirm": True,
            },
        )

    assert payload["success"] is True
    mock_portal_client.delete_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID, _PAGE_UUID, layout=parse_portal_page_layout(_PRUNED_LAYOUT)
    )


@pytest.mark.anyio
async def test_delete_portal_element_preview_names_the_layout_rewrite(
    portal_session, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_portal_element",
            {"element_id": _ELEMENT_UUID, "page_id": _PAGE_UUID, "layout": []},
        )

    payload = extract_payload(result)
    assert payload["requires_confirmation"] is True
    assert "replacing that page's layout" in payload["resource"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "layout",
    [
        [{"id": "row-1", "type": "row", "children": [_ELEMENT_UUID]}],
        [{"children": []}],
    ],
    ids=["still-lists-element", "incomplete-row"],
)
async def test_delete_portal_element_rejects_bad_layout_before_preview(
    portal_session, extract_payload, layout
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_portal_element",
            {"element_id": _ELEMENT_UUID, "page_id": _PAGE_UUID, "layout": layout},
        )

    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    assert "confirmation_token" not in payload


@pytest.mark.anyio
async def test_delete_portal_element_token_without_layout_does_not_confirm_layout(
    portal_session, mock_portal_client, extract_payload
):
    """A token minted without layout must not confirm a delete that rewrites the grid."""
    async with portal_session as session:
        preview = extract_payload(
            await session.call_tool(
                "delete_portal_element",
                {"element_id": _ELEMENT_UUID, "page_id": _PAGE_UUID},
            )
        )
        result = await session.call_tool(
            "delete_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "page_id": _PAGE_UUID,
                "layout": _PRUNED_LAYOUT,
                "confirm": True,
                "confirmation_token": preview["confirmation_token"],
            },
        )

    payload = extract_payload(result)
    assert payload["requires_confirmation"] is True
    assert "does not match" in payload["message"]
    mock_portal_client.delete_portal_element.assert_not_called()


@pytest.mark.anyio
async def test_delete_portal_element_has_destructive_hint(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    delete_tool = tool_map["delete_portal_element"]
    assert delete_tool.annotations is not None
    assert delete_tool.annotations.destructive_hint is True
    assert delete_tool.annotations.read_only_hint is not True


@pytest.mark.anyio
async def test_duplicate_portal_element_success(
    portal_session, mock_portal_client, extract_payload
):
    duplicated = {
        "id": "el-copy",
        "uuid": "el-copy",
        "type": "text",
        "metadata": {},
    }
    mock_portal_client.duplicate_portal_element = AsyncMock(return_value=duplicated)

    async with portal_session as session:
        result = await session.call_tool(
            "duplicate_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "portal_uuid": _PORTAL_UUID,
                "page_id": _PAGE_UUID,
            },
        )

    assert result.is_error is False
    mock_portal_client.duplicate_portal_element.assert_awaited_once_with(
        element_id=_ELEMENT_UUID,
        portal_uuid=_PORTAL_UUID,
        page_id=_PAGE_UUID,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["uuid"] == "el-copy"


@pytest.mark.anyio
async def test_duplicate_portal_element_rejects_blank_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "duplicate_portal_element",
            {
                "element_id": _ELEMENT_UUID,
                "portal_uuid": "  ",
                "page_id": _PAGE_UUID,
            },
        )

    mock_portal_client.duplicate_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "portal_uuid" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_element_write_tools_are_not_readonly(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    for name in _ELEMENT_WRITE_TOOL_NAMES:
        tool = tool_map[name]
        assert tool.annotations is not None, f"{name} missing annotations"
        assert tool.annotations.read_only_hint is not True, (
            f"{name} should not be readOnlyHint=True"
        )


# ---------------------------------------------------------------------------
# Sub-portal write tools (task 6.3 RED — tools registered in 6.4)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_sub_portal_success(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.create_sub_portal = AsyncMock(return_value=_CREATED_SUB_PORTAL)

    async with portal_session as session:
        result = await session.call_tool(
            "create_sub_portal",
            {
                "main_portal_uuid": _MAIN_PORTAL_UUID,
                "name": _SUB_PORTAL_NAME,
            },
        )

    assert result.is_error is False
    mock_portal_client.create_sub_portal.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _SUB_PORTAL_NAME,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["uuid"] == _SUB_PORTAL_UUID
    assert payload["data"]["name"] == _SUB_PORTAL_NAME


@pytest.mark.anyio
async def test_create_sub_portal_rejects_blank_main_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "create_sub_portal",
            {"main_portal_uuid": "  ", "name": _SUB_PORTAL_NAME},
        )

    mock_portal_client.create_sub_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "main_portal_uuid" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_create_sub_portal_transport_error_not_permission_envelope(
    portal_session, mock_portal_client, extract_payload
):
    # A genuine transport failure (timeout/network), not a GraphQL error envelope:
    # its message must surface verbatim and must not be mistaken for a permission denial.
    mock_portal_client.create_sub_portal = AsyncMock(
        side_effect=TransportError("timeout")
    )

    async with portal_session as session:
        result = await session.call_tool(
            "create_sub_portal",
            {"main_portal_uuid": _MAIN_PORTAL_UUID},
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "timeout" in message
    assert "manage_portals" not in message


@pytest.mark.anyio
async def test_update_sub_portal_element_success(
    portal_session, mock_portal_client, extract_payload
):
    mutation_result = {"updateSubPortalElement": {"success": True}}
    mock_portal_client.update_sub_portal_element = AsyncMock(
        return_value=mutation_result
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_sub_portal_element",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "sub_portal_uuid": _SUB_PORTAL_UUID,
            },
        )

    assert result.is_error is False
    mock_portal_client.update_sub_portal_element.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
        _SUB_PORTAL_UUID,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["updateSubPortalElement"]["success"] is True


@pytest.mark.anyio
async def test_update_sub_portal_element_rejects_blank_sub_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_sub_portal_element",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "sub_portal_uuid": "  ",
            },
        )

    mock_portal_client.update_sub_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "sub_portal_uuid" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_update_sub_portal_element_fails_when_success_false(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.update_sub_portal_element = AsyncMock(
        return_value={"updateSubPortalElement": {"success": False}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "update_sub_portal_element",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "sub_portal_uuid": _SUB_PORTAL_UUID,
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "failed" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_publish_sub_portal_success(
    portal_session, mock_portal_client, extract_payload
):
    mutation_result = {"updateSubPortalElement": {"success": True}}
    mock_portal_client.publish_sub_portal = AsyncMock(return_value=mutation_result)

    async with portal_session as session:
        result = await session.call_tool(
            "publish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "sub_portal_uuid": _SUB_PORTAL_UUID,
            },
        )

    assert result.is_error is False
    mock_portal_client.publish_sub_portal.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
        _SUB_PORTAL_UUID,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["updateSubPortalElement"]["success"] is True


@pytest.mark.anyio
async def test_publish_sub_portal_rejects_blank_element_id(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "publish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": "  ",
                "sub_portal_uuid": _SUB_PORTAL_UUID,
            },
        )

    mock_portal_client.publish_sub_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "element_id" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_publish_sub_portal_fails_when_success_false(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.publish_sub_portal = AsyncMock(
        return_value={"updateSubPortalElement": {"success": False}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "publish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "sub_portal_uuid": _SUB_PORTAL_UUID,
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "failed" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_publish_sub_portal_permission_denied_returns_actionable_error(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.publish_sub_portal = AsyncMock(
        side_effect=PortalPermissionError(_PORTAL_PERMISSION_DENIED_MSG)
    )

    async with portal_session as session:
        result = await session.call_tool(
            "publish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "sub_portal_uuid": _SUB_PORTAL_UUID,
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool_name", "client_method", "tool_args"),
    [
        (
            "publish_sub_portal",
            "publish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "sub_portal_uuid": _SUB_PORTAL_UUID,
            },
        ),
        (
            "unpublish_sub_portal",
            "unpublish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
            },
        ),
        (
            "delete_sub_portal_element",
            "delete_sub_portal_element",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "confirm": True,
            },
        ),
        (
            "delete_sub_portal",
            "delete_sub_portal",
            {"sub_portal_uuid": _SUB_PORTAL_UUID, "confirm": True},
        ),
    ],
)
async def test_sub_portal_internal_api_permission_denied_returns_actionable_error(
    portal_session,
    mock_portal_client,
    extract_payload,
    tool_name: str,
    client_method: str,
    tool_args: dict[str, object],
):
    setattr(
        mock_portal_client,
        client_method,
        AsyncMock(side_effect=_INTERNAL_API_PERMISSION_DENIED_ERROR),
    )

    async with portal_session as session:
        if tool_args.get("confirm"):
            payload = await confirm_after_preview(session, tool_name, tool_args)
        else:
            result = await session.call_tool(tool_name, tool_args)
            assert result.is_error is False
            payload = extract_payload(result)

    assert payload["success"] is False
    message = tool_error_message(payload).lower()
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.anyio
async def test_unpublish_sub_portal_success(
    portal_session, mock_portal_client, extract_payload
):
    mutation_result = {"updateSubPortalElement": {"success": True}}
    mock_portal_client.unpublish_sub_portal = AsyncMock(return_value=mutation_result)

    async with portal_session as session:
        result = await session.call_tool(
            "unpublish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
            },
        )

    assert result.is_error is False
    mock_portal_client.unpublish_sub_portal.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"]["updateSubPortalElement"]["success"] is True


@pytest.mark.anyio
async def test_unpublish_sub_portal_rejects_blank_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "unpublish_sub_portal",
            {
                "portal_uuid": "  ",
                "element_id": _FORMS_ELEMENT_ID,
            },
        )

    mock_portal_client.unpublish_sub_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "portal_uuid" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_unpublish_sub_portal_fails_when_success_false(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.unpublish_sub_portal = AsyncMock(
        return_value={"updateSubPortalElement": {"success": False}}
    )

    async with portal_session as session:
        result = await session.call_tool(
            "unpublish_sub_portal",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "failed" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_delete_sub_portal_element_preview_does_not_delete(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_sub_portal_element",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
            },
        )

    assert result.is_error is False
    mock_portal_client.delete_sub_portal_element.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["requires_confirmation"] is True
    assert _FORMS_ELEMENT_ID in payload["resource"]
    assert "confirm=True" in payload["message"]


@pytest.mark.anyio
async def test_delete_sub_portal_element_success(portal_session, mock_portal_client):
    mock_portal_client.delete_sub_portal_element = AsyncMock(
        return_value={"deleteSubPortalElement": {"success": True}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_sub_portal_element",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "confirm": True,
            },
        )

    mock_portal_client.delete_sub_portal_element.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
    )
    assert payload["success"] is True
    assert payload["data"]["deleteSubPortalElement"]["success"] is True


@pytest.mark.anyio
async def test_delete_sub_portal_element_fails_when_success_false(
    portal_session, mock_portal_client
):
    mock_portal_client.delete_sub_portal_element = AsyncMock(
        return_value={"deleteSubPortalElement": {"success": False}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_sub_portal_element",
            {
                "portal_uuid": _MAIN_PORTAL_UUID,
                "element_id": _FORMS_ELEMENT_ID,
                "confirm": True,
            },
        )

    assert payload["success"] is False
    assert "failed" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_delete_sub_portal_element_has_destructive_hint(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    delete_tool = tool_map["delete_sub_portal_element"]
    assert delete_tool.annotations is not None
    assert delete_tool.annotations.destructive_hint is True
    assert delete_tool.annotations.read_only_hint is not True


@pytest.mark.anyio
async def test_delete_sub_portal_preview_does_not_delete(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_sub_portal",
            {"sub_portal_uuid": _SUB_PORTAL_UUID},
        )

    assert result.is_error is False
    mock_portal_client.delete_sub_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["requires_confirmation"] is True
    assert _SUB_PORTAL_UUID in payload["resource"]
    assert "confirm=True" in payload["message"]


@pytest.mark.anyio
async def test_delete_sub_portal_success(portal_session, mock_portal_client):
    mock_portal_client.delete_sub_portal = AsyncMock(
        return_value={"deleteSubPortalInterface": {"success": True}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_sub_portal",
            {"sub_portal_uuid": _SUB_PORTAL_UUID, "confirm": True},
        )

    mock_portal_client.delete_sub_portal.assert_awaited_once_with(_SUB_PORTAL_UUID)
    assert payload["success"] is True
    assert payload["data"]["deleteSubPortalInterface"]["success"] is True


@pytest.mark.anyio
async def test_delete_sub_portal_fails_when_success_false(
    portal_session, mock_portal_client
):
    mock_portal_client.delete_sub_portal = AsyncMock(
        return_value={"deleteSubPortalInterface": {"success": False}}
    )

    async with portal_session as session:
        payload = await confirm_after_preview(
            session,
            "delete_sub_portal",
            {"sub_portal_uuid": _SUB_PORTAL_UUID, "confirm": True},
        )

    assert payload["success"] is False
    assert "failed" in tool_error_message(payload).lower()


@pytest.mark.anyio
async def test_delete_sub_portal_rejects_blank_sub_portal_uuid(
    portal_session, mock_portal_client, extract_payload
):
    async with portal_session as session:
        result = await session.call_tool(
            "delete_sub_portal",
            {"sub_portal_uuid": "  ", "confirm": True},
        )

    mock_portal_client.delete_sub_portal.assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    assert "sub_portal_uuid" in tool_error_message(payload).lower()


_INVALID_SUB_PORTAL_ID_VALUES = ["", "   ", True, False]

_SUB_PORTAL_PORTAL_UUID_CASES = [
    (
        "create_sub_portal",
        "main_portal_uuid",
        {"name": _SUB_PORTAL_NAME},
        "create_sub_portal",
    ),
    (
        "update_sub_portal_element",
        "portal_uuid",
        {
            "element_id": _FORMS_ELEMENT_ID,
            "sub_portal_uuid": _SUB_PORTAL_UUID,
        },
        "update_sub_portal_element",
    ),
    (
        "publish_sub_portal",
        "portal_uuid",
        {
            "element_id": _FORMS_ELEMENT_ID,
            "sub_portal_uuid": _SUB_PORTAL_UUID,
        },
        "publish_sub_portal",
    ),
    (
        "unpublish_sub_portal",
        "portal_uuid",
        {"element_id": _FORMS_ELEMENT_ID},
        "unpublish_sub_portal",
    ),
    (
        "delete_sub_portal_element",
        "portal_uuid",
        {"element_id": _FORMS_ELEMENT_ID, "confirm": True},
        "delete_sub_portal_element",
    ),
]

_SUB_PORTAL_ELEMENT_OR_SUB_UUID_CASES = [
    (
        "update_sub_portal_element",
        "element_id",
        {
            "portal_uuid": _MAIN_PORTAL_UUID,
            "sub_portal_uuid": _SUB_PORTAL_UUID,
        },
        "update_sub_portal_element",
    ),
    (
        "update_sub_portal_element",
        "sub_portal_uuid",
        {
            "portal_uuid": _MAIN_PORTAL_UUID,
            "element_id": _FORMS_ELEMENT_ID,
        },
        "update_sub_portal_element",
    ),
    (
        "publish_sub_portal",
        "element_id",
        {
            "portal_uuid": _MAIN_PORTAL_UUID,
            "sub_portal_uuid": _SUB_PORTAL_UUID,
        },
        "publish_sub_portal",
    ),
    (
        "publish_sub_portal",
        "sub_portal_uuid",
        {
            "portal_uuid": _MAIN_PORTAL_UUID,
            "element_id": _FORMS_ELEMENT_ID,
        },
        "publish_sub_portal",
    ),
    (
        "unpublish_sub_portal",
        "element_id",
        {"portal_uuid": _MAIN_PORTAL_UUID},
        "unpublish_sub_portal",
    ),
    (
        "delete_sub_portal_element",
        "element_id",
        {"portal_uuid": _MAIN_PORTAL_UUID, "confirm": True},
        "delete_sub_portal_element",
    ),
    (
        "delete_sub_portal",
        "sub_portal_uuid",
        {"confirm": True},
        "delete_sub_portal",
    ),
]


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_id", _INVALID_SUB_PORTAL_ID_VALUES)
@pytest.mark.parametrize(
    ("tool_name", "id_field", "base_args", "client_method"),
    _SUB_PORTAL_PORTAL_UUID_CASES,
    ids=[case[0] for case in _SUB_PORTAL_PORTAL_UUID_CASES],
)
async def test_sub_portal_write_tools_reject_invalid_portal_uuid(
    portal_session,
    mock_portal_client,
    extract_payload,
    invalid_id: object,
    tool_name: str,
    id_field: str,
    base_args: dict[str, object],
    client_method: str,
):
    tool_args = {**base_args, id_field: invalid_id}

    async with portal_session as session:
        result = await session.call_tool(tool_name, tool_args)

    getattr(mock_portal_client, client_method).assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    if isinstance(invalid_id, bool):
        assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    else:
        assert tool_error_message(payload)


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_id", _INVALID_SUB_PORTAL_ID_VALUES)
@pytest.mark.parametrize(
    ("tool_name", "id_field", "base_args", "client_method"),
    _SUB_PORTAL_ELEMENT_OR_SUB_UUID_CASES,
    ids=[f"{case[0]}-{case[1]}" for case in _SUB_PORTAL_ELEMENT_OR_SUB_UUID_CASES],
)
async def test_sub_portal_write_tools_reject_invalid_element_or_sub_portal_id(
    portal_session,
    mock_portal_client,
    extract_payload,
    invalid_id: object,
    tool_name: str,
    id_field: str,
    base_args: dict[str, object],
    client_method: str,
):
    tool_args = {**base_args, id_field: invalid_id}

    async with portal_session as session:
        result = await session.call_tool(tool_name, tool_args)

    getattr(mock_portal_client, client_method).assert_not_called()
    payload = extract_payload(result)
    assert payload["success"] is False
    if isinstance(invalid_id, bool):
        assert payload["error"]["code"] == "INVALID_ARGUMENTS"
    else:
        assert tool_error_message(payload)


@pytest.mark.anyio
async def test_delete_sub_portal_has_destructive_hint(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    delete_tool = tool_map["delete_sub_portal"]
    assert delete_tool.annotations is not None
    assert delete_tool.annotations.destructive_hint is True
    assert delete_tool.annotations.read_only_hint is not True


@pytest.mark.anyio
async def test_sub_portal_write_tools_are_not_readonly(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    for name in _SUB_PORTAL_WRITE_TOOL_NAMES:
        tool = tool_map[name]
        assert tool.annotations is not None, f"{name} missing annotations"
        assert tool.annotations.read_only_hint is not True, (
            f"{name} should not be readOnlyHint=True"
        )


@pytest.mark.anyio
async def test_create_sub_portal_docstring_mentions_publish_semantics(
    portal_session,
):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    description = (tool_map["create_sub_portal"].description or "").lower()
    assert "published" in description
    assert "update_portal" in description or "visibility" in description


@pytest.mark.anyio
async def test_update_sub_portal_element_docstring_mentions_publish_semantics(
    portal_session,
):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    description = (tool_map["update_sub_portal_element"].description or "").lower()
    assert "published" in description or "update_portal" in description


@pytest.mark.anyio
async def test_publish_sub_portal_docstring_mentions_subportals_published(
    portal_session,
):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    description = (tool_map["publish_sub_portal"].description or "").lower()
    assert "subportals" in description or "sub portals" in description
    assert "get_portal" in description
    assert "createelement" not in description.replace(" ", "")


@pytest.mark.anyio
async def test_unpublish_sub_portal_docstring_mentions_subportals_published(
    portal_session,
):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    description = (tool_map["unpublish_sub_portal"].description or "").lower()
    assert "subportals" in description or "sub portals" in description
    assert "get_portal" in description


@pytest.mark.anyio
async def test_delete_sub_portal_docstring_warns_irreversible(portal_session):
    async with portal_session as session:
        listed = await session.list_tools()

    tool_map = {t.name: t for t in listed.tools}
    description = (tool_map["delete_sub_portal"].description or "").lower()
    assert "irreversible" in description


@pytest.mark.anyio
@pytest.mark.parametrize("layout", [{"rows": []}, "not-json", ["element-1"]])
async def test_page_layout_rejects_non_row_arrays(
    portal_session, mock_portal_client, extract_payload, layout
):
    async with portal_session as session:
        result = await session.call_tool(
            "update_portal_page_layout", {"page_id": _PAGE_UUID, "layout": layout}
        )
    assert extract_payload(result)["success"] is False
    mock_portal_client.update_portal_page_layout.assert_not_called()


_REPO_NODE = {
    "id": EXAMPLE_PIPE_REPO_ID,
    "uuid": "repo-uuid-1",
    "suid": "Ab12Cd34",
    "name": "Purchase requests",
    "type": "Pipe",
    "icon": "cart",
    "color": "blue",
    "noun": "Request",
}


@pytest.mark.anyio
async def test_list_interface_repos_returns_repos_for_the_numeric_org_id(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.list_interface_repos = AsyncMock(return_value=[_REPO_NODE])

    async with portal_session as session:
        result = await session.call_tool(
            "list_interface_repos",
            {
                "organization_id": int(EXAMPLE_NUMERIC_ORG_ID),
                "interface_uuid": "html-uuid-1",
                "repo_name": " purchase ",
            },
        )

    mock_portal_client.list_interface_repos.assert_awaited_once_with(
        EXAMPLE_NUMERIC_ORG_ID, interface_uuid="html-uuid-1", repo_name="purchase"
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"] == {"repos": [_REPO_NODE]}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (
            {"organization_id": "00000000-0000-4000-8000-000000000001"},
            "numeric organization id",
        ),
        (
            {"organization_id": EXAMPLE_NUMERIC_ORG_ID, "repo_name": " "},
            "repo_name",
        ),
    ],
    ids=["org uuid", "blank repo_name"],
)
async def test_list_interface_repos_rejects_bad_arguments_before_any_call(
    portal_session, mock_portal_client, arguments, message
):
    async with portal_session as session:
        result = await session.call_tool("list_interface_repos", arguments)

    payload = assert_invalid_arguments_envelope(result)
    assert message in payload["error"]["message"]
    mock_portal_client.list_interface_repos.assert_not_awaited()


_SET_SOURCES_ARGS_BASE = {
    "interface_uuid": "html-uuid-1",
    "page_id": "page-uuid-1",
    "element_id": "el-uuid-1",
    "data_sources": [],
}

_NOT_FOUND_ERROR = PipefyGraphQLError(
    [{"message": "Record not found", "extensions": {"code": "RECORD_NOT_FOUND"}}]
)


@pytest.mark.anyio
@pytest.mark.parametrize("interface_uuid", [None, "html-uuid-1"])
async def test_list_interface_repos_names_only_the_org_on_not_found(
    portal_session, mock_portal_client, extract_payload, interface_uuid
):
    """An unknown interface is not an error for the listing, so it is never named."""
    mock_portal_client.list_interface_repos = AsyncMock(side_effect=_NOT_FOUND_ERROR)

    async with portal_session as session:
        result = await session.call_tool(
            "list_interface_repos",
            {
                "organization_id": EXAMPLE_NUMERIC_ORG_ID,
                "interface_uuid": interface_uuid,
            },
        )

    assert extract_payload(result)["error"]["message"] == (
        f"No organization has id '{EXAMPLE_NUMERIC_ORG_ID}'."
    )


_REPO_FIELD = {
    "id": "900000101",
    "uuid": "6a850d1c-0000-4000-8000-000000000016",
    "label": "Amount",
    "type": "currency",
    "phaseId": "900000201",
    "archived": False,
    "required": True,
    "options": None,
    "description": None,
    "helpText": None,
    "connectedRepoId": None,
}


@pytest.mark.anyio
async def test_get_interface_repo_fields_returns_the_fields(
    portal_session, mock_portal_client, extract_payload
):
    mock_portal_client.get_interface_repo_fields = AsyncMock(return_value=[_REPO_FIELD])

    async with portal_session as session:
        result = await session.call_tool(
            "get_interface_repo_fields",
            {"repo_uuid": "repo-uuid-1", "interface_uuid": "html-uuid-1"},
        )

    mock_portal_client.get_interface_repo_fields.assert_awaited_once_with(
        "repo-uuid-1", interface_uuid="html-uuid-1"
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"] == {"fields": [_REPO_FIELD]}


def _blank_id_message(name: str) -> str:
    return f"Invalid '{name}': provide a non-empty string or positive integer."


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool", "arguments", "blank"),
    [
        (
            "list_interface_repos",
            {"organization_id": EXAMPLE_NUMERIC_ORG_ID, "interface_uuid": " "},
            "interface_uuid",
        ),
        ("get_interface_repo_fields", {"repo_uuid": " "}, "repo_uuid"),
        (
            "get_interface_repo_fields",
            {"repo_uuid": "repo-uuid-1", "interface_uuid": " "},
            "interface_uuid",
        ),
        (
            "set_interface_sources",
            {**_SET_SOURCES_ARGS_BASE, "interface_uuid": " "},
            "interface_uuid",
        ),
        (
            "set_interface_sources",
            {**_SET_SOURCES_ARGS_BASE, "page_id": " "},
            "page_id",
        ),
        (
            "set_interface_sources",
            {**_SET_SOURCES_ARGS_BASE, "element_id": " "},
            "element_id",
        ),
    ],
    ids=[
        "repos interface_uuid",
        "fields repo_uuid",
        "fields interface_uuid",
        "sources interface_uuid",
        "sources page_id",
        "sources element_id",
    ],
)
async def test_interface_source_tools_reject_blank_ids_before_any_call(
    portal_session, mock_portal_client, extract_payload, tool, arguments, blank
):
    async with portal_session as session:
        result = await session.call_tool(tool, arguments)

    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["message"] == _blank_id_message(blank)
    getattr(mock_portal_client, tool).assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "interface_uuid", "message"),
    [
        (
            _NOT_FOUND_ERROR,
            None,
            "No repo has uuid 'repo-uuid-1'. list_interface_repos lists the repos "
            "an interface can read.",
        ),
        (
            PipefyGraphQLError(
                [{"message": "Missing", "extensions": {"code": "RESOURCE_NOT_FOUND"}}]
            ),
            "html-uuid-1",
            "No repo has uuid 'repo-uuid-1', or no interface has uuid "
            "'html-uuid-1'. list_interface_repos lists the repos an interface "
            "can read.",
        ),
        (
            PipefyGraphQLError([{"message": "Couldn't find the interface"}]),
            "html-uuid-1",
            "No repo has uuid 'repo-uuid-1', or no interface has uuid "
            "'html-uuid-1'. list_interface_repos lists the repos an interface "
            "can read.",
        ),
    ],
    ids=["record not found", "resource not found", "uncoded not found"],
)
async def test_get_interface_repo_fields_names_the_ids_on_not_found(
    portal_session, mock_portal_client, extract_payload, error, interface_uuid, message
):
    mock_portal_client.get_interface_repo_fields = AsyncMock(side_effect=error)

    async with portal_session as session:
        result = await session.call_tool(
            "get_interface_repo_fields",
            {"repo_uuid": "repo-uuid-1", "interface_uuid": interface_uuid},
        )

    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["message"] == message


_SOURCES = [
    {
        "id": "open-requests",
        "name": "Open requests",
        "repoId": "repo-uuid-1",
        "fieldKeys": ["title", "6a850d1c-0000-4000-8000-000000000016"],
        "filters": None,
    }
]

_SET_SOURCES_ARGS = {**_SET_SOURCES_ARGS_BASE, "data_sources": _SOURCES}


@pytest.mark.anyio
async def test_set_interface_sources_sends_parsed_sources_and_returns_them(
    portal_session, mock_portal_client, extract_payload
):
    set_result = {"id": "el-uuid-1", "uuid": "el-uuid-1", "dataSources": _SOURCES}
    mock_portal_client.set_interface_sources = AsyncMock(return_value=set_result)

    async with portal_session as session:
        result = await session.call_tool("set_interface_sources", _SET_SOURCES_ARGS)

    mock_portal_client.set_interface_sources.assert_awaited_once_with(
        "page-uuid-1",
        "el-uuid-1",
        [
            InterfaceDataSource(
                id="open-requests",
                name="Open requests",
                repo_id="repo-uuid-1",
                field_keys=["title", "6a850d1c-0000-4000-8000-000000000016"],
                filters=None,
            )
        ],
        interface_uuid="html-uuid-1",
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"] == set_result


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (
            {"data_sources": [{**_SOURCES[0], "fieldKeys": []}]},
            "data_sources[0].fieldKeys: List should have at least 1 item after "
            "validation, not 0",
        ),
        (
            {"data_sources": [{**_SOURCES[0], "id": " "}, {**_SOURCES[0], "name": ""}]},
            "data_sources[0].id: Value should have at least 1 item after "
            "validation, not 0; data_sources[1].name: Value should have at least 1 "
            "item after validation, not 0",
        ),
        (
            {"data_sources": [_SOURCES[0], {**_SOURCES[0], "name": "Other"}]},
            "data_sources: Each data source needs its own id; repeated: open-requests.",
        ),
    ],
    ids=["empty field keys", "two blank values", "repeated id"],
)
async def test_set_interface_sources_rejects_invalid_sources_before_any_call(
    portal_session, mock_portal_client, arguments, message
):
    async with portal_session as session:
        result = await session.call_tool(
            "set_interface_sources", {**_SET_SOURCES_ARGS, **arguments}
        )

    payload = assert_invalid_arguments_envelope(result)
    assert payload["error"]["message"] == message
    mock_portal_client.set_interface_sources.assert_not_awaited()


_SOURCE_REFUSED = (
    "Permission denied for a data source: you can bind only the pipes and tables "
    "list_interface_repos returns for this interface."
)
_TABLE_ELEMENT = (
    "Element 'el-uuid-1' is a 'table' element; named data sources go on an HTML "
    "interface's customCode element."
)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            PipefyGraphQLError([{"message": "Couldn't find the interface"}]),
            "No HTML interface has uuid 'html-uuid-1'.",
        ),
        (PipefyGraphQLError([{"message": "Permission denied"}]), _SOURCE_REFUSED),
        (
            PipefyGraphQLError(
                [
                    {
                        "message": "Permission denied",
                        "extensions": {"code": "PERMISSION_DENIED"},
                    }
                ]
            ),
            _PORTAL_PERMISSION_DENIED_MSG,
        ),
        (
            PipefyGraphQLError([{"message": "Permission denied for this portal"}]),
            _PORTAL_PERMISSION_DENIED_MSG,
        ),
        (
            PortalPermissionError(_PORTAL_PERMISSION_DENIED_MSG),
            _PORTAL_PERMISSION_DENIED_MSG,
        ),
        (ValueError(_TABLE_ELEMENT), _TABLE_ELEMENT),
    ],
    ids=[
        "unknown interface",
        "source repo refused",
        "coded refusal",
        "other refusal text",
        "interface refused",
        "sdk",
    ],
)
async def test_set_interface_sources_maps_api_errors_for_agents(
    portal_session, mock_portal_client, extract_payload, error, message
):
    mock_portal_client.set_interface_sources = AsyncMock(side_effect=error)

    async with portal_session as session:
        result = await session.call_tool("set_interface_sources", _SET_SOURCES_ARGS)

    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["message"] == message


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            PipefyGraphQLError([{"message": "Couldn't find the organization"}]),
            "One of the data sources' repoId was not found.",
        ),
        (PipefyGraphQLError([{"message": "Permission denied"}]), _SOURCE_REFUSED),
        (
            PipefyGraphQLError(
                [
                    {
                        "message": "Permission denied",
                        "extensions": {"code": "PERMISSION_DENIED"},
                    }
                ]
            ),
            _PORTAL_PERMISSION_DENIED_MSG,
        ),
        (
            PortalPermissionError(_PORTAL_PERMISSION_DENIED_MSG),
            _PORTAL_PERMISSION_DENIED_MSG,
        ),
    ],
    ids=["unknown repo", "source repo refused", "coded refusal", "portal refused"],
)
async def test_create_html_interface_maps_api_errors_for_agents(
    portal_session, mock_portal_client, extract_payload, error, message
):
    mock_portal_client.create_interface = AsyncMock(side_effect=error)

    async with portal_session as session:
        result = await session.call_tool(
            "create_html_interface",
            {
                "organization_uuid": "org-abc-123",
                "name": "Open purchase requests",
                "html": "<div>Hello</div>",
            },
        )

    assert result.is_error is False
    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["message"] == message
    mock_portal_client.write_html_document.assert_not_awaited()


_ACTIONS = [
    {
        "actionId": "details",
        "kind": "openRecord",
        "sourceId": "open-requests",
        "fieldKeys": ["title"],
    },
    {
        "actionId": "approve",
        "kind": "triggerAutomation",
        "sourceId": "open-requests",
        "automationIds": ["301"],
    },
]
_SET_ACTIONS_ARGS = {
    "interface_uuid": "html-uuid-1",
    "page_id": "page-uuid-1",
    "element_id": "el-uuid-1",
    "actions": _ACTIONS,
}


@pytest.mark.anyio
@pytest.mark.parametrize("editable", [None, True])
async def test_set_interface_actions_sends_parsed_actions_and_returns_them(
    portal_session, mock_portal_client, extract_payload, editable
):
    set_result = {
        "id": "el-uuid-1",
        "uuid": "el-uuid-1",
        "actions": _ACTIONS,
        "editable": bool(editable),
    }
    mock_portal_client.set_interface_actions = AsyncMock(return_value=set_result)
    arguments = dict(_SET_ACTIONS_ARGS)
    if editable is not None:
        arguments["editable"] = editable

    async with portal_session as session:
        result = await session.call_tool("set_interface_actions", arguments)

    mock_portal_client.set_interface_actions.assert_awaited_once_with(
        "page-uuid-1",
        "el-uuid-1",
        [
            OpenRecordAction(
                action_id="details",
                kind="openRecord",
                source_id="open-requests",
                field_keys=["title"],
            ),
            TriggerAutomationAction(
                action_id="approve",
                kind="triggerAutomation",
                source_id="open-requests",
                automation_ids=["301"],
            ),
        ],
        interface_uuid="html-uuid-1",
        editable=editable,
    )
    payload = extract_payload(result)
    assert payload["success"] is True
    assert payload["data"] == set_result


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actions", "message"),
    [
        (
            [{**_ACTIONS[0], "sourceId": " "}],
            "actions[0].sourceId: Value should have at least 1 item after "
            "validation, not 0",
        ),
        (
            [_ACTIONS[0], {**_ACTIONS[1], "automationIds": []}],
            "actions[1].automationIds: List should have at least 1 item after "
            "validation, not 0",
        ),
        (
            [{**_ACTIONS[0], "kind": "openUrl"}],
            "actions[0].kind: Input tag 'openUrl' found using 'kind' does not "
            "match any of the expected tags: 'openStartForm', 'openRecord', "
            "'triggerAutomation'",
        ),
        (
            [{**_ACTIONS[0], "display": "page"}],
            "actions[0]: Action details opens the record on a page, so it needs "
            "a pageId: a record layout page of this interface for the source's "
            "repo.",
        ),
        (
            [_ACTIONS[0], {**_ACTIONS[1], "actionId": "details"}],
            "actions: Each action needs its own actionId; repeated: details.",
        ),
    ],
    ids=[
        "blank source id",
        "no automation ids",
        "unknown kind",
        "page display without page id",
        "repeated action id",
    ],
)
async def test_set_interface_actions_rejects_invalid_actions_before_any_call(
    portal_session, mock_portal_client, actions, message
):
    async with portal_session as session:
        result = await session.call_tool(
            "set_interface_actions", {**_SET_ACTIONS_ARGS, "actions": actions}
        )

    payload = assert_invalid_arguments_envelope(result)
    assert payload["error"]["message"] == message
    mock_portal_client.set_interface_actions.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("blank", ["interface_uuid", "page_id", "element_id"])
async def test_set_interface_actions_rejects_blank_ids_before_any_call(
    portal_session, mock_portal_client, extract_payload, blank
):
    async with portal_session as session:
        result = await session.call_tool(
            "set_interface_actions", {**_SET_ACTIONS_ARGS, blank: " "}
        )

    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["message"] == _blank_id_message(blank)
    mock_portal_client.set_interface_actions.assert_not_awaited()


_ACTION_SOURCE_REFUSED = (
    "Permission denied for a data source of this element: you can set its "
    "actions only when you can bind every pipe and table its sources read, as "
    "list_interface_repos returns them for this interface."
)
_UNKNOWN_SOURCE = (
    "actions[0].sourceId: 'closed-requests' is not a data source of this "
    "element; its sources are: open-requests"
)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            PipefyGraphQLError([{"message": "Couldn't find the interface"}]),
            "No HTML interface has uuid 'html-uuid-1'.",
        ),
        (
            PipefyGraphQLError(
                [{"message": "x", "extensions": {"code": "RESOURCE_NOT_FOUND"}}]
            ),
            "No HTML interface has uuid 'html-uuid-1'.",
        ),
        (
            PipefyGraphQLError([{"message": "Permission denied"}]),
            _ACTION_SOURCE_REFUSED,
        ),
        (
            PipefyGraphQLError(
                [
                    {
                        "message": "Permission denied",
                        "extensions": {"code": "PERMISSION_DENIED"},
                    }
                ]
            ),
            _PORTAL_PERMISSION_DENIED_MSG,
        ),
        (
            PortalPermissionError(_PORTAL_PERMISSION_DENIED_MSG),
            _PORTAL_PERMISSION_DENIED_MSG,
        ),
        (
            PipefyGraphQLError(
                [
                    {
                        "message": "Action approve lists automationIds that are "
                        "not manually triggered automations of its source's repo: 9"
                    }
                ]
            ),
            "Action approve lists automationIds that are not manually triggered "
            "automations of its source's repo: 9",
        ),
        (ValueError(_UNKNOWN_SOURCE), _UNKNOWN_SOURCE),
    ],
    ids=[
        "unknown interface",
        "coded not found",
        "source repo refused",
        "coded refusal",
        "interface refused",
        "action refused by the api",
        "sdk",
    ],
)
async def test_set_interface_actions_maps_api_errors_for_agents(
    portal_session, mock_portal_client, extract_payload, error, message
):
    mock_portal_client.set_interface_actions = AsyncMock(side_effect=error)

    async with portal_session as session:
        result = await session.call_tool("set_interface_actions", _SET_ACTIONS_ARGS)

    payload = extract_payload(result)
    assert payload["success"] is False
    assert payload["error"]["message"] == message
