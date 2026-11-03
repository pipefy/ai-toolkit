"""Tests for ``pipefy portal`` subcommands."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from _shared.fixture_ids import EXAMPLE_PIPE_REPO_ID
from pipefy_sdk import PipefyGraphQLError
from pipefy_sdk.exceptions import (
    HtmlValidationError,
    HtmlViolation,
    PortalPermissionError,
)
from pipefy_sdk.models.portal import (
    OpenRecordAction,
    TriggerAutomationAction,
    parse_portal_page_layout,
)

from pipefy_cli.main import app

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


def test_portal_list_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-list")
    payload = [_PORTAL_LIST_NODE]
    mock_client = MagicMock()
    mock_client.list_portals = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "list", "--organization-uuid", "org-123", "--json"],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.list_portals.assert_awaited_once_with("org-123", search_term=None)


def test_portal_get_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-get")
    mock_client = MagicMock()
    mock_client.get_portal = AsyncMock(return_value=_PORTAL_DETAIL)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "get", "portal-uuid-1", "--json"],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _PORTAL_DETAIL
    mock_client.get_portal.assert_awaited_once_with("portal-uuid-1")


def test_portal_list_missing_org_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-list-missing-org")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["portal", "list", "--json"])
    assert result.exit_code == 2
    mock_client.list_portals.assert_not_called()


def test_portal_get_missing_uuid_exit_2(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-get-missing-uuid")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["portal", "get", "--json"])
    assert result.exit_code == 2
    mock_client.get_portal.assert_not_called()


def test_portal_delete_without_yes_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-del-no-yes")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["portal", "delete", "portal-uuid-1"])
    assert result.exit_code == 1
    mock_client.delete_portal.assert_not_called()


def test_portal_delete_with_yes_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-del-yes")
    payload = {"deleteInterface": {"success": True}}
    mock_client = MagicMock()
    mock_client.delete_portal = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "delete", "portal-uuid-1", "--yes", "--json"],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.delete_portal.assert_awaited_once_with("portal-uuid-1")


def test_portal_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-create")
    payload = {
        "id": "portal-uuid-new",
        "uuid": "portal-uuid-new",
        "name": "Main Portal",
    }
    mock_client = MagicMock()
    mock_client.create_portal = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "create", "--organization-uuid", "org-123", "--json"],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.create_portal.assert_awaited_once_with("org-123")


def test_portal_update_name_visibility_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-update")
    payload = {
        "id": "portal-uuid-1",
        "uuid": "portal-uuid-1",
        "name": "Renamed Portal",
        "visibility": "public",
    }
    mock_client = MagicMock()
    mock_client.update_portal = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "update",
                "portal-uuid-1",
                "--name",
                "Renamed Portal",
                "--visibility",
                "public",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.update_portal.assert_awaited_once_with(
        "portal-uuid-1",
        name="Renamed Portal",
        visibility="public",
    )


def test_portal_update_no_attributes_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-upd-none")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "update", "portal-uuid-1", "--json"],
        )
    assert result.exit_code == 2
    mock_client.update_portal.assert_not_called()


def test_portal_update_blank_name_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-upd-blank-name")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "update", "portal-uuid-1", "--name", "   ", "--json"],
        )
    assert result.exit_code == 2
    mock_client.update_portal.assert_not_called()


# ---------------------------------------------------------------------------
# Portal page subcommands
# ---------------------------------------------------------------------------

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


def test_portal_page_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-page-create")
    mock_client = MagicMock()
    mock_client.create_portal_page = AsyncMock(return_value=_CREATED_PAGE)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "create",
                "--portal-uuid",
                _PORTAL_UUID,
                "--title",
                _PAGE_TITLE,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _CREATED_PAGE
    mock_client.create_portal_page.assert_awaited_once_with(
        _PORTAL_UUID,
        _PAGE_TITLE,
        description=None,
        index=None,
    )


def test_portal_page_create_with_optional_fields_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-create-opts")
    mock_client = MagicMock()
    mock_client.create_portal_page = AsyncMock(return_value=_CREATED_PAGE)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "create",
                "--portal-uuid",
                _PORTAL_UUID,
                "--title",
                _PAGE_TITLE,
                "--description",
                "Landing copy",
                "--index",
                "1",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.create_portal_page.assert_awaited_once_with(
        _PORTAL_UUID,
        _PAGE_TITLE,
        description="Landing copy",
        index=1,
    )


def test_portal_page_update_title_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-page-update")
    payload = {**_CREATED_PAGE, "title": "Renamed Page"}
    mock_client = MagicMock()
    mock_client.update_portal_page = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "update",
                _PORTAL_UUID,
                _PAGE_UUID,
                "--title",
                "Renamed Page",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.update_portal_page.assert_awaited_once_with(
        _PORTAL_UUID,
        _PAGE_UUID,
        title="Renamed Page",
    )


def test_portal_page_update_no_attributes_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-upd-none")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "update",
                _PORTAL_UUID,
                _PAGE_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.update_portal_page.assert_not_called()


def test_portal_page_delete_without_yes_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-del-no-yes")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "page", "delete", _PORTAL_UUID, _PAGE_UUID],
        )
    assert result.exit_code == 1
    mock_client.delete_portal_page.assert_not_called()


def test_portal_page_delete_with_yes_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-del-yes")
    payload = {"deletePage": {"success": True}}
    mock_client = MagicMock()
    mock_client.delete_portal_page = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "delete",
                _PORTAL_UUID,
                _PAGE_UUID,
                "--yes",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.delete_portal_page.assert_awaited_once_with(_PORTAL_UUID, _PAGE_UUID)


def test_portal_page_sort_comma_separated_page_ids_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-sort-csv")
    page_ids = [_PAGE_UUID_2, _PAGE_UUID]
    payload = {"sortPages": {"success": True}}
    mock_client = MagicMock()
    mock_client.sort_portal_pages = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "sort",
                "--portal-uuid",
                _PORTAL_UUID,
                "--page-ids",
                f"{_PAGE_UUID_2},{_PAGE_UUID}",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.sort_portal_pages.assert_awaited_once_with(_PORTAL_UUID, page_ids)


def test_portal_page_sort_ids_json_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-page-sort-json")
    page_ids = [_PAGE_UUID_2, _PAGE_UUID]
    payload = {"sortPages": {"success": True}}
    mock_client = MagicMock()
    mock_client.sort_portal_pages = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "sort",
                "--portal-uuid",
                _PORTAL_UUID,
                "--ids-json",
                json.dumps(page_ids),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.sort_portal_pages.assert_awaited_once_with(_PORTAL_UUID, page_ids)


def test_portal_page_sort_page_ids_csv_rejects_duplicate_ids(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-sort-dup-csv")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "sort",
                "--portal-uuid",
                _PORTAL_UUID,
                "--page-ids",
                f"{_PAGE_UUID},{_PAGE_UUID}",
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.sort_portal_pages.assert_not_called()


def test_portal_page_sort_ids_json_rejects_duplicate_ids(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-sort-dup-json")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "sort",
                "--portal-uuid",
                _PORTAL_UUID,
                "--ids-json",
                json.dumps([_PAGE_UUID, _PAGE_UUID]),
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.sort_portal_pages.assert_not_called()


def test_portal_page_create_rejects_negative_index(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-create-bad-index")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "create",
                "--portal-uuid",
                _PORTAL_UUID,
                "--title",
                "Home",
                "--index",
                "-1",
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.create_portal_page.assert_not_called()


def test_portal_page_sort_page_ids_csv_rejects_invalid_items(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-sort-invalid-csv")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "sort",
                "--portal-uuid",
                _PORTAL_UUID,
                "--page-ids",
                "0,-1,page-1",
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.sort_portal_pages.assert_not_called()


def test_portal_page_sort_ids_json_rejects_invalid_items(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-sort-invalid-json")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "sort",
                "--portal-uuid",
                _PORTAL_UUID,
                "--ids-json",
                json.dumps([None, "   ", False]),
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.sort_portal_pages.assert_not_called()


def test_portal_page_sort_missing_page_ids_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-sort-missing")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "page", "sort", "--portal-uuid", _PORTAL_UUID, "--json"],
        )
    assert result.exit_code == 2
    mock_client.sort_portal_pages.assert_not_called()


def test_portal_page_layout_update_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-page-layout")
    payload = {"updatePageLayout": {"success": True}}
    mock_client = MagicMock()
    mock_client.update_portal_page_layout = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "layout",
                "update",
                "--page-id",
                _PAGE_UUID,
                "--layout",
                json.dumps(_PAGE_LAYOUT),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.update_portal_page_layout.assert_awaited_once_with(
        _PAGE_UUID, parse_portal_page_layout(_PAGE_LAYOUT)
    )


def test_portal_page_layout_update_accepts_empty_array(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-page-layout-empty")
    payload = {"updatePageLayout": {"success": True}}
    mock_client = MagicMock()
    mock_client.update_portal_page_layout = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "layout",
                "update",
                "--page-id",
                _PAGE_UUID,
                "--layout",
                "[]",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.update_portal_page_layout.assert_awaited_once_with(_PAGE_UUID, [])


@pytest.mark.parametrize(
    "layout",
    [
        [{}],
        [{"children": ["el-1"]}],
        [{"id": "row-1", "type": "column", "children": ["el-1"]}],
    ],
)
def test_page_layout_rejects_malformed_rows(
    runner, clean_pipefy_env, saved_cwd, oauth_env, layout
):
    oauth_env("portal-layout-malformed-row")
    mock_client = MagicMock()
    mock_client.update_portal_page_layout = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "page",
                "layout",
                "update",
                "--page-id",
                _PAGE_UUID,
                "--layout",
                json.dumps(layout),
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "type 'row'" in result.stderr
    mock_client.update_portal_page_layout.assert_not_called()


# ---------------------------------------------------------------------------
# Portal element subcommands
# ---------------------------------------------------------------------------

_ELEMENT_UUID = "el-uuid-1"
_FORMS_METADATA = {"name": "Request form"}
_FORMS_DATA_SOURCES = [{"repoId": EXAMPLE_PIPE_REPO_ID}]

_CREATED_ELEMENT = {
    "id": _ELEMENT_UUID,
    "uuid": _ELEMENT_UUID,
    "type": "forms",
    "metadata": _FORMS_METADATA,
}


def test_portal_element_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-element-create")
    mock_client = MagicMock()
    mock_client.create_portal_element = AsyncMock(return_value=_CREATED_ELEMENT)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "create",
                "--page-id",
                _PAGE_UUID,
                "--type",
                "forms",
                "--metadata",
                json.dumps(_FORMS_METADATA),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _CREATED_ELEMENT
    mock_client.create_portal_element.assert_awaited_once_with(
        _PAGE_UUID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=[],
    )


def test_portal_element_create_with_data_sources_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-create-ds")
    mock_client = MagicMock()
    mock_client.create_portal_element = AsyncMock(return_value=_CREATED_ELEMENT)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "create",
                "--page-id",
                _PAGE_UUID,
                "--type",
                "forms",
                "--metadata",
                json.dumps(_FORMS_METADATA),
                "--data-sources",
                json.dumps(_FORMS_DATA_SOURCES),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.create_portal_element.assert_awaited_once_with(
        _PAGE_UUID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=_FORMS_DATA_SOURCES,
    )


def test_portal_element_create_rejects_invalid_metadata_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-create-bad-meta")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "create",
                "--page-id",
                _PAGE_UUID,
                "--type",
                "forms",
                "--metadata",
                json.dumps({}),
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.create_portal_element.assert_not_called()


def test_portal_element_create_missing_metadata_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-create-no-meta")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "create",
                "--page-id",
                _PAGE_UUID,
                "--type",
                "forms",
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.create_portal_element.assert_not_called()


def test_portal_element_update_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-element-update")
    link_metadata = {
        "linkUrl": "https://example.com/pipefy",
        "linkName": "Open",
    }
    payload = {
        **_CREATED_ELEMENT,
        "type": "link",
        "metadata": link_metadata,
    }
    mock_client = MagicMock()
    mock_client.update_portal_element = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "update",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--type",
                "link",
                "--metadata",
                json.dumps(link_metadata),
                "--data-sources",
                "[]",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.update_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID,
        _PAGE_UUID,
        type="link",
        metadata=link_metadata,
        data_sources=[],
        portal_uuid=None,
    )


def test_portal_element_update_keeps_data_sources_with_portal_uuid(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """Without --data-sources, --portal-uuid lets the SDK keep the current ones."""
    oauth_env("portal-element-update-keep")
    mock_client = MagicMock()
    mock_client.update_portal_element = AsyncMock(
        return_value={**_CREATED_ELEMENT, "metadata": _FORMS_METADATA}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "update",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--type",
                "forms",
                "--metadata",
                json.dumps(_FORMS_METADATA),
                "--portal-uuid",
                _PORTAL_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.update_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID,
        _PAGE_UUID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=None,
        portal_uuid=_PORTAL_UUID,
    )


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _panel_text(stderr: str) -> str:
    """Flatten a Typer error panel into one line of words, without ANSI styling.

    Rich styles option names when color is forced (CI sets ``FORCE_COLOR``), which
    splits ``--portal-uuid`` into escape-wrapped pieces.
    """
    plain = _ANSI_ESCAPE.sub("", stderr)
    return " ".join(plain.replace("│", " ").split())


def _invoke_element_update(runner, mock_client, *options: str):
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        return runner.invoke(
            app,
            [
                "portal",
                "element",
                "update",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--type",
                "forms",
                "--metadata",
                json.dumps(_FORMS_METADATA),
                *options,
                "--json",
            ],
        )


def test_portal_element_update_without_data_sources_or_portal_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """Omitting both is rejected before any call, naming the two flags."""
    oauth_env("portal-element-update-neither")
    mock_client = MagicMock()
    result = _invoke_element_update(runner, mock_client)
    assert result.exit_code == 2
    assert (
        "Pass --portal-uuid to keep the element's current data sources, or "
        "--data-sources to replace them ('[]' unlinks them all)."
    ) in _panel_text(result.stderr)
    mock_client.update_portal_element.assert_not_called()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (("--portal-uuid", "   "), "--portal-uuid, when provided, must be non-empty."),
        (
            ("--data-sources", "  ", "--portal-uuid", _PORTAL_UUID),
            "--data-sources, when provided, must be non-empty.",
        ),
    ],
)
def test_portal_element_update_rejects_blank_option_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env, options, message
):
    oauth_env("portal-element-update-blank")
    mock_client = MagicMock()
    result = _invoke_element_update(runner, mock_client, *options)
    assert result.exit_code == 2
    assert message in _panel_text(result.stderr)
    mock_client.update_portal_element.assert_not_called()


def test_portal_element_update_element_not_on_page_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """The SDK's keep-path lookup error reaches stderr as is."""
    oauth_env("portal-element-update-not-on-page")
    message = (
        f"Element '{_ELEMENT_UUID}' is on page '{_PAGE_UUID_2}' of portal "
        f"'{_PORTAL_UUID}', not on page '{_PAGE_UUID}'. Pass page_id='{_PAGE_UUID_2}'."
    )
    mock_client = MagicMock()
    mock_client.update_portal_element = AsyncMock(side_effect=ValueError(message))
    result = _invoke_element_update(runner, mock_client, "--portal-uuid", _PORTAL_UUID)
    assert result.exit_code == 2
    assert message in result.stderr


def test_portal_element_update_rejects_invalid_metadata_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-upd-bad-meta")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "update",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--type",
                "link",
                "--metadata",
                json.dumps({}),
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.update_portal_element.assert_not_called()


def test_portal_element_delete_without_yes_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-del-no-yes")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "element", "delete", _ELEMENT_UUID, _PAGE_UUID],
        )
    assert result.exit_code == 1
    mock_client.delete_portal_element.assert_not_called()


def test_portal_element_delete_with_yes_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-del-yes")
    payload = {"deleteElement": {"success": True}}
    mock_client = MagicMock()
    mock_client.delete_portal_element = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "delete",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--yes",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == payload
    mock_client.delete_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID, _PAGE_UUID
    )


def test_portal_element_delete_forwards_pruned_layout(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-del-layout")
    pruned = [{"id": "row-1", "type": "row", "children": ["el-other"]}]
    mock_client = MagicMock()
    mock_client.delete_portal_element = AsyncMock(
        return_value={"deleteElement": {"success": True}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "delete",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--layout",
                json.dumps(pruned),
                "--yes",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.delete_portal_element.assert_awaited_once_with(
        _ELEMENT_UUID, _PAGE_UUID, layout=parse_portal_page_layout(pruned)
    )


def test_portal_element_delete_prompt_names_the_layout_rewrite(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-del-layout-prompt")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "delete",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--layout",
                "[]",
            ],
            input="n\n",
        )
    assert result.exit_code == 1
    assert "replace that page's layout" in result.stdout
    mock_client.delete_portal_element.assert_not_called()


def test_portal_element_delete_rejects_layout_still_listing_element_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-del-layout-orphan")
    leftover = [{"id": "row-1", "type": "row", "children": [_ELEMENT_UUID]}]
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "delete",
                _ELEMENT_UUID,
                _PAGE_UUID,
                "--layout",
                json.dumps(leftover),
                "--yes",
            ],
        )
    assert result.exit_code == 2
    assert "still lists element_id" in result.stderr
    mock_client.delete_portal_element.assert_not_called()


@pytest.mark.parametrize("raw_layout", ["", "  ", "null"])
@pytest.mark.parametrize(
    "command",
    [
        ["delete", _ELEMENT_UUID, _PAGE_UUID, "--yes"],
        [
            "create",
            "--page-id",
            _PAGE_UUID,
            "--type",
            "link",
            "--metadata",
            json.dumps({"linkName": "Docs"}),
            "--element-id",
            "el-new",
        ],
    ],
    ids=["delete", "create"],
)
def test_portal_element_given_blank_layout_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env, command, raw_layout
):
    """A layout variable that came out empty must not run the write without a grid."""
    oauth_env("portal-element-blank-layout")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app, ["portal", "element", *command, "--layout", raw_layout]
        )
    assert result.exit_code == 2
    assert "JSON array of row objects" in result.stderr
    mock_client.delete_portal_element.assert_not_called()
    mock_client.create_portal_element.assert_not_called()


def test_portal_element_duplicate_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-element-dup")
    duplicated = {
        "id": "el-copy",
        "uuid": "el-copy",
        "type": "text",
        "metadata": {},
    }
    mock_client = MagicMock()
    mock_client.duplicate_portal_element = AsyncMock(return_value=duplicated)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "duplicate",
                "--element-id",
                _ELEMENT_UUID,
                "--portal-uuid",
                _PORTAL_UUID,
                "--page-id",
                _PAGE_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == duplicated
    mock_client.duplicate_portal_element.assert_awaited_once_with(
        element_id=_ELEMENT_UUID,
        portal_uuid=_PORTAL_UUID,
        page_id=_PAGE_UUID,
    )


def test_portal_element_duplicate_missing_portal_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-dup-no-portal")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "duplicate",
                "--element-id",
                _ELEMENT_UUID,
                "--page-id",
                _PAGE_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.duplicate_portal_element.assert_not_called()


def test_portal_element_duplicate_missing_page_id_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-dup-no-page")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "duplicate",
                "--element-id",
                _ELEMENT_UUID,
                "--portal-uuid",
                _PORTAL_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.duplicate_portal_element.assert_not_called()


# ---------------------------------------------------------------------------
# Portal sub-portal subcommands (task 6.5 RED — sub_portal_app in 6.6)
# ---------------------------------------------------------------------------

_MAIN_PORTAL_UUID = _PORTAL_UUID
_SUB_PORTAL_UUID = "sub-portal-uuid-1"
_FORMS_ELEMENT_ID = "el-forms-1"
_SUB_PORTAL_NAME = "Sub Portal 1"

_CREATED_SUB_PORTAL = {
    "id": _SUB_PORTAL_UUID,
    "uuid": _SUB_PORTAL_UUID,
    "name": _SUB_PORTAL_NAME,
}

_UPDATE_SUB_PORTAL_ELEMENT_RESULT = {"updateSubPortalElement": {"success": True}}
_DELETE_SUB_PORTAL_ELEMENT_RESULT = {"deleteSubPortalElement": {"success": True}}
_DELETE_SUB_PORTAL_RESULT = {"deleteSubPortalInterface": {"success": True}}


def _sub_portal_validation_stderr(result) -> str:
    return (result.stderr or result.stdout or "").lower()


def test_portal_sub_portal_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-sub-portal-create")
    mock_client = MagicMock()
    mock_client.create_sub_portal = AsyncMock(return_value=_CREATED_SUB_PORTAL)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "create",
                "--main-portal-uuid",
                _MAIN_PORTAL_UUID,
                "--name",
                _SUB_PORTAL_NAME,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _CREATED_SUB_PORTAL
    mock_client.create_sub_portal.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        name=_SUB_PORTAL_NAME,
    )


def test_portal_sub_portal_create_rejects_blank_main_portal_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-create-blank-main")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "create",
                "--main-portal-uuid",
                "   ",
                "--name",
                _SUB_PORTAL_NAME,
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "non-empty" in _sub_portal_validation_stderr(result)
    mock_client.create_sub_portal.assert_not_called()


def test_portal_sub_portal_attach_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-sub-portal-attach")
    mock_client = MagicMock()
    mock_client.update_sub_portal_element = AsyncMock(
        return_value=_UPDATE_SUB_PORTAL_ELEMENT_RESULT
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "attach",
                _MAIN_PORTAL_UUID,
                _FORMS_ELEMENT_ID,
                _SUB_PORTAL_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _UPDATE_SUB_PORTAL_ELEMENT_RESULT
    mock_client.update_sub_portal_element.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
        _SUB_PORTAL_UUID,
    )


def test_portal_sub_portal_attach_rejects_blank_portal_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-attach-blank-portal")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "attach",
                "   ",
                _FORMS_ELEMENT_ID,
                _SUB_PORTAL_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "non-empty" in _sub_portal_validation_stderr(result)
    mock_client.update_sub_portal_element.assert_not_called()


def test_portal_sub_portal_attach_rejects_blank_element_id_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-attach-blank-element")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "attach",
                _MAIN_PORTAL_UUID,
                "   ",
                _SUB_PORTAL_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "non-empty" in _sub_portal_validation_stderr(result)
    mock_client.update_sub_portal_element.assert_not_called()


def test_portal_sub_portal_attach_rejects_blank_sub_portal_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-attach-blank-sub")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "attach",
                _MAIN_PORTAL_UUID,
                _FORMS_ELEMENT_ID,
                "   ",
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "non-empty" in _sub_portal_validation_stderr(result)
    mock_client.update_sub_portal_element.assert_not_called()


def test_portal_sub_portal_detach_without_yes_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-detach-no-yes")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "detach",
                _MAIN_PORTAL_UUID,
                _FORMS_ELEMENT_ID,
            ],
        )
    assert result.exit_code == 1
    mock_client.delete_sub_portal_element.assert_not_called()


def test_portal_sub_portal_detach_with_yes_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-detach-yes")
    mock_client = MagicMock()
    mock_client.delete_sub_portal_element = AsyncMock(
        return_value=_DELETE_SUB_PORTAL_ELEMENT_RESULT
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "detach",
                _MAIN_PORTAL_UUID,
                _FORMS_ELEMENT_ID,
                "--yes",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _DELETE_SUB_PORTAL_ELEMENT_RESULT
    mock_client.delete_sub_portal_element.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
    )


def test_portal_sub_portal_publish_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("portal-sub-portal-publish")
    mock_client = MagicMock()
    mock_client.publish_sub_portal = AsyncMock(
        return_value=_UPDATE_SUB_PORTAL_ELEMENT_RESULT
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "publish",
                _MAIN_PORTAL_UUID,
                _FORMS_ELEMENT_ID,
                _SUB_PORTAL_UUID,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _UPDATE_SUB_PORTAL_ELEMENT_RESULT
    mock_client.publish_sub_portal.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
        _SUB_PORTAL_UUID,
    )


def test_portal_sub_portal_publish_rejects_blank_sub_portal_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-publish-blank-sub")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "publish",
                _MAIN_PORTAL_UUID,
                _FORMS_ELEMENT_ID,
                "   ",
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "non-empty" in _sub_portal_validation_stderr(result)
    mock_client.publish_sub_portal.assert_not_called()


def test_portal_sub_portal_unpublish_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-unpublish")
    mock_client = MagicMock()
    mock_client.unpublish_sub_portal = AsyncMock(
        return_value=_UPDATE_SUB_PORTAL_ELEMENT_RESULT
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "unpublish",
                _MAIN_PORTAL_UUID,
                _FORMS_ELEMENT_ID,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _UPDATE_SUB_PORTAL_ELEMENT_RESULT
    mock_client.unpublish_sub_portal.assert_awaited_once_with(
        _MAIN_PORTAL_UUID,
        _FORMS_ELEMENT_ID,
    )


def test_portal_sub_portal_unpublish_rejects_blank_portal_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-unpublish-blank-portal")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "unpublish",
                "   ",
                _FORMS_ELEMENT_ID,
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "non-empty" in _sub_portal_validation_stderr(result)
    mock_client.unpublish_sub_portal.assert_not_called()


def test_portal_sub_portal_delete_without_yes_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-del-no-yes")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "sub-portal", "delete", _SUB_PORTAL_UUID],
        )
    assert result.exit_code == 1
    mock_client.delete_sub_portal.assert_not_called()


def test_portal_sub_portal_delete_with_yes_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-sub-portal-del-yes")
    mock_client = MagicMock()
    mock_client.delete_sub_portal = AsyncMock(return_value=_DELETE_SUB_PORTAL_RESULT)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "sub-portal",
                "delete",
                _SUB_PORTAL_UUID,
                "--yes",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _DELETE_SUB_PORTAL_RESULT
    mock_client.delete_sub_portal.assert_awaited_once_with(_SUB_PORTAL_UUID)


_BLANK_SUB_PORTAL_CLI_ID_CASES: list[tuple[str, Callable[[str], list[str]], str]] = [
    (
        "create-main-portal",
        lambda blank: [
            "portal",
            "sub-portal",
            "create",
            "--main-portal-uuid",
            blank,
            "--name",
            _SUB_PORTAL_NAME,
            "--json",
        ],
        "create_sub_portal",
    ),
    (
        "detach-portal",
        lambda blank: [
            "portal",
            "sub-portal",
            "detach",
            blank,
            _FORMS_ELEMENT_ID,
            "--yes",
            "--json",
        ],
        "delete_sub_portal_element",
    ),
    (
        "detach-element",
        lambda blank: [
            "portal",
            "sub-portal",
            "detach",
            _MAIN_PORTAL_UUID,
            blank,
            "--yes",
            "--json",
        ],
        "delete_sub_portal_element",
    ),
    (
        "publish-portal",
        lambda blank: [
            "portal",
            "sub-portal",
            "publish",
            blank,
            _FORMS_ELEMENT_ID,
            _SUB_PORTAL_UUID,
            "--json",
        ],
        "publish_sub_portal",
    ),
    (
        "publish-element",
        lambda blank: [
            "portal",
            "sub-portal",
            "publish",
            _MAIN_PORTAL_UUID,
            blank,
            _SUB_PORTAL_UUID,
            "--json",
        ],
        "publish_sub_portal",
    ),
    (
        "unpublish-element",
        lambda blank: [
            "portal",
            "sub-portal",
            "unpublish",
            _MAIN_PORTAL_UUID,
            blank,
            "--json",
        ],
        "unpublish_sub_portal",
    ),
    (
        "delete-sub-portal",
        lambda blank: [
            "portal",
            "sub-portal",
            "delete",
            blank,
            "--yes",
            "--json",
        ],
        "delete_sub_portal",
    ),
]


@pytest.mark.parametrize("blank_id", ["", "   "])
@pytest.mark.parametrize(
    ("case_id", "build_args", "client_method"),
    _BLANK_SUB_PORTAL_CLI_ID_CASES,
    ids=[case[0] for case in _BLANK_SUB_PORTAL_CLI_ID_CASES],
)
def test_portal_sub_portal_rejects_blank_ids_exit_2(
    runner,
    clean_pipefy_env,
    saved_cwd,
    oauth_env,
    blank_id: str,
    case_id: str,
    build_args: Callable[[str], list[str]],
    client_method: str,
):
    oauth_env(f"portal-sub-portal-blank-{case_id}-{blank_id.strip() or 'empty'}")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, build_args(blank_id))
    assert result.exit_code == 2
    assert "non-empty" in _sub_portal_validation_stderr(result)
    getattr(mock_client, client_method).assert_not_called()


def test_portal_sub_portal_detach_graphql_error_exits_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A non-permission GraphQL error on an internal-API portal command exits 1.

    This path used to arrive as a ValueError (the ``[code=...]`` envelope) and
    exit 2, the usage-error code. It now raises PipefyGraphQLError and exits 1,
    aligned with public-API command failures. Permission errors still exit 2 via
    PortalPermissionError, unchanged.

    The ``errors`` payload here is the shape the Internal API actually returns
    for a nonexistent PortalInterface, so the assertion pins the real stderr
    line and not just the exit code. ``correlation_id`` stays out of the
    message: the CLI renders code and message only.
    """
    oauth_env("portal-sub-detach-error")
    mock_client = MagicMock()
    mock_client.delete_sub_portal_element = AsyncMock(
        side_effect=PipefyGraphQLError(
            [
                {
                    "message": "Couldn't find PortalInterface with",
                    "path": ["deleteSubPortalElement"],
                    "extensions": {
                        "code": "RECORD_NOT_FOUND",
                        "correlation_id": "a22c1fbab98ae41d-GRU",
                    },
                }
            ]
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "sub-portal", "detach", "portal-uuid-1", "element-1", "--yes"],
        )
    assert result.exit_code == 1, result.stdout + (result.stderr or "")
    assert (
        result.stderr.strip() == "Couldn't find PortalInterface with (RECORD_NOT_FOUND)"
    )
    mock_client.delete_sub_portal_element.assert_awaited_once_with(
        "portal-uuid-1", "element-1"
    )


def test_portal_sub_portal_detach_graphql_error_without_code_is_message_only(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """An error carrying no ``extensions.code`` renders the message with no suffix.

    Pins the other branch of the CLI formatter, so a future change that always
    appends a parenthesised code cannot land silently.
    """
    oauth_env("portal-sub-detach-error-no-code")
    mock_client = MagicMock()
    mock_client.delete_sub_portal_element = AsyncMock(
        side_effect=PipefyGraphQLError(
            [{"message": "Something went wrong on the server"}]
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "sub-portal", "detach", "portal-uuid-1", "element-1", "--yes"],
        )
    assert result.exit_code == 1, result.stdout + (result.stderr or "")
    assert result.stderr.strip() == "Something went wrong on the server"


def test_portal_sub_portal_detach_permission_error_still_exits_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A portal permission error keeps exiting 2, the other half of the pair above.

    ``PortalPermissionError`` subclasses ``ValueError``, not ``PipefyError``, so it
    reaches the runner's ``ValueError`` branch and keeps its exit code while
    non-permission GraphQL errors moved from 2 to 1. Portal permission mapping now
    runs through ``classify_exception``, so pin the exit code here rather than
    inferring it from the SDK-level mapping tests.
    """
    oauth_env("portal-sub-detach-permission")
    mock_client = MagicMock()
    mock_client.delete_sub_portal_element = AsyncMock(
        side_effect=PortalPermissionError(
            "This token lacks manage_portals on the organization."
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "sub-portal", "detach", "portal-uuid-1", "element-1", "--yes"],
        )
    assert result.exit_code == 2, result.stdout + (result.stderr or "")
    assert "manage_portals" in result.stderr


@pytest.mark.parametrize("layout", [{"rows": []}, ["element-1"], None])
def test_page_layout_rejects_non_row_arrays(
    runner, clean_pipefy_env, saved_cwd, oauth_env, layout
):
    oauth_env("portal-layout-invalid")
    result = runner.invoke(
        app,
        [
            "portal",
            "page",
            "layout",
            "update",
            "--page-id",
            _PAGE_UUID,
            "--layout",
            json.dumps(layout),
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert "JSON array of row objects" in result.stderr


_PLACING_LAYOUT = [
    {"id": "row-1", "type": "row", "children": ["el-1"]},
    {"id": "row-2", "type": "row", "children": ["el-new"]},
]


def test_portal_element_create_with_layout_places_element(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("portal-element-create-layout")
    mock_client = MagicMock()
    mock_client.create_portal_element = AsyncMock(return_value=_CREATED_ELEMENT)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "create",
                "--page-id",
                _PAGE_UUID,
                "--type",
                "forms",
                "--metadata",
                json.dumps(_FORMS_METADATA),
                "--element-id",
                "el-new",
                "--layout",
                json.dumps(_PLACING_LAYOUT),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.create_portal_element.assert_awaited_once_with(
        _PAGE_UUID,
        type="forms",
        metadata=_FORMS_METADATA,
        data_sources=[],
        element_id="el-new",
        layout=parse_portal_page_layout(_PLACING_LAYOUT),
    )


@pytest.mark.parametrize(
    ("extra_args", "expected"),
    [
        (
            ["--element-id", "el-new", "--layout", json.dumps({"rows": []})],
            "JSON array of row objects",
        ),
        (["--layout", json.dumps(_PLACING_LAYOUT)], "element_id"),
        (
            [
                "--element-id",
                "el-new",
                "--layout",
                json.dumps([{"children": ["el-new"]}]),
            ],
            "type 'row'",
        ),
    ],
    ids=["object-wrapper", "missing-element-id", "incomplete-row"],
)
def test_portal_element_create_rejects_unplaceable_layout_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env, extra_args, expected
):
    oauth_env("portal-element-create-bad-layout")
    mock_client = MagicMock()
    mock_client.create_portal_element = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "element",
                "create",
                "--page-id",
                _PAGE_UUID,
                "--type",
                "forms",
                "--metadata",
                json.dumps(_FORMS_METADATA),
                *extra_args,
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert expected in result.stderr
    mock_client.create_portal_element.assert_not_called()


# ---------------------------------------------------------------------------
# portal html-interface
# ---------------------------------------------------------------------------

_HTML_INTERFACE_LIST_NODE = {
    "id": "html-uuid-1",
    "uuid": "html-uuid-1",
    "name": "Open purchase requests",
    "visibility": "internal",
    "contentModeHtml": True,
}

_HTML_INTERFACE_DETAIL = {
    "id": "html-uuid-1",
    "uuid": "html-uuid-1",
    "name": "Open purchase requests",
    "pages": [
        {
            "id": "page-1",
            "uuid": "page-1",
            "title": "Open purchase requests",
            "elements": [
                {
                    "id": "el-1",
                    "uuid": "el-1",
                    "type": "customCode",
                    "htmlDocument": {"content": "<div>Hello</div>"},
                }
            ],
        }
    ],
}

_CREATED_HTML_INTERFACE = {
    "id": "html-uuid-new",
    "uuid": "html-uuid-new",
    "name": "Open purchase requests",
    "pages": [
        {
            "id": "page-new-1",
            "uuid": "page-new-1",
            "title": "Open purchase requests",
            "elements": [{"id": "el-new-1", "uuid": "el-new-1", "type": "customCode"}],
        }
    ],
}


def test_html_interface_list_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("html-interface-list")
    mock_client = MagicMock()
    mock_client.list_html_interfaces = AsyncMock(
        return_value=[_HTML_INTERFACE_LIST_NODE]
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "list",
                "--organization-uuid",
                "org-123",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == [_HTML_INTERFACE_LIST_NODE]
    mock_client.list_html_interfaces.assert_awaited_once_with(
        "org-123", search_term=None
    )


def test_html_interface_get_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("html-interface-get")
    mock_client = MagicMock()
    mock_client.get_html_interface = AsyncMock(return_value=_HTML_INTERFACE_DETAIL)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app, ["portal", "html-interface", "get", "html-uuid-1", "--json"]
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _HTML_INTERFACE_DETAIL
    mock_client.get_html_interface.assert_awaited_once_with("html-uuid-1")


def test_html_interface_write_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("html-interface-write")
    mock_client = MagicMock()
    mock_client.write_html_document = AsyncMock(return_value={"success": True})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content",
                "<div>Hello</div>",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == {"success": True}
    mock_client.write_html_document.assert_awaited_once_with(
        page_id="page-1", element_id="el-1", content="<div>Hello</div>"
    )


def test_html_interface_write_rejects_blank_content_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-write-blank")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content",
                "   ",
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.write_html_document.assert_not_called()


def test_html_interface_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("html-interface-create")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(return_value=_CREATED_HTML_INTERFACE)
    mock_client.write_html_document = AsyncMock(return_value={"success": True})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == _CREATED_HTML_INTERFACE
    mock_client.create_interface.assert_awaited_once_with(
        "org-123", "Open purchase requests", color="blue", data_sources=None
    )
    mock_client.write_html_document.assert_awaited_once_with(
        page_id="page-new-1", element_id="el-new-1", content="<div>Hello</div>"
    )


def test_html_interface_create_write_failure_names_retry_ids_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A failed second call must not be retried as a second create."""
    oauth_env("html-interface-create-write-fails")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(return_value=_CREATED_HTML_INTERFACE)
    mock_client.write_html_document = AsyncMock(
        side_effect=ValueError("Page does not have this element.")
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "--page-id page-new-1" in result.stderr
    assert "--element-id el-new-1" in result.stderr
    assert "Do not run create again" in result.stderr
    assert "Page does not have this element." in result.stderr


def test_html_interface_create_write_failure_preserves_exit_code_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A write-phase failure keeps its own exception type, not a wrapping ValueError.

    HtmlValidationError is a PipefyError subclass (exit 1), unlike the plain
    ValueError case above (exit 2) -- the retry guidance must not collapse the
    two into the same exit code.
    """
    oauth_env("html-interface-create-write-fails-html-validation")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(return_value=_CREATED_HTML_INTERFACE)
    mock_client.write_html_document = AsyncMock(
        side_effect=HtmlValidationError(
            (
                HtmlViolation(
                    code="SCRIPT_FORBIDDEN",
                    message="<script> is not allowed.",
                    selector="script",
                    attribute=None,
                ),
            )
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--json",
            ],
        )
    assert result.exit_code == 1
    assert "--page-id page-new-1" in result.stderr
    assert "--element-id el-new-1" in result.stderr
    assert "- SCRIPT_FORBIDDEN at script: <script> is not allowed." in result.stderr


def test_html_interface_repos_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("html-interface-repos")
    mock_client = MagicMock()
    mock_client.list_interface_repos = AsyncMock(
        return_value=[{"uuid": EXAMPLE_PIPE_REPO_ID, "name": "Sales", "type": "Pipe"}]
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repos",
                "--organization-id",
                "123",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == {
        "repos": [{"uuid": EXAMPLE_PIPE_REPO_ID, "name": "Sales", "type": "Pipe"}]
    }
    mock_client.list_interface_repos.assert_awaited_once_with(
        "123", interface_uuid=None, repo_name=None
    )


def test_html_interface_repo_fields_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-repo-fields")
    mock_client = MagicMock()
    mock_client.get_interface_repo_fields = AsyncMock(
        return_value=[{"uuid": "field-1", "name": "Amount"}]
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repo-fields",
                "--repo-uuid",
                EXAMPLE_PIPE_REPO_ID,
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == {
        "fields": [{"uuid": "field-1", "name": "Amount"}]
    }
    mock_client.get_interface_repo_fields.assert_awaited_once_with(
        EXAMPLE_PIPE_REPO_ID, interface_uuid=None
    )


def test_html_interface_set_sources_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-set-sources")
    mock_client = MagicMock()
    mock_client.set_interface_sources = AsyncMock(
        return_value={"id": "el-1", "uuid": "el-1", "dataSources": []}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "set-sources",
                "--interface-uuid",
                "html-uuid-1",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--data-sources",
                "[]",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == {
        "id": "el-1",
        "uuid": "el-1",
        "dataSources": [],
    }
    mock_client.set_interface_sources.assert_awaited_once_with(
        "page-1", "el-1", [], interface_uuid="html-uuid-1"
    )


def test_html_interface_set_sources_rejects_invalid_source_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-set-sources-invalid")
    mock_client = MagicMock()
    mock_client.set_interface_sources = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "set-sources",
                "--interface-uuid",
                "html-uuid-1",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--data-sources",
                json.dumps([{"id": "x", "name": "X"}]),
                "--json",
            ],
        )
    assert result.exit_code == 2
    assert "repoId" in result.stderr
    mock_client.set_interface_sources.assert_not_called()


def test_html_interface_guidelines_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("html-interface-guidelines")
    mock_client = MagicMock()
    mock_client.get_interface_html_guidelines = AsyncMock(
        return_value={"allowedTags": ["div", "p"]}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app, ["portal", "html-interface", "guidelines", "--json"]
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == {"allowedTags": ["div", "p"]}
    mock_client.get_interface_html_guidelines.assert_awaited_once_with(
        include_design_system=False
    )


def test_html_interface_guidelines_include_design_system(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-guidelines-design-system")
    mock_client = MagicMock()
    mock_client.get_interface_html_guidelines = AsyncMock(
        return_value={"allowedTags": ["div"], "designSystem": {"tokens": {}}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "guidelines",
                "--include-design-system",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == {
        "allowedTags": ["div"],
        "designSystem": {"tokens": {}},
    }
    mock_client.get_interface_html_guidelines.assert_awaited_once_with(
        include_design_system=True
    )


def test_html_interface_guidelines_permission_denied_shows_guidance_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A raw PERMISSION_DENIED is re-raised as PortalPermissionError (exit 2),

    the same exit code as a denial the SDK already wraps on a write, so a
    caller scripting against this sub-app sees one exit code for a denial.
    """
    oauth_env("html-interface-guidelines-permission-denied")
    mock_client = MagicMock()
    mock_client.get_interface_html_guidelines = AsyncMock(
        side_effect=PipefyGraphQLError(
            [
                {
                    "message": "Permission denied",
                    "extensions": {"code": "PERMISSION_DENIED"},
                }
            ]
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["portal", "html-interface", "guidelines"])
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied. Request organization permissions such as "
        "`create_portal` or `manage_portals` from your admin."
    )


def test_html_interface_list_forwards_search_term(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-list-search")
    mock_client = MagicMock()
    mock_client.list_html_interfaces = AsyncMock(return_value=[])
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "list",
                "--organization-uuid",
                "org-123",
                "--search-term",
                "purchase",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.list_html_interfaces.assert_awaited_once_with(
        "org-123", search_term="purchase"
    )


def test_html_interface_list_permission_denied_shows_guidance_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A raw PERMISSION_DENIED GraphQL error becomes the standard guidance text,

    re-raised as PortalPermissionError (exit 2). list_html_interfaces never
    wraps a failure in PortalPermissionError itself (it calls
    execute_interfaces_query directly), so this is the real raw failure shape
    reaching the CLI mapping, not the SDK's own wrapping.
    """
    oauth_env("html-interface-list-permission-denied")
    mock_client = MagicMock()
    mock_client.list_html_interfaces = AsyncMock(
        side_effect=PipefyGraphQLError(
            [
                {
                    "message": "Permission denied",
                    "extensions": {"code": "PERMISSION_DENIED"},
                }
            ]
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["portal", "html-interface", "list", "--organization-uuid", "org-123"],
        )
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied. Request organization permissions such as "
        "`create_portal` or `manage_portals` from your admin."
    )


def test_html_interface_get_unknown_uuid_shows_clean_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-get-not-found")
    mock_client = MagicMock()
    mock_client.get_html_interface = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the interface"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["portal", "html-interface", "get", "html-missing"])
    assert result.exit_code == 1
    assert result.stderr.strip() == "No HTML interface has uuid 'html-missing'."


def test_html_interface_get_grid_interface_names_cli_command_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """get_html_interface's grid-interface error names pipefy portal get,

    not get_portal, the SDK/MCP method name it raises.
    """
    oauth_env("html-interface-get-grid-interface")
    mock_client = MagicMock()
    mock_client.get_html_interface = AsyncMock(
        side_effect=ValueError(
            "Interface 'grid-1' is not an HTML interface; "
            "use get_portal to read its elements."
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["portal", "html-interface", "get", "grid-1"])
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Interface 'grid-1' is not an HTML interface; "
        "use `pipefy portal get` to read its elements."
    )


def test_html_interface_set_sources_grid_interface_names_cli_command_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """set_interface_sources reads the interface first; its grid-interface

    error gets the same CLI-command rewrite as the standalone get command.
    """
    oauth_env("html-interface-set-sources-grid-interface")
    mock_client = MagicMock()
    mock_client.set_interface_sources = AsyncMock(
        side_effect=ValueError(
            "Interface 'grid-1' is not an HTML interface; "
            "use get_portal to read its elements."
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "set-sources",
                "--interface-uuid",
                "grid-1",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--data-sources",
                "[]",
            ],
        )
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Interface 'grid-1' is not an HTML interface; "
        "use `pipefy portal get` to read its elements."
    )


def test_html_interface_get_permission_denied_shows_guidance_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A raw PERMISSION_DENIED GraphQL error becomes the standard guidance text,

    re-raised as PortalPermissionError (exit 2). get_html_interface never
    wraps a failure in PortalPermissionError itself (it calls
    execute_interfaces_query directly), so this is the real raw failure shape
    reaching the CLI mapping, not the SDK's own wrapping.
    """
    oauth_env("html-interface-get-permission-denied")
    mock_client = MagicMock()
    mock_client.get_html_interface = AsyncMock(
        side_effect=PipefyGraphQLError(
            [
                {
                    "message": "Permission denied",
                    "extensions": {"code": "PERMISSION_DENIED"},
                }
            ]
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["portal", "html-interface", "get", "html-uuid-1"])
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied. Request organization permissions such as "
        "`create_portal` or `manage_portals` from your admin."
    )


def test_html_interface_write_permission_denied_shows_guidance_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """PortalPermissionError's own message is already the guidance text.

    write_html_document wraps PERMISSION_DENIED into PortalPermissionError (a
    ValueError subclass), so this stays exit 2, unlike the raw-PipefyGraphQLError
    cases elsewhere in this sub-app that map to exit 1.
    """
    oauth_env("html-interface-write-permission-denied")
    mock_client = MagicMock()
    mock_client.write_html_document = AsyncMock(
        side_effect=PortalPermissionError(
            "Permission denied. Request organization permissions such as "
            "`create_portal` or `manage_portals` from your admin."
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content",
                "<div>Hello</div>",
            ],
        )
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied. Request organization permissions such as "
        "`create_portal` or `manage_portals` from your admin."
    )


def test_html_interface_write_html_validation_error_lists_violations_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-write-validation")
    mock_client = MagicMock()
    mock_client.write_html_document = AsyncMock(
        side_effect=HtmlValidationError(
            (
                HtmlViolation(
                    code="SCRIPT_FORBIDDEN",
                    message="<script> is not allowed.",
                    selector="script",
                    attribute=None,
                ),
                HtmlViolation(
                    code="EVENT_HANDLER_FORBIDDEN",
                    message="onclick is not allowed.",
                    selector="button",
                    attribute="onclick",
                ),
            )
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content",
                "<script>bad</script>",
            ],
        )
    assert result.exit_code == 1
    assert "it has 2 violations" in result.stderr
    assert "- SCRIPT_FORBIDDEN at script: <script> is not allowed." in result.stderr
    assert (
        "- EVENT_HANDLER_FORBIDDEN at button[onclick]: onclick is not allowed."
        in result.stderr
    )


def test_html_interface_write_html_validation_error_single_violation_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """The singular ``violation`` noun is used when there is exactly one."""
    oauth_env("html-interface-write-validation-single")
    mock_client = MagicMock()
    mock_client.write_html_document = AsyncMock(
        side_effect=HtmlValidationError(
            (
                HtmlViolation(
                    code="SCRIPT_FORBIDDEN",
                    message="<script> is not allowed.",
                    selector="script",
                    attribute=None,
                ),
            )
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content",
                "<script>bad</script>",
            ],
        )
    assert result.exit_code == 1
    assert "it has 1 violation." in result.stderr
    assert "- SCRIPT_FORBIDDEN at script: <script> is not allowed." in result.stderr


def test_html_interface_write_uses_content_file(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-write-content-file")
    content_path = saved_cwd / "page.html"
    content_path.write_text("<div>from file</div>", encoding="utf-8")
    mock_client = MagicMock()
    mock_client.write_html_document = AsyncMock(return_value={"success": True})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content-file",
                str(content_path),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.write_html_document.assert_awaited_once_with(
        page_id="page-1", element_id="el-1", content="<div>from file</div>"
    )


def test_html_interface_write_rejects_non_utf8_content_file_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A read failure (bad encoding, missing file) is a clean BadParameter, not a crash."""
    oauth_env("html-interface-write-bad-encoding")
    content_path = saved_cwd / "page.html"
    content_path.write_bytes(b"\xff\xfe not valid utf-8")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content-file",
                str(content_path),
            ],
        )
    assert result.exit_code == 2
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "is not valid UTF-8 text" in _panel_text(result.stderr)
    mock_client.write_html_document.assert_not_called()


def test_html_interface_write_rejects_oversized_content_file_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A --content-file over the size cap is rejected before any read into memory."""
    oauth_env("html-interface-write-oversized-file")
    content_path = saved_cwd / "page.html"
    content_path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content-file",
                str(content_path),
            ],
        )
    assert result.exit_code == 2
    assert "exceeds 2097152 bytes" in _panel_text(result.stderr)
    mock_client.write_html_document.assert_not_called()


def test_html_interface_write_rejects_nonexistent_content_file_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A --content-file that cannot be read gets a clean message, not a traceback."""
    oauth_env("html-interface-write-nonexistent-file")
    missing_path = saved_cwd / "does-not-exist.html"
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content-file",
                str(missing_path),
            ],
        )
    assert result.exit_code == 2
    assert "No such file or directory" in result.stderr
    mock_client.write_html_document.assert_not_called()


def test_html_interface_write_rejects_content_and_content_file_together_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-write-both-content")
    content_path = saved_cwd / "page.html"
    content_path.write_text("<div>from file</div>", encoding="utf-8")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--content",
                "<div>inline</div>",
                "--content-file",
                str(content_path),
            ],
        )
    assert result.exit_code == 2
    mock_client.write_html_document.assert_not_called()


def test_html_interface_write_rejects_neither_content_nor_content_file_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-write-no-content")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "write",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
            ],
        )
    assert result.exit_code == 2
    mock_client.write_html_document.assert_not_called()


def test_html_interface_create_uses_html_file(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-html-file")
    html_path = saved_cwd / "page.html"
    html_path.write_text("<div>from file</div>", encoding="utf-8")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(return_value=_CREATED_HTML_INTERFACE)
    mock_client.write_html_document = AsyncMock(return_value={"success": True})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html-file",
                str(html_path),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.write_html_document.assert_awaited_once_with(
        page_id="page-new-1", element_id="el-new-1", content="<div>from file</div>"
    )


def test_html_interface_create_with_color(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-color")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(return_value=_CREATED_HTML_INTERFACE)
    mock_client.write_html_document = AsyncMock(return_value={"success": True})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--color",
                "purple",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.create_interface.assert_awaited_once_with(
        "org-123", "Open purchase requests", color="purple", data_sources=None
    )


def test_html_interface_create_rejects_unknown_color_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-bad-color")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--color",
                "chartreuse",
            ],
        )
    assert result.exit_code == 2
    mock_client.create_interface.assert_not_called()


def test_html_interface_create_rejects_blank_name_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-blank-name")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "   ",
                "--html",
                "<div>Hello</div>",
            ],
        )
    assert result.exit_code == 2
    mock_client.create_interface.assert_not_called()


def test_html_interface_create_rejects_blank_html_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-blank-html")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "   ",
            ],
        )
    assert result.exit_code == 2
    mock_client.create_interface.assert_not_called()


def test_html_interface_create_rejects_invalid_data_sources_exit_2_before_any_call(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A source missing repoId/fieldKeys is rejected client-side, not by a raw

    pydantic traceback surfacing from inside the SDK call.
    """
    oauth_env("html-interface-create-invalid-sources")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--data-sources",
                json.dumps([{"id": "x", "name": "X"}]),
            ],
        )
    assert result.exit_code == 2
    assert "repoId" in result.stderr
    mock_client.create_interface.assert_not_called()


def test_html_interface_create_rejects_non_array_data_sources_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A --data-sources value that parses as JSON but isn't an array is rejected."""
    oauth_env("html-interface-create-non-array-sources")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--data-sources",
                "{}",
            ],
        )
    assert result.exit_code == 2
    assert "must be a JSON array" in result.stderr
    mock_client.create_interface.assert_not_called()


def test_html_interface_create_forwards_valid_data_sources(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-valid-sources")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(return_value=_CREATED_HTML_INTERFACE)
    mock_client.write_html_document = AsyncMock(return_value={"success": True})
    sources = [
        {
            "id": "source-1",
            "name": "Purchase requests",
            "repoId": EXAMPLE_PIPE_REPO_ID,
            "fieldKeys": ["status"],
        }
    ]
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--data-sources",
                json.dumps(sources),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.create_interface.assert_awaited_once_with(
        "org-123", "Open purchase requests", color="blue", data_sources=sources
    )


def test_html_interface_create_no_page_raises_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-no-page")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(
        return_value={"id": "html-uuid-new", "uuid": "html-uuid-new", "pages": []}
    )
    mock_client.write_html_document = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
            ],
        )
    assert result.exit_code == 2
    assert "returned no page" in result.stderr
    mock_client.write_html_document.assert_not_awaited()


def test_html_interface_create_unknown_repo_id_shows_clean_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-create-unknown-repo")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the repo"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--data-sources",
                json.dumps(
                    [
                        {
                            "id": "source-1",
                            "name": "Source",
                            "repoId": "repo-missing",
                            "fieldKeys": ["status"],
                        }
                    ]
                ),
            ],
        )
    assert result.exit_code == 1
    assert result.stderr.strip() == "One of the data sources' repoId was not found."


def test_html_interface_create_source_access_denied_shows_clean_message_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A bare, code-less 'Permission denied' is the data-source-access refusal,

    distinct from the general PERMISSION_DENIED-coded portal guidance, but
    both are a permission denial and so share the same exit code (2).
    """
    oauth_env("html-interface-create-source-denied")
    mock_client = MagicMock()
    mock_client.create_interface = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Permission denied"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "create",
                "--organization-uuid",
                "org-123",
                "--name",
                "Open purchase requests",
                "--html",
                "<div>Hello</div>",
                "--data-sources",
                json.dumps(
                    [
                        {
                            "id": "source-1",
                            "name": "Source",
                            "repoId": EXAMPLE_PIPE_REPO_ID,
                            "fieldKeys": ["status"],
                        }
                    ]
                ),
            ],
        )
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied for a data source: you can bind only the pipes and "
        "tables 'portal html-interface repos' returns for this interface."
    )


def test_html_interface_repos_forwards_interface_uuid_and_repo_name(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-repos-forward")
    mock_client = MagicMock()
    mock_client.list_interface_repos = AsyncMock(return_value=[])
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repos",
                "--organization-id",
                "123",
                "--interface-uuid",
                "html-uuid-1",
                "--repo-name",
                "sales",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.list_interface_repos.assert_awaited_once_with(
        "123", interface_uuid="html-uuid-1", repo_name="sales"
    )


def test_html_interface_repos_rejects_blank_interface_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-repos-blank-interface-uuid")
    mock_client = MagicMock()
    mock_client.list_interface_repos = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repos",
                "--organization-id",
                "123",
                "--interface-uuid",
                "   ",
            ],
        )
    assert result.exit_code == 2
    mock_client.list_interface_repos.assert_not_called()


def test_html_interface_repos_unknown_org_shows_clean_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-repos-not-found")
    mock_client = MagicMock()
    mock_client.list_interface_repos = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the organization"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repos",
                "--organization-id",
                "999999",
            ],
        )
    assert result.exit_code == 1
    assert result.stderr.strip() == "No organization has id '999999'."


def test_html_interface_repos_source_access_denied_shows_clean_message_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A bare, code-less 'Permission denied' is the data-source-access refusal,

    distinct from the general PERMISSION_DENIED-coded portal guidance, but
    both are a permission denial and so share the same exit code (2).
    """
    oauth_env("html-interface-repos-source-denied")
    mock_client = MagicMock()
    mock_client.list_interface_repos = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Permission denied"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repos",
                "--organization-id",
                "123",
                "--interface-uuid",
                "html-uuid-1",
            ],
        )
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied for a data source: you can bind only the pipes and "
        "tables 'portal html-interface repos' returns for this interface."
    )


def test_html_interface_repo_fields_forwards_interface_uuid(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-repo-fields-forward")
    mock_client = MagicMock()
    mock_client.get_interface_repo_fields = AsyncMock(return_value=[])
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repo-fields",
                "--repo-uuid",
                EXAMPLE_PIPE_REPO_ID,
                "--interface-uuid",
                "html-uuid-1",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.get_interface_repo_fields.assert_awaited_once_with(
        EXAMPLE_PIPE_REPO_ID, interface_uuid="html-uuid-1"
    )


def test_html_interface_repo_fields_rejects_blank_interface_uuid_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-repo-fields-blank-interface-uuid")
    mock_client = MagicMock()
    mock_client.get_interface_repo_fields = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repo-fields",
                "--repo-uuid",
                EXAMPLE_PIPE_REPO_ID,
                "--interface-uuid",
                "   ",
            ],
        )
    assert result.exit_code == 2
    mock_client.get_interface_repo_fields.assert_not_called()


def test_html_interface_repo_fields_unknown_repo_shows_clean_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """Without --interface-uuid, the not-found message names only the repo."""
    oauth_env("html-interface-repo-fields-unknown-repo")
    mock_client = MagicMock()
    mock_client.get_interface_repo_fields = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the repo"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repo-fields",
                "--repo-uuid",
                "repo-missing",
            ],
        )
    assert result.exit_code == 1
    assert result.stderr.strip() == (
        "No repo has uuid 'repo-missing'. 'pipefy portal html-interface repos' "
        "lists the repos an interface can read."
    )


def test_html_interface_repo_fields_unknown_interface_shows_clean_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """With --interface-uuid, the not-found message names both candidates."""
    oauth_env("html-interface-repo-fields-unknown-interface")
    mock_client = MagicMock()
    mock_client.get_interface_repo_fields = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the repo"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repo-fields",
                "--repo-uuid",
                "repo-missing",
                "--interface-uuid",
                "html-missing",
            ],
        )
    assert result.exit_code == 1
    assert result.stderr.strip() == (
        "No repo has uuid 'repo-missing', or no interface has uuid "
        "'html-missing'. 'pipefy portal html-interface repos' lists the repos "
        "an interface can read."
    )


def test_html_interface_repo_fields_source_access_denied_shows_clean_message_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A bare, code-less 'Permission denied' is the data-source-access refusal,

    distinct from the general PERMISSION_DENIED-coded portal guidance, but
    both are a permission denial and so share the same exit code (2).
    """
    oauth_env("html-interface-repo-fields-source-denied")
    mock_client = MagicMock()
    mock_client.get_interface_repo_fields = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Permission denied"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "repo-fields",
                "--repo-uuid",
                EXAMPLE_PIPE_REPO_ID,
            ],
        )
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied for a data source: you can bind only the pipes and "
        "tables 'portal html-interface repos' returns for this interface."
    )


def test_html_interface_set_sources_forwards_parsed_source_attributes(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A non-empty source must reach the SDK as parsed, not as the raw dict.

    The ``[]`` case above cannot tell ``sources.root`` apart from the raw
    ``parsed`` list, since both are the same empty list.
    """
    oauth_env("html-interface-set-sources-valid")
    mock_client = MagicMock()
    mock_client.set_interface_sources = AsyncMock(
        return_value={"id": "el-1", "uuid": "el-1", "dataSources": []}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "set-sources",
                "--interface-uuid",
                "html-uuid-1",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--data-sources",
                json.dumps(
                    [
                        {
                            "id": "source-1",
                            "name": "Source",
                            "repoId": EXAMPLE_PIPE_REPO_ID,
                            "fieldKeys": ["status"],
                        }
                    ]
                ),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    mock_client.set_interface_sources.assert_awaited_once()
    sent_sources = mock_client.set_interface_sources.await_args.args[2]
    assert len(sent_sources) == 1
    assert sent_sources[0].id == "source-1"
    assert sent_sources[0].repo_id == EXAMPLE_PIPE_REPO_ID
    assert sent_sources[0].field_keys == ["status"]


def test_html_interface_set_sources_rejects_non_array_data_sources_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-set-sources-non-array")
    mock_client = MagicMock()
    mock_client.set_interface_sources = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "set-sources",
                "--interface-uuid",
                "html-uuid-1",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--data-sources",
                "{}",
            ],
        )
    assert result.exit_code == 2
    mock_client.set_interface_sources.assert_not_called()


def test_html_interface_set_sources_unknown_interface_shows_clean_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-set-sources-not-found")
    mock_client = MagicMock()
    mock_client.set_interface_sources = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the interface"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "set-sources",
                "--interface-uuid",
                "html-missing",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--data-sources",
                "[]",
            ],
        )
    assert result.exit_code == 1
    assert result.stderr.strip() == "No HTML interface has uuid 'html-missing'."


def test_html_interface_set_sources_source_access_denied_shows_clean_message_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A bare, code-less 'Permission denied' is the data-source-access refusal,

    distinct from the general PERMISSION_DENIED-coded portal guidance, but
    both are a permission denial and so share the same exit code (2). The SDK
    documents this exact shape for set_interface_sources: the caller cannot
    manage a repo that a new or widened source reads.
    """
    oauth_env("html-interface-set-sources-source-denied")
    mock_client = MagicMock()
    mock_client.set_interface_sources = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Permission denied"}])
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "portal",
                "html-interface",
                "set-sources",
                "--interface-uuid",
                "html-uuid-1",
                "--page-id",
                "page-1",
                "--element-id",
                "el-1",
                "--data-sources",
                "[]",
            ],
        )
    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Permission denied for a data source: you can bind only the pipes and "
        "tables 'portal html-interface repos' returns for this interface."
    )


_SET_ACTIONS_ARGV = [
    "portal",
    "html-interface",
    "set-actions",
    "--interface-uuid",
    "html-uuid-1",
    "--page-id",
    "page-1",
    "--element-id",
    "el-1",
]
_CLI_ACTIONS = [
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


def _invoke_set_actions(runner, mock_client, *extra: str):
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        return runner.invoke(app, [*_SET_ACTIONS_ARGV, *extra])


@pytest.mark.parametrize(
    ("flags", "editable"),
    [([], None), (["--editable"], True), (["--no-editable"], False)],
    ids=["keep editable", "set editable", "clear editable"],
)
def test_html_interface_set_actions_forwards_parsed_actions_and_editable(
    runner, clean_pipefy_env, saved_cwd, oauth_env, flags, editable
):
    """The SDK gets the parsed action models, not the raw dicts."""
    oauth_env("html-interface-set-actions")
    set_result = {
        "id": "el-1",
        "uuid": "el-1",
        "actions": _CLI_ACTIONS,
        "editable": bool(editable),
    }
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock(return_value=set_result)

    result = _invoke_set_actions(
        runner, mock_client, "--actions", json.dumps(_CLI_ACTIONS), *flags, "--json"
    )

    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    assert json.loads(result.stdout) == set_result
    mock_client.set_interface_actions.assert_awaited_once_with(
        "page-1",
        "el-1",
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


@pytest.mark.parametrize(
    ("actions", "fragment"),
    [
        ("{}", "JSON array"),
        (json.dumps([{**_CLI_ACTIONS[0], "kind": "openUrl"}]), "openUrl"),
        (
            json.dumps([_CLI_ACTIONS[0], {**_CLI_ACTIONS[1], "actionId": "details"}]),
            "own actionId",
        ),
    ],
    ids=["not an array", "unknown kind", "repeated action id"],
)
def test_html_interface_set_actions_rejects_invalid_actions_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env, actions, fragment
):
    oauth_env("html-interface-set-actions-invalid")
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock()

    result = _invoke_set_actions(runner, mock_client, "--actions", actions)

    assert result.exit_code == 2
    assert fragment in result.stderr
    mock_client.set_interface_actions.assert_not_called()


def test_html_interface_set_actions_unknown_reference_shows_sdk_message_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """A sourceId the element lacks is bad input: the SDK message, exit 2."""
    oauth_env("html-interface-set-actions-unknown-source")
    message = (
        "actions[0].sourceId: 'closed-requests' is not a data source of this "
        "element; its sources are: open-requests"
    )
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock(side_effect=ValueError(message))

    result = _invoke_set_actions(runner, mock_client, "--actions", "[]")

    assert result.exit_code == 2
    assert result.stderr.strip() == message


def test_html_interface_set_actions_grid_interface_names_cli_command_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-set-actions-grid-interface")
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock(
        side_effect=ValueError(
            "Interface 'html-uuid-1' is not an HTML interface; "
            "use get_portal to read its elements."
        )
    )

    result = _invoke_set_actions(runner, mock_client, "--actions", "[]")

    assert result.exit_code == 2
    assert result.stderr.strip() == (
        "Interface 'html-uuid-1' is not an HTML interface; "
        "use `pipefy portal get` to read its elements."
    )


def test_html_interface_set_actions_unknown_interface_shows_clean_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("html-interface-set-actions-not-found")
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": "Couldn't find the interface"}])
    )

    result = _invoke_set_actions(runner, mock_client, "--actions", "[]")

    assert result.exit_code == 1
    assert result.stderr.strip() == "No HTML interface has uuid 'html-uuid-1'."


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            PipefyGraphQLError([{"message": "Permission denied"}]),
            "Permission denied for a data source of this element: you can set "
            "its actions only when you can bind every pipe and table its "
            "sources read, as 'portal html-interface repos' returns them for "
            "this interface.",
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
            "Permission denied. Request organization permissions such as "
            "`create_portal` or `manage_portals` from your admin.",
        ),
    ],
    ids=["source repo refused", "interface refused"],
)
def test_html_interface_set_actions_permission_denied_shows_guidance_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env, error, message
):
    """Both refusals are a permission denial, so they share exit code 2."""
    oauth_env("html-interface-set-actions-denied")
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock(side_effect=error)

    result = _invoke_set_actions(runner, mock_client, "--actions", "[]")

    assert result.exit_code == 2
    assert result.stderr.strip() == message


def test_html_interface_set_actions_api_refusal_passes_its_message_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    """An action the API refuses keeps the API's own text and exit code."""
    oauth_env("html-interface-set-actions-api-refusal")
    message = (
        "Action approve lists automationIds that are not manually triggered "
        "automations of its source's repo: 9"
    )
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock(
        side_effect=PipefyGraphQLError([{"message": message}])
    )

    result = _invoke_set_actions(runner, mock_client, "--actions", "[]")

    assert result.exit_code == 1
    assert message in result.stderr


@pytest.mark.parametrize("option", ["--interface-uuid", "--page-id", "--element-id"])
def test_html_interface_set_actions_rejects_blank_id_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env, option
):
    oauth_env("html-interface-set-actions-blank-id")
    mock_client = MagicMock()
    mock_client.set_interface_actions = AsyncMock()
    argv = list(_SET_ACTIONS_ARGV)
    argv[argv.index(option) + 1] = "   "

    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, [*argv, "--actions", "[]"])

    assert result.exit_code == 2
    mock_client.set_interface_actions.assert_not_called()
