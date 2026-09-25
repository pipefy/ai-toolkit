"""Tests for ``pipefy_sdk.member_removal.verify_member_removal``."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from _shared.fixture_ids import (
    EXAMPLE_FIELD_INTERNAL_ID,
    EXAMPLE_FIELD_INTERNAL_ID_2,
    EXAMPLE_ORG_UUID,
    EXAMPLE_OTHER_ORG_UUID,
    EXAMPLE_PIPE_ID,
)

from pipefy_sdk.member_removal import verify_member_removal

_STILL_PRESENT_WARNING = (
    "API returned success but member(s) [{ids}] are still present in the pipe. "
    "They may have org-level permissions that override pipe-level removal."
)


def _client(*, members=None, side_effect=None):
    client = MagicMock()
    client.get_pipe_members = AsyncMock(
        return_value={"pipe": {"members": members or []}},
        side_effect=side_effect,
    )
    return client


@pytest.mark.anyio
async def test_verify_member_removal_returns_none_when_requested_ids_are_gone():
    client = _client(
        members=[
            {
                "user": {
                    "id": EXAMPLE_FIELD_INTERNAL_ID_2,
                    "uuid": EXAMPLE_OTHER_ORG_UUID,
                    "name": "Other",
                    "email": "other@x.com",
                },
                "role_name": "member",
            },
        ]
    )

    warning = await verify_member_removal(client, EXAMPLE_PIPE_ID, ["user-1", "user-2"])

    assert warning is None
    client.get_pipe_members.assert_awaited_once_with(EXAMPLE_PIPE_ID)


@pytest.mark.anyio
async def test_verify_member_removal_warns_with_sorted_ids_when_one_remains():
    client = _client(
        members=[
            {
                "user": {
                    "id": EXAMPLE_FIELD_INTERNAL_ID,
                    "uuid": EXAMPLE_ORG_UUID,
                    "name": "User",
                    "email": "user@x.com",
                },
                "role_name": "admin",
            },
            {
                "user": {
                    "id": EXAMPLE_FIELD_INTERNAL_ID_2,
                    "uuid": EXAMPLE_OTHER_ORG_UUID,
                    "name": "Other",
                    "email": "other@x.com",
                },
                "role_name": "member",
            },
        ]
    )

    warning = await verify_member_removal(
        client, EXAMPLE_PIPE_ID, [EXAMPLE_FIELD_INTERNAL_ID]
    )

    assert warning == _STILL_PRESENT_WARNING.format(ids=EXAMPLE_FIELD_INTERNAL_ID)


@pytest.mark.anyio
async def test_verify_member_removal_warns_when_requested_uuid_remains():
    client = _client(
        members=[
            {
                "user": {
                    "id": EXAMPLE_FIELD_INTERNAL_ID,
                    "uuid": EXAMPLE_ORG_UUID,
                    "name": "User",
                    "email": "user@x.com",
                },
                "role_name": "admin",
            },
        ]
    )

    warning = await verify_member_removal(client, EXAMPLE_PIPE_ID, [EXAMPLE_ORG_UUID])

    assert warning == _STILL_PRESENT_WARNING.format(ids=EXAMPLE_ORG_UUID)


@pytest.mark.anyio
async def test_verify_member_removal_names_several_remaining_ids_sorted():
    client = _client(
        members=[
            {
                "user": {
                    "id": EXAMPLE_FIELD_INTERNAL_ID,
                    "uuid": EXAMPLE_ORG_UUID,
                    "name": "User",
                    "email": "user@x.com",
                },
                "role_name": "admin",
            },
            {
                "user": {
                    "id": EXAMPLE_FIELD_INTERNAL_ID_2,
                    "uuid": EXAMPLE_OTHER_ORG_UUID,
                    "name": "Other",
                    "email": "other@x.com",
                },
                "role_name": "member",
            },
        ]
    )

    warning = await verify_member_removal(
        client,
        EXAMPLE_PIPE_ID,
        [EXAMPLE_FIELD_INTERNAL_ID_2, EXAMPLE_FIELD_INTERNAL_ID],
    )

    assert warning == _STILL_PRESENT_WARNING.format(
        ids=f"{EXAMPLE_FIELD_INTERNAL_ID}, {EXAMPLE_FIELD_INTERNAL_ID_2}"
    )


@pytest.mark.anyio
async def test_verify_member_removal_returns_none_when_pipe_id_is_not_numeric():
    client = _client()

    warning = await verify_member_removal(client, "pipe-1", ["user-1"])

    assert warning is None
    client.get_pipe_members.assert_not_awaited()


@pytest.mark.anyio
async def test_verify_member_removal_returns_none_when_get_pipe_members_raises():
    client = _client(side_effect=Exception("network error"))

    warning = await verify_member_removal(client, EXAMPLE_PIPE_ID, ["user-1"])

    assert warning is None
