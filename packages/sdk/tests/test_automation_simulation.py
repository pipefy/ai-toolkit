import pytest

from pipefy_sdk.automation_simulation import (
    next_simulation_poll_delay,
    parse_simulation_wait_seconds,
    requested_simulation_field_ids,
    simulation_output_warnings,
    simulation_read_budget,
)


def _row(result, status="success"):
    return {"status": status, "details": None, "simulationResult": result}


def _entry(value, label="Reply draft", field_type="long_text"):
    return {"label": label, "type": field_type, "value": value}


@pytest.mark.unit
def test_warnings_list_each_bracket_placeholder_once_per_field():
    row = _row(
        {
            "101": _entry("Best regards,\n[Your Name]\n[Your Company]\n[Your Name]"),
            "102": _entry("Prezado [Nome do Cliente],", label="Saudacao"),
        }
    )

    assert simulation_output_warnings(row) == [
        {"field_id": "101", "kind": "placeholder", "text": "[Your Name]"},
        {"field_id": "101", "kind": "placeholder", "text": "[Your Company]"},
        {"field_id": "102", "kind": "placeholder", "text": "[Nome do Cliente]"},
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "See [the policy](https://example.com/policy).",
        "As stated in [1] and [12].",
        "- [ ] review\n- [x] approve\n- [X] sign",
        "Totals [1, 2, 3]",
        "No brackets here.",
    ],
)
def test_warnings_ignore_links_citations_and_checkboxes(text):
    assert simulation_output_warnings(_row({"101": _entry(text)})) == []


@pytest.mark.unit
def test_warnings_read_each_item_of_a_list_value():
    row = _row(
        {"103": _entry(["urgent", "[Tag]"], label="Tags", field_type="checklist")}
    )

    assert simulation_output_warnings(row) == [
        {"field_id": "103", "kind": "placeholder", "text": "[Tag]"},
    ]


@pytest.mark.unit
def test_warnings_list_each_requested_field_with_no_output():
    row = _row({"101": _entry("Hello.")})

    assert simulation_output_warnings(row, ["101", "102", " 103 ", "102"]) == [
        {"field_id": "102", "kind": "empty", "text": ""},
        {"field_id": "103", "kind": "empty", "text": ""},
    ]


@pytest.mark.unit
def test_warnings_flag_every_requested_field_when_the_result_is_empty():
    assert simulation_output_warnings(_row({}), [101, 102]) == [
        {"field_id": "101", "kind": "empty", "text": ""},
        {"field_id": "102", "kind": "empty", "text": ""},
    ]


@pytest.mark.unit
@pytest.mark.parametrize("status", ["processing", "failed"])
def test_warnings_are_empty_until_the_simulation_succeeds(status):
    assert simulation_output_warnings(_row(None, status=status), ["101"]) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    ("action_params", "expected"),
    [
        ({"aiParams": {"fieldIds": ["101", 102]}}, ["101", "102"]),
        ({"aiParams": {"value": "x"}}, []),
        ({"aiParams": "not an object"}, []),
        ({"aiParams": {"fieldIds": "101"}}, []),
        ({}, []),
        (None, []),
    ],
)
def test_requested_field_ids_come_from_ai_params(action_params, expected):
    assert requested_simulation_field_ids(action_params) == expected


@pytest.mark.unit
@pytest.mark.parametrize("value", [0, 30, 45])
def test_wait_seconds_accepts_zero_to_forty_five(value):
    assert parse_simulation_wait_seconds(value) == value


@pytest.mark.unit
@pytest.mark.parametrize("value", [-1, 46, True])
def test_wait_seconds_rejects_values_outside_the_range(value):
    with pytest.raises(ValueError, match=rf"timeout_seconds={value!r}"):
        parse_simulation_wait_seconds(value)


@pytest.mark.unit
@pytest.mark.parametrize("status", ["success", "failed"])
def test_poll_stops_when_the_simulation_is_final(status):
    assert (
        next_simulation_poll_delay(status, waited_seconds=0.0, timeout_seconds=30)
        is None
    )


@pytest.mark.unit
def test_poll_waits_the_interval_while_processing():
    assert (
        next_simulation_poll_delay("processing", waited_seconds=4.0, timeout_seconds=30)
        == 2.0
    )


@pytest.mark.unit
def test_poll_shortens_the_last_wait_to_the_limit():
    assert (
        next_simulation_poll_delay(
            "processing", waited_seconds=29.5, timeout_seconds=30
        )
        == 0.5
    )


@pytest.mark.unit
@pytest.mark.parametrize(("waited", "limit"), [(30.0, 30), (31.0, 30), (0.0, 0)])
def test_poll_stops_at_the_limit(waited, limit):
    assert (
        next_simulation_poll_delay(
            "processing", waited_seconds=waited, timeout_seconds=limit
        )
        is None
    )


@pytest.mark.unit
def test_read_budget_is_the_time_left_before_the_limit():
    assert simulation_read_budget(waited_seconds=4.0, timeout_seconds=5) == 1.0


@pytest.mark.unit
@pytest.mark.parametrize(("waited", "limit"), [(5.0, 5), (6.3, 5), (0.0, 0)])
def test_read_budget_is_none_at_or_after_the_limit(waited, limit):
    assert simulation_read_budget(waited_seconds=waited, timeout_seconds=limit) is None
