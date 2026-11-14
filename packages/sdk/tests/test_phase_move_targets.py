import pytest

from pipefy_sdk.graphql_inputs import UpdatePhaseInput
from pipefy_sdk.phase_move_targets import (
    parse_target_phase_ids,
    plan_phase_move_targets,
)


def _allowed_moves(name="Review", targets=("20", "30")):
    return {
        "phase": {
            "id": "10",
            "name": name,
            "cards_can_be_moved_to_phases": [
                {"id": t, "name": f"Phase {t}"} for t in targets
            ],
        }
    }


@pytest.mark.unit
def test_parse_target_phase_ids_keeps_order_and_drops_repeats():
    assert parse_target_phase_ids([40, " 20 ", "40", "20"], replace=False) == (
        "40",
        "20",
    )


@pytest.mark.unit
def test_parse_target_phase_ids_rejects_an_empty_list_without_replace():
    with pytest.raises(ValueError, match="target_phase_ids is empty"):
        parse_target_phase_ids([], replace=False)


@pytest.mark.unit
def test_parse_target_phase_ids_accepts_an_empty_list_with_replace():
    assert parse_target_phase_ids([], replace=True) == ()


@pytest.mark.unit
@pytest.mark.parametrize("replace", [False, True])
def test_parse_target_phase_ids_rejects_a_blank_id(replace):
    with pytest.raises(ValueError, match=r"target_phase_ids\[1\] is blank"):
        parse_target_phase_ids(["20", " "], replace=replace)


@pytest.mark.unit
def test_additive_plan_keeps_current_targets_and_appends_new_ones():
    plan = plan_phase_move_targets("10", _allowed_moves(), ("40",), replace=False)

    assert plan == UpdatePhaseInput(
        id="10", name="Review", jumpTargetIds=["20", "30", "40"]
    )


@pytest.mark.unit
def test_additive_plan_sends_a_target_that_is_already_connected_once():
    plan = plan_phase_move_targets("10", _allowed_moves(), ("30", "40"), replace=False)

    assert plan.jumpTargetIds == ["20", "30", "40"]


@pytest.mark.unit
def test_replace_plan_sends_only_the_requested_targets():
    plan = plan_phase_move_targets("10", _allowed_moves(), ("40", "20"), replace=True)

    assert plan == UpdatePhaseInput(id="10", name="Review", jumpTargetIds=["40", "20"])


@pytest.mark.unit
def test_replace_plan_with_no_targets_clears_the_connections():
    plan = plan_phase_move_targets("10", _allowed_moves(), (), replace=True)

    assert plan.to_graphql_input() == {
        "id": "10",
        "name": "Review",
        "jumpTargetIds": [],
    }


@pytest.mark.unit
def test_plan_on_a_phase_whose_connections_read_as_null():
    allowed_moves = {
        "phase": {"id": "10", "name": "Review", "cards_can_be_moved_to_phases": None}
    }

    plan = plan_phase_move_targets("10", allowed_moves, ("20",), replace=False)

    assert plan.jumpTargetIds == ["20"]


@pytest.mark.unit
def test_plan_on_a_phase_with_no_connections():
    plan = plan_phase_move_targets(
        "10", _allowed_moves(targets=()), ("20",), replace=False
    )

    assert plan.jumpTargetIds == ["20"]


@pytest.mark.unit
def test_plan_rejects_a_phase_the_read_did_not_return():
    with pytest.raises(ValueError, match="Phase 10 not found or access denied"):
        plan_phase_move_targets("10", {"phase": None}, ("20",), replace=False)
