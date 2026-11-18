import asyncio

import pytest

from pipefy_sdk import PipefyRequestTimeoutError
from pipefy_sdk.read_deadline import ReadDeadlinePassed, await_before_deadline


async def _value():
    return "row"


@pytest.mark.unit
async def test_returns_the_result_of_a_call_that_ends_in_time():
    assert await await_before_deadline(_value, 5) == "row"


@pytest.mark.unit
async def test_a_call_still_pending_at_the_deadline_raises_deadline_passed():
    with pytest.raises(ReadDeadlinePassed):
        await await_before_deadline(lambda: asyncio.Event().wait(), 0)


@pytest.mark.unit
async def test_a_timeout_raised_by_the_call_itself_propagates():
    async def transport_timeout():
        raise PipefyRequestTimeoutError(30)

    with pytest.raises(PipefyRequestTimeoutError):
        await await_before_deadline(transport_timeout, 5)


@pytest.mark.unit
async def test_a_cancel_from_the_caller_propagates():
    started = asyncio.Event()

    async def pending():
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(await_before_deadline(pending, 30))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
