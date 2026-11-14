"""``PipefyClient.set_phase_move_targets`` against a fake that keeps phase state."""

import pytest
from _shared.mock_clients import mock_executor

from pipefy_sdk import PipefyAPIError, PipefyGraphQLError
from pipefy_sdk.client import Executors, PipefyClient
from pipefy_sdk.settings import PipefySettings


class _PhaseConnectionsApi:
    """Executor stand-in that stores one phase the way the Pipefy API does.

    ``updatePhase`` writes the name it receives, so a client that sends a stale
    name restores it. ``updatePhaseJumps`` writes only the connections.
    """

    def __init__(self, *, name="Review", targets=("20",)):
        self.name = name
        self.targets = list(targets)
        self.operations = []
        self.after_first_read = None

    def respond(self, request, variables):
        field = request.document.definitions[0].selection_set.selections[0].name.value
        self.operations.append(field)
        if field == "phase":
            payload = {"phase": self._phase()}
            if self.after_first_read is not None:
                hook, self.after_first_read = self.after_first_read, None
                hook(self)
            return payload
        if field == "updatePhase":
            self.name = variables["input"]["name"]
            if "jumpTargetIds" in variables["input"]:
                self.targets = list(variables["input"]["jumpTargetIds"])
            return {"updatePhase": {"phase": self._phase()}}
        if field == "updatePhaseJumps":
            self.targets = list(variables["input"]["targetPhaseIds"])
            return {"updatePhaseJumps": {"success": True}}
        raise AssertionError(f"unexpected operation: {field}")

    def _phase(self):
        rows = [{"id": t, "name": f"Phase {t}"} for t in self.targets]
        return {
            "id": "10",
            "name": self.name,
            "cards_can_be_moved_to_phases": rows or None,
        }


def _client(executor):
    return PipefyClient.from_executors(
        Executors(public=executor, interfaces=executor, internal=executor),
        settings=PipefySettings(base_url="https://api.pipefy.com"),
    )


def _connect(api):
    executor = mock_executor(side_effect=api.respond)
    return _client(executor), executor


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_keeps_current_connections_and_returns_the_saved_list():
    api = _PhaseConnectionsApi(targets=("20",))
    client, _ = _connect(api)

    result = await client.set_phase_move_targets("10", ["30"])

    assert api.targets == ["20", "30"]
    assert result == await client.get_phase_allowed_move_targets("10")
    assert [row["id"] for row in result["phase"]["cards_can_be_moved_to_phases"]] == [
        "20",
        "30",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_of_a_phase_that_is_already_connected_keeps_the_list():
    api = _PhaseConnectionsApi(targets=("20", "30"))
    client, _ = _connect(api)

    await client.set_phase_move_targets("10", ["30"])

    assert api.targets == ["20", "30"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replace_writes_only_the_given_targets_without_a_first_read():
    api = _PhaseConnectionsApi(targets=("20",))
    client, _ = _connect(api)

    await client.set_phase_move_targets("10", ["40", "30"], replace=True)

    assert api.targets == ["40", "30"]
    assert api.operations == ["updatePhaseJumps", "phase"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replace_with_an_empty_list_removes_every_connection():
    api = _PhaseConnectionsApi(targets=("20", "30"))
    client, _ = _connect(api)

    result = await client.set_phase_move_targets("10", [], replace=True)

    assert api.targets == []
    assert result["phase"]["cards_can_be_moved_to_phases"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_one_item_list_is_one_phase_id():
    api = _PhaseConnectionsApi(targets=())
    client, _ = _connect(api)

    await client.set_phase_move_targets("10", ["123"])

    assert api.targets == ["123"]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("scalar", ["", "123", b"123"])
@pytest.mark.parametrize("replace", [False, True])
async def test_a_string_or_bytes_never_reaches_the_api(scalar, replace):
    api = _PhaseConnectionsApi(targets=("20",))
    client, executor = _connect(api)

    with pytest.raises(ValueError, match="must be a list of phase ids"):
        await client.set_phase_move_targets("10", scalar, replace=replace)

    executor.execute_query.assert_not_called()
    assert api.targets == ["20"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_an_empty_list_without_replace_never_reaches_the_api():
    api = _PhaseConnectionsApi(targets=("20",))
    client, executor = _connect(api)

    with pytest.raises(ValueError, match="target_phase_ids is empty"):
        await client.set_phase_move_targets("10", [])

    executor.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_does_not_restore_a_name_changed_after_its_read():
    api = _PhaseConnectionsApi(name="Review", targets=("20",))
    api.after_first_read = lambda phase: setattr(phase, "name", "Renamed")
    client, _ = _connect(api)

    result = await client.set_phase_move_targets("10", ["30"])

    assert api.name == "Renamed"
    assert result["phase"]["name"] == "Renamed"
    assert api.targets == ["20", "30"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_on_a_phase_the_read_does_not_return_writes_nothing():
    executor = mock_executor({"phase": None})

    with pytest.raises(ValueError, match="Phase 10 not found or access denied"):
        await _client(executor).set_phase_move_targets("10", ["30"])

    assert executor.execute_query.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_rejected_write_raises_and_skips_the_read_back():
    rejected = PipefyGraphQLError(
        [{"message": "Invalid input", "extensions": {"code": "INVALID_INPUT"}}]
    )
    executor = mock_executor(side_effect=[rejected])

    with pytest.raises(PipefyGraphQLError):
        await _client(executor).set_phase_move_targets("10", ["30"], replace=True)

    assert executor.execute_query.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_write_that_returns_success_false_raises():
    executor = mock_executor(side_effect=[{"updatePhaseJumps": {"success": False}}])

    with pytest.raises(PipefyAPIError, match="success=false for phase_id='10'"):
        await _client(executor).set_phase_move_targets("10", ["30"], replace=True)

    assert executor.execute_query.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_read_back_with_no_phase_raises():
    executor = mock_executor(
        side_effect=[{"updatePhaseJumps": {"success": True}}, {"phase": None}]
    )

    with pytest.raises(PipefyAPIError, match="read-back returned no phase"):
        await _client(executor).set_phase_move_targets("10", ["30"], replace=True)
