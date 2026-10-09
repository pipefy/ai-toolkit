"""Live portal scenarios with disposable pages, elements, and sub-portals.

Set live credentials and ``PIPEFY_PORTAL_ORG_UUID`` for a dedicated test
organization with an existing main portal and portal-management access.
The fixtures remove owned resources and compare the original portal content.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from _shared.live_settings import (
    live_pipefy_settings,
    live_resolved_auth,
    require_live_creds,
)
from _shared.portal_assertions import assert_portal_restored

from pipefy_sdk.client import build_executors
from pipefy_sdk.services.portal_service import PortalService


@pytest.fixture
def live_portal_service():
    require_live_creds()
    ex = build_executors(live_pipefy_settings(), live_resolved_auth())
    return PortalService(
        public_executor=ex.public,
        interfaces_executor=ex.interfaces,
        internal_executor=ex.internal,
    )


def _require_portal_org_uuid():
    org_uuid = os.environ.get("PIPEFY_PORTAL_ORG_UUID", "").strip()
    if not org_uuid:
        pytest.skip("Set PIPEFY_PORTAL_ORG_UUID to a dedicated test organization.")
    return org_uuid


def _portal_element(portal, element_id):
    return next(
        (
            element
            for page in portal.get("pages") or []
            for element in page.get("elements") or []
            if element["uuid"] == element_id
        ),
        None,
    )


def _sub_portal_published(portal, sub_portal_uuid):
    return next(
        (
            sub_portal.get("published")
            for sub_portal in portal.get("subPortals") or []
            if sub_portal["uuid"] == sub_portal_uuid
        ),
        None,
    )


@pytest_asyncio.fixture
async def live_main_portal(live_portal_service):
    portals = await live_portal_service.list_portals(_require_portal_org_uuid())
    if not portals:
        pytest.skip("The test organization needs an existing main portal.")
    return await live_portal_service.get_portal(portals[0]["uuid"])


@pytest_asyncio.fixture
async def live_portal_page(live_portal_service, live_main_portal):
    portal_uuid = live_main_portal["uuid"]
    title = f"[smoke:{uuid.uuid4().hex}:sdk-portal-page]"
    page = await live_portal_service.create_portal_page(portal_uuid, title)
    page_id = page["uuid"]
    try:
        yield page
    finally:
        result = await live_portal_service.delete_portal_page(portal_uuid, page_id)
        assert result.get("deletePage", {}).get("success") is True
        await assert_portal_restored(live_portal_service, live_main_portal)


@pytest_asyncio.fixture
async def live_first_page_forms_element(live_portal_service, live_main_portal):
    pages = live_main_portal.get("pages") or []
    if not pages:
        pytest.skip("The main portal needs a first page for sub-portal publication.")
    portal_uuid = live_main_portal["uuid"]
    page_id = pages[0]["uuid"]
    element_id = str(uuid.uuid4())
    try:
        element = await live_portal_service.create_portal_element(
            page_id,
            type="forms",
            element_id=element_id,
            metadata={
                "name": f"[smoke:{uuid.uuid4().hex}:sdk-publish-slot]",
                "gridMap": {"height": 66, "columns": 4, "minColumns": 4},
            },
        )
        assert element["uuid"] == element_id
        yield {"element_id": element_id, "page_id": page_id}
    finally:
        current = await live_portal_service.get_portal(portal_uuid)
        if _portal_element(current, element_id) is not None:
            result = await live_portal_service.delete_portal_element(
                element_id, page_id
            )
            assert result.get("deleteElement", {}).get("success") is True
        await assert_portal_restored(live_portal_service, live_main_portal)


@pytest_asyncio.fixture
async def live_sub_portal(
    live_portal_service, live_main_portal, live_first_page_forms_element
):
    # This dependency keeps element cleanup after sub-portal cleanup.
    portal_uuid = live_main_portal["uuid"]
    name = f"[smoke:{uuid.uuid4().hex}:sdk-sub-portal]"
    sub_portal = await live_portal_service.create_sub_portal(portal_uuid, name)
    sub_portal_uuid = sub_portal["uuid"]
    try:
        yield sub_portal_uuid
    finally:
        result = await live_portal_service.delete_sub_portal(sub_portal_uuid)
        assert result.get("deleteSubPortalInterface", {}).get("success") is True
        after = await live_portal_service.get_portal(portal_uuid)
        assert _sub_portal_published(after, sub_portal_uuid) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_list_portals_returns_list_shape(live_portal_service):
    portals = await live_portal_service.list_portals(_require_portal_org_uuid())

    assert isinstance(portals, list)
    if portals:
        assert "uuid" in portals[0]
        assert "name" in portals[0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_get_portal_round_trip_from_list(
    live_portal_service, live_main_portal
):
    detail = await live_portal_service.get_portal(live_main_portal["uuid"])

    assert detail["uuid"] == live_main_portal["uuid"]
    assert "published" in detail
    assert "pages" in detail


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_create_portal_idempotent_returns_same_uuid(
    live_portal_service, live_main_portal
):
    org_uuid = _require_portal_org_uuid()
    first = await live_portal_service.create_portal(org_uuid)
    second = await live_portal_service.create_portal(org_uuid)

    assert first["uuid"] == second["uuid"] == live_main_portal["uuid"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_update_portal_page_layout_on_bootstrapped_page(
    live_portal_service, live_portal_page
):
    layout = [
        {"id": str(uuid.uuid4()), "type": "row", "children": [element["uuid"]]}
        for element in live_portal_page.get("elements") or []
    ]
    result = await live_portal_service.update_portal_page_layout(
        live_portal_page["uuid"], layout
    )

    assert result.get("updatePageLayout", {}).get("success") is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_update_portal_element_on_bootstrapped_page(
    live_portal_service, live_portal_page, live_main_portal
):
    link = next(
        (e for e in live_portal_page.get("elements") or [] if e.get("type") == "link"),
        None,
    )
    if link is None:
        pytest.skip("Bootstrapped page has no link element to update.")
    metadata = {
        "gridMap": {"height": 64, "columns": 4, "minColumns": 4},
        "linkName": "SDK integration updated link",
    }
    updated = await live_portal_service.update_portal_element(
        link["uuid"], live_portal_page["uuid"], type="link", metadata=metadata
    )

    assert updated["uuid"] == link["uuid"]
    after = await live_portal_service.get_portal(live_main_portal["uuid"])
    stored = _portal_element(after, link["uuid"])
    assert stored["metadata"]["linkName"] == metadata["linkName"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_create_portal_element_on_bootstrapped_page(
    live_portal_service, live_portal_page, live_main_portal
):
    metadata = {
        "gridMap": {"height": 64, "columns": 4, "minColumns": 4},
        "linkUrl": "https://pipefy.com",
        "linkName": "Pipefy SDK smoke",
    }
    element = await live_portal_service.create_portal_element(
        live_portal_page["uuid"], type="link", metadata=metadata
    )
    element_id = element["uuid"]
    assert element_id
    assert element.get("type") == "link"

    result = await live_portal_service.delete_portal_element(
        element_id, live_portal_page["uuid"]
    )
    assert result.get("deleteElement", {}).get("success") is True
    after = await live_portal_service.get_portal(live_main_portal["uuid"])
    assert _portal_element(after, element_id) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_publish_sub_portal_cycle(
    live_portal_service,
    live_main_portal,
    live_first_page_forms_element,
    live_sub_portal,
):
    portal_uuid = live_main_portal["uuid"]
    element_id = live_first_page_forms_element["element_id"]
    result = await live_portal_service.publish_sub_portal(
        portal_uuid, element_id, live_sub_portal
    )
    assert result.get("updateSubPortalElement", {}).get("success") is True

    after_publish = await live_portal_service.get_portal(portal_uuid)
    published_after_attach = _sub_portal_published(after_publish, live_sub_portal)
    assert published_after_attach is True
    stored = _portal_element(after_publish, element_id)
    assert stored["metadata"]["subPortalUuid"] == live_sub_portal

    result = await live_portal_service.unpublish_sub_portal(portal_uuid, element_id)
    assert result.get("updateSubPortalElement", {}).get("success") is True

    after_unpublish = await live_portal_service.get_portal(portal_uuid)
    published_after_detach = _sub_portal_published(after_unpublish, live_sub_portal)
    assert published_after_detach is False
    stored = _portal_element(after_unpublish, element_id)
    assert stored["metadata"].get("subPortalUuid") is None
