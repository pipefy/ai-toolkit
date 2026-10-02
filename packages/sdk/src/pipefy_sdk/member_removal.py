"""Read-back after pipe member removal: warn when a user is still present."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from pipefy_sdk.client import PipefyClient


class MemberRemovalResult(TypedDict):
    data: dict[str, Any]
    warning: str | None


async def verify_member_removal(
    client: PipefyClient,
    pipe_id: str,
    user_ids: list[str],
) -> str | None:
    """Return a warning when requested users remain on the pipe after removal.

    Returns ``None`` when every requested id or uuid is gone, when ``pipe_id``
    is not numeric (the members read needs a numeric id), or when
    ``get_pipe_members`` raises.
    """
    pipe_id_str = str(pipe_id).strip()
    if not pipe_id_str.isdigit():
        return None

    try:
        members_data = await client.get_pipe_members(pipe_id_str)
    except Exception:  # noqa: BLE001
        return None

    members = (members_data.get("pipe") or {}).get("members") or []
    remaining_ids: set[str] = set()
    for member in members:
        user = member.get("user") if isinstance(member.get("user"), dict) else {}
        if user.get("id"):
            remaining_ids.add(str(user["id"]))
        if user.get("uuid"):
            remaining_ids.add(str(user["uuid"]))

    requested = {str(uid) for uid in user_ids}
    still_present = requested & remaining_ids
    if not still_present:
        return None

    ids_str = ", ".join(sorted(still_present))
    return (
        f"API returned success but member(s) [{ids_str}] are still present in the pipe. "
        "They may have org-level permissions that override pipe-level removal."
    )
