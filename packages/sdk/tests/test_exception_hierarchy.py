"""The SDK error hierarchy consumers catch against.

``PipefyError`` is the documented root, so ``except PipefyError`` has to catch
the failures the SDK actually raises. It did not: ``PipefyGraphQLError``, the
type every GraphQL failure arrives as, subclassed ``Exception`` directly, so the
root caught nothing a caller would ever see.

Nothing else pins the parentage. The CLI tests covering the same failures catch
``PipefyGraphQLError`` by name, so they stay green whichever base it has.

The contract spans ``exceptions`` and ``graphql_executor``, so it lives here
rather than in either module's tests. Types come off the package rather than
their defining modules because the public import is what consumers catch
against.
"""

from __future__ import annotations

from pipefy_sdk import (
    PipefyAPIError,
    PipefyError,
    PipefyGraphQLError,
    PipefyRequestTimeoutError,
)


def test_api_error_is_rooted() -> None:
    assert issubclass(PipefyAPIError, PipefyError)


def test_graphql_error_is_an_api_error() -> None:
    """A GraphQL ``errors`` payload is the API reporting a failure."""
    assert issubclass(PipefyGraphQLError, PipefyAPIError)


def test_graphql_error_is_catchable_as_the_root() -> None:
    assert issubclass(PipefyGraphQLError, PipefyError)


def test_raised_graphql_error_is_caught_by_the_root() -> None:
    """The parentage holds for an instance, not only for the classes."""
    try:
        raise PipefyGraphQLError([{"message": "denied"}])
    except PipefyError as exc:
        assert isinstance(exc, PipefyGraphQLError)
        assert exc.errors == [{"message": "denied"}]
    else:  # pragma: no cover - the raise above always fires
        raise AssertionError("PipefyGraphQLError escaped except PipefyError")


def test_request_timeout_is_catchable_as_the_root() -> None:
    assert issubclass(PipefyRequestTimeoutError, PipefyError)


def test_request_timeout_is_still_a_timeout_error() -> None:
    """Back-compat: a timed-out request stays catchable as ``TimeoutError``."""
    assert issubclass(PipefyRequestTimeoutError, TimeoutError)


def test_request_timeout_message_warns_the_write_may_have_applied() -> None:
    """The message tells the caller a timed-out write can still have committed.

    The server does not abort a mutation when the client stops waiting, so the
    message must steer the caller to read state back rather than blindly retry.
    """
    message = str(PipefyRequestTimeoutError(30))
    lowered = message.lower()
    assert "mutation" in lowered
    assert "read the state back" in lowered


def test_raised_request_timeout_is_caught_by_both_contracts() -> None:
    """One instance satisfies both ``except PipefyError`` and ``except TimeoutError``."""
    caught_as_root = False
    try:
        raise PipefyRequestTimeoutError(30)
    except PipefyError as exc:
        caught_as_root = True
        assert isinstance(exc, TimeoutError)
        assert exc.timeout_seconds == 30
        assert str(exc).strip()
        assert "30" in str(exc)
    assert caught_as_root

    try:
        raise PipefyRequestTimeoutError(30)
    except TimeoutError as exc:
        assert isinstance(exc, PipefyError)
    else:  # pragma: no cover - the raise above always fires
        raise AssertionError("PipefyRequestTimeoutError escaped except TimeoutError")
