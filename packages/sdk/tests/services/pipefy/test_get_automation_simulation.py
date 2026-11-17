import pytest
from _shared.mock_clients import mock_executor

from pipefy_sdk.queries.automation_queries import AUTOMATION_SIMULATION_QUERY
from pipefy_sdk.services.automation_service import AutomationService


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def _read(status, result=None):
    return {
        "automationSimulation": {
            "status": status,
            "details": None,
            "simulationResult": result,
        }
    }


def _service(executor, clock):
    return AutomationService(executor=executor, sleep=clock.sleep, clock=clock)


@pytest.mark.unit
async def test_reads_until_the_simulation_leaves_processing():
    clock = FakeClock()
    final = {"101": {"label": "Reply", "type": "long_text", "value": "Hi [Your Name]"}}
    executor = mock_executor(
        side_effect=[_read("processing"), _read("processing"), _read("success", final)]
    )

    result = await _service(executor, clock).get_automation_simulation(
        "sim-1", field_ids=["101", "102"]
    )

    assert executor.execute_query.await_count == 3
    query, variables = executor.execute_query.call_args_list[0][0]
    assert query is AUTOMATION_SIMULATION_QUERY
    assert variables == {"simulationId": "sim-1"}
    assert clock.sleeps == [2.0, 2.0]
    assert result == {
        "simulation_id": "sim-1",
        "automation_simulation": {
            "status": "success",
            "details": None,
            "simulationResult": final,
        },
        "warnings": [
            {"field_id": "101", "kind": "placeholder", "text": "[Your Name]"},
            {"field_id": "102", "kind": "empty", "text": ""},
        ],
        "waited_seconds": 4.0,
    }


@pytest.mark.unit
async def test_returns_processing_when_the_limit_passes():
    clock = FakeClock()
    executor = mock_executor(side_effect=[_read("processing")] * 4)

    result = await _service(executor, clock).get_automation_simulation(
        "sim-2", timeout_seconds=5
    )

    assert clock.sleeps == [2.0, 2.0, 1.0]
    assert executor.execute_query.await_count == 4
    assert result["automation_simulation"]["status"] == "processing"
    assert result["warnings"] == []
    assert result["waited_seconds"] == 5.0


@pytest.mark.unit
async def test_zero_timeout_reads_once():
    clock = FakeClock()
    executor = mock_executor(side_effect=[_read("processing")])

    result = await _service(executor, clock).get_automation_simulation(
        "sim-3", timeout_seconds=0
    )

    assert clock.sleeps == []
    assert executor.execute_query.await_count == 1
    assert result["waited_seconds"] == 0.0


@pytest.mark.unit
async def test_rejects_a_timeout_outside_the_range_before_any_read():
    executor = mock_executor(side_effect=[_read("success", {})])

    with pytest.raises(ValueError, match="timeout_seconds=61"):
        await _service(executor, FakeClock()).get_automation_simulation(
            "sim-4", timeout_seconds=61
        )

    executor.execute_query.assert_not_called()


@pytest.mark.unit
async def test_unknown_simulation_id_raises_with_the_id():
    executor = mock_executor(side_effect=[{"automationSimulation": None}])

    with pytest.raises(ValueError, match="simulation_id='sim-404'"):
        await _service(executor, FakeClock()).get_automation_simulation("sim-404")


def _ai_params(*field_ids):
    return {"aiParams": {"value": "x", "fieldIds": list(field_ids)}}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("action_params", "extra_input", "final", "expected_warnings"),
    [
        pytest.param(
            _ai_params("101", "102"),
            None,
            {"101": {"label": "Reply", "type": "long_text", "value": "[Seu Nome]"}},
            [
                {"field_id": "101", "kind": "placeholder", "text": "[Seu Nome]"},
                {"field_id": "102", "kind": "empty", "text": ""},
            ],
            id="action_params",
        ),
        pytest.param(
            _ai_params("101", "102"),
            {"action_params": _ai_params("201", "202")},
            {"201": {"label": "Reply", "type": "long_text", "value": "Done"}},
            [{"field_id": "202", "kind": "empty", "text": ""}],
            id="extra_input_replaces_action_params",
        ),
        pytest.param(
            None,
            {"action_params": _ai_params("201", "202")},
            {"201": {"label": "Reply", "type": "long_text", "value": "Done"}},
            [{"field_id": "202", "kind": "empty", "text": ""}],
            id="extra_input_only",
        ),
    ],
)
async def test_simulate_automation_warns_about_the_first_final_read(
    action_params, extra_input, final, expected_warnings
):
    mutation = {"createAutomationSimulation": {"simulationId": "sim-5"}}
    executor = mock_executor(side_effect=[mutation, _read("success", final)])

    result = await _service(executor, FakeClock()).simulate_automation(
        pipe_id="p1",
        action_id="generate_with_ai",
        sample_card_id="c1",
        action_params=action_params,
        extra_input=extra_input,
    )

    assert result["warnings"] == expected_warnings


@pytest.mark.unit
async def test_simulate_automation_has_no_warnings_while_processing():
    mutation = {"createAutomationSimulation": {"simulationId": "sim-6"}}
    executor = mock_executor(side_effect=[mutation, _read("processing")])

    result = await _service(executor, FakeClock()).simulate_automation(
        pipe_id="p1",
        action_id="generate_with_ai",
        sample_card_id="c1",
        action_params={"aiParams": {"value": "x", "fieldIds": ["101"]}},
    )

    assert result["warnings"] == []
