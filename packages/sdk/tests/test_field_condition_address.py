import pytest

from pipefy_sdk.field_condition_address import (
    field_address_slug_heads,
    internal_ids_by_field_slug,
    resolve_field_address_slugs,
)


def _pipe():
    return {
        "start_form_fields": [{"id": "requester", "internal_id": "100"}],
        "phases": [
            {"id": "1", "fields": [{"id": "aprovado", "internal_id": "200"}]},
            {"id": "2", "fields": [{"id": "parent_card", "internal_id": "300"}]},
        ],
    }


def _condition(*addresses):
    return {
        "expressions": [
            {
                "structure_id": index,
                "field_address": address,
                "operation": "equals",
                "value": "Sim",
            }
            for index, address in enumerate(addresses)
        ],
        "expressions_structure": [list(range(len(addresses)))],
    }


@pytest.mark.unit
def test_numeric_addresses_need_no_lookup():
    assert field_address_slug_heads(_condition("200", "300.400")) == set()


@pytest.mark.unit
def test_non_numeric_first_segments_need_a_lookup():
    condition = _condition("aprovado", "parent_card.400", "200")

    assert field_address_slug_heads(condition) == {"aprovado", "parent_card"}


@pytest.mark.unit
def test_a_condition_without_expressions_needs_no_lookup():
    assert field_address_slug_heads(None) == set()
    assert field_address_slug_heads({"expressions": None}) == set()


@pytest.mark.unit
def test_slugs_of_the_start_form_and_every_phase_map_to_internal_ids():
    assert internal_ids_by_field_slug(_pipe()) == {
        "requester": {"100"},
        "aprovado": {"200"},
        "parent_card": {"300"},
    }


@pytest.mark.unit
def test_a_field_slug_becomes_its_internal_id():
    resolved = resolve_field_address_slugs(
        _condition("aprovado", "requester"), internal_ids_by_field_slug(_pipe())
    )

    addresses = [e["field_address"] for e in resolved["expressions"]]
    assert addresses == ["200", "100"]
    assert resolved["expressions_structure"] == [[0, 1]]


@pytest.mark.unit
def test_only_the_first_segment_of_a_connected_field_path_changes():
    resolved = resolve_field_address_slugs(
        _condition("parent_card.400"), internal_ids_by_field_slug(_pipe())
    )

    assert resolved["expressions"][0]["field_address"] == "300.400"


@pytest.mark.unit
def test_a_value_that_is_no_field_slug_of_the_pipe_stays_as_sent():
    resolved = resolve_field_address_slugs(
        _condition("title"), internal_ids_by_field_slug(_pipe())
    )

    assert resolved["expressions"][0]["field_address"] == "title"


@pytest.mark.unit
def test_a_slug_shared_by_two_fields_is_rejected_with_both_ids():
    slugs = {"aprovado": {"200", "201"}}

    with pytest.raises(ValueError, match="'aprovado'.*200.*201"):
        resolve_field_address_slugs(_condition("aprovado"), slugs)


@pytest.mark.unit
def test_the_caller_condition_is_not_changed():
    condition = _condition("aprovado")

    resolve_field_address_slugs(condition, internal_ids_by_field_slug(_pipe()))

    assert condition["expressions"][0]["field_address"] == "aprovado"
