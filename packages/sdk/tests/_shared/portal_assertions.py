"""Assertions for restoring the complete state after live portal cleanup."""

from __future__ import annotations

import asyncio
import hashlib
import json

_CLEANUP_READS = 3
_CLEANUP_READ_DELAY_SECONDS = 0.5


def _portal_fingerprint(portal):
    encoded = json.dumps(portal, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


async def assert_portal_restored(service, original):
    """Require the complete original content within three post-cleanup reads."""
    expected = _portal_fingerprint(original)
    observed = []
    for attempt in range(_CLEANUP_READS):
        after = await service.get_portal(original["uuid"])
        observed.append(_portal_fingerprint(after))
        if observed[-1] == expected:
            return
        if attempt < _CLEANUP_READS - 1:
            await asyncio.sleep(_CLEANUP_READ_DELAY_SECONDS)
    raise AssertionError(
        f"Portal cleanup did not restore the complete baseline after {_CLEANUP_READS} reads: "
        f"expected_sha256={expected}; observed_sha256={','.join(observed)}"
    )
