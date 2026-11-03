"""Unit tests for the data lookup records search planner (pure, no I/O)."""

import pytest

from pipefy_sdk.models.knowledge_base import DataLookupAttribute, DataLookupCondition
from pipefy_sdk.services.data_lookup_records import (
    field_uuids_by_slug,
    needs_field_uuids,
    to_records_conditions,
)


def _condition(field, **extra):
    return DataLookupCondition.model_validate(
        {"field": field, "operator": "eq", "value": "x", **extra}
    )


class TestNeedsFieldUuids:
    def test_custom_slug_without_target_needs_uuids(self):
        assert needs_field_uuids([_condition("title"), _condition("customer_email")])

    def test_fixed_slugs_and_given_targets_do_not(self):
        conditions = [
            _condition("created_by"),
            _condition("customer_email", fieldUuid="u-1"),
            _condition("labels", attribute="LABELS"),
        ]
        assert not needs_field_uuids(conditions)


class TestFieldUuidsBySlug:
    def test_maps_start_form_and_phase_fields(self):
        response = {
            "pipes": [
                {
                    "start_form_fields": [{"id": "email", "uuid": "u-1"}],
                    "phases": [
                        {"fields": [{"id": "status", "uuid": "u-2"}]},
                        {"fields": []},
                    ],
                }
            ]
        }
        assert field_uuids_by_slug(response) == {"email": "u-1", "status": "u-2"}

    def test_empty_or_missing_source_maps_nothing(self):
        assert field_uuids_by_slug({"pipes": []}) == {}
        assert field_uuids_by_slug({"pipes": None}) == {}

    def test_field_without_uuid_is_skipped(self):
        response = {"pipes": [{"start_form_fields": [{"id": "email", "uuid": None}]}]}
        assert field_uuids_by_slug(response) == {}


class TestToRecordsConditions:
    @pytest.mark.parametrize(
        ("slug", "attribute"),
        [
            ("id", DataLookupAttribute.ID),
            ("title", DataLookupAttribute.TITLE),
            ("created_by", DataLookupAttribute.CREATOR),
            ("current_phase", DataLookupAttribute.CURRENT_PHASE),
            ("assignees", DataLookupAttribute.ASSIGNEES),
        ],
    )
    def test_fixed_slug_gets_attribute(self, slug, attribute):
        (filled,) = to_records_conditions([_condition(slug)], {}, "301234567")
        assert filled.attribute is attribute
        assert filled.field_uuid is None
        assert filled.field == slug

    def test_custom_slug_gets_uuid(self):
        (filled,) = to_records_conditions(
            [_condition("email")], {"email": "u-1"}, "301234567"
        )
        assert filled.field_uuid == "u-1"
        assert filled.attribute is None

    def test_given_target_is_kept(self):
        given = _condition("email", fieldUuid="u-given")
        (filled,) = to_records_conditions([given], {"email": "u-1"}, "301234567")
        assert filled.field_uuid == "u-given"

    def test_unknown_slugs_listed_in_one_error(self):
        conditions = [_condition("email"), _condition("title"), _condition("ghost")]
        with pytest.raises(ValueError) as exc:
            to_records_conditions(conditions, {}, "301234567")
        message = str(exc.value)
        assert "conditions[0].field 'email'" in message
        assert "conditions[2].field 'ghost'" in message
        assert "title" not in message
        assert "301234567" in message

    def test_serialized_condition_carries_field_and_target(self):
        (filled,) = to_records_conditions([_condition("created_at")], {}, "301234567")
        assert filled.to_input() == {
            "field": "created_at",
            "operator": "eq",
            "value": "x",
            "usingFillWithAi": False,
            "attribute": "CREATED_AT",
        }
