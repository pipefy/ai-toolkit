"""Run one read with a time limit, and tell a passed limit apart from other timeouts."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

_T = TypeVar("_T")


class ReadDeadlinePassed(Exception):
    """The read was still running when its own limit passed, so the helper cancelled it."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        super().__init__(f"The read did not end within {seconds} s.")


class ReadBeforeDeadline(Protocol):
    """Starts ``start()`` and returns its result, or raises :class:`ReadDeadlinePassed`."""

    def __call__(
        self, start: Callable[[], Awaitable[_T]], seconds: float
    ) -> Awaitable[_T]: ...


async def await_before_deadline(
    start: Callable[[], Awaitable[_T]], seconds: float
) -> _T:
    """Return ``await start()``, or raise :class:`ReadDeadlinePassed` after ``seconds``.

    Only this limit becomes :class:`ReadDeadlinePassed`. A ``TimeoutError`` that the
    read raises itself, such as ``PipefyRequestTimeoutError``, and a cancel from the
    caller propagate unchanged.
    """
    scope = asyncio.timeout(seconds)
    try:
        async with scope:
            return await start()
    except TimeoutError:
        if scope.expired():
            raise ReadDeadlinePassed(seconds) from None
        raise


__all__ = ["ReadBeforeDeadline", "ReadDeadlinePassed", "await_before_deadline"]
