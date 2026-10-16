"""Complete portal cleanup must converge within a fixed read budget."""

from __future__ import annotations

from copy import deepcopy

import pytest
from _shared.mock_clients import mock_executor
from _shared.portal_assertions import assert_portal_restored

from pipefy_sdk.services.portal_service import PortalService

_PORTAL = {
    "id": "portal-fixture",
    "uuid": "portal-fixture",
    "name": "Portal fixture",
    "published": True,
    "pages": [
        {
            "id": "page-first",
            "uuid": "page-first",
            "title": "Home",
            "layout": [{"id": "row-one", "children": ["element-one", "element-two"]}],
            "elements": [
                {
                    "id": "element-one",
                    "uuid": "element-one",
                    "metadata": {"name": "Original"},
                },
                {"id": "element-two", "uuid": "element-two", "metadata": {}},
            ],
        },
        {
            "id": "page-second",
            "uuid": "page-second",
            "title": "Help",
            "layout": [],
            "elements": [],
        },
    ],
    "subPortals": [
        {"id": "sub-one", "uuid": "sub-one", "published": False},
        {"id": "sub-two", "uuid": "sub-two", "published": True},
    ],
}


def _service(*responses):
    executor = mock_executor(
        side_effect=[
            value if isinstance(value, Exception) else {"portalInterface": value}
            for value in responses
        ]
    )
    service = PortalService(
        public_executor=mock_executor(),
        interfaces_executor=executor,
        internal_executor=mock_executor(),
    )
    return service, executor


@pytest.mark.asyncio
@pytest.mark.parametrize("stale_reads", [0, 1, 2])
async def test_portal_cleanup_accepts_exact_baseline_within_read_budget(stale_reads):
    stale = deepcopy(_PORTAL)
    stale["pages"].append({"id": "owned-page", "uuid": "owned-page", "elements": []})
    service, executor = _service(*([stale] * stale_reads), _PORTAL)

    await assert_portal_restored(service, _PORTAL)

    assert executor.execute_query.await_count == stale_reads + 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change", ["metadata", "pages", "elements", "layout", "sub_portals"]
)
async def test_portal_cleanup_rejects_persistent_content_or_order_change(change):
    changed = deepcopy(_PORTAL)
    if change == "metadata":
        changed["pages"][0]["elements"][0]["metadata"]["name"] = (
            "Changed private content"
        )
    elif change == "pages":
        changed["pages"].reverse()
    elif change == "elements":
        changed["pages"][0]["elements"].reverse()
    elif change == "layout":
        changed["pages"][0]["layout"][0]["children"].reverse()
    else:
        changed["subPortals"].reverse()
    service, executor = _service(changed, changed, changed)

    with pytest.raises(AssertionError, match="after 3 reads") as failure:
        await assert_portal_restored(service, _PORTAL)

    assert executor.execute_query.await_count == 3
    assert "expected_sha256=" in str(failure.value)
    assert "observed_sha256=" in str(failure.value)
    assert "Changed private content" not in str(failure.value)


@pytest.mark.asyncio
async def test_portal_cleanup_propagates_read_failure_without_retry():
    service, executor = _service(RuntimeError("Read failed"))

    with pytest.raises(RuntimeError, match="Read failed"):
        await assert_portal_restored(service, _PORTAL)

    assert executor.execute_query.await_count == 1
