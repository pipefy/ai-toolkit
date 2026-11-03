"""Unit tests for the data lookup records search planner (pure, no I/O)."""

import pytest
from _shared.query_selection import selected_field_names

from pipefy_sdk.models.knowledge_base import DataLookupAttribute, DataLookupCondition
from pipefy_sdk.queries.knowledge_base_queries import (
    GET_DATA_LOOKUP_SOURCE_FIELDS_QUERY,
)
from pipefy_sdk.services.data_lookup_records import (
    field_uuids_by_slug,
    needs_source_fields,
    to_records_conditions,
)


def _condition(field, **extra):
    return DataLookupCondition.model_validate(
        {"field": field, "operator": "eq", "value": "x", **extra}
    )


def test_source_fields_query_selects_slug_and_uuid():
    for path in (("pipes", "start_form_fields"), ("pipes", "phases", "fields")):
        assert {"id", "uuid"} <= selected_field_names(
            GET_DATA_LOOKUP_SOURCE_FIELDS_QUERY, *path
        )


class TestNeedsSourceFields:
    def test_condition_without_target_needs_source(self):
        assert needs_source_fields([_condition("title")])

    def test_given_targets_do_not(self):
        conditions = [
            _condition("customer_email", fieldUuid="u-1"),
            _condition("labels", attribute="LABELS"),
        ]
        assert not needs_source_fields(conditions)


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
        assert field_uuids_by_slug(response, "301234567") == {
            "email": {"u-1"},
            "status": {"u-2"},
        }

    def test_slug_repeated_across_phases_keeps_every_uuid(self):
        response = {
            "pipes": [
                {
                    "phases": [
                        {"fields": [{"id": "status", "uuid": "u-1"}]},
                        {"fields": [{"id": "status", "uuid": "u-2"}]},
                    ]
                }
            ]
        }
        assert field_uuids_by_slug(response, "301234567") == {"status": {"u-1", "u-2"}}

    @pytest.mark.parametrize("pipes", [[], None, [None]])
    def test_missing_source_names_the_source_id(self, pipes):
        with pytest.raises(ValueError, match="source_repo_id '301234567': no pipe"):
            field_uuids_by_slug({"pipes": pipes}, "301234567")

    def test_field_without_uuid_is_skipped(self):
        response = {"pipes": [{"start_form_fields": [{"id": "email", "uuid": None}]}]}
        assert field_uuids_by_slug(response, "301234567") == {}


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
            [_condition("email")], {"email": {"u-1"}}, "301234567"
        )
        assert filled.field_uuid == "u-1"
        assert filled.attribute is None

    def test_given_target_is_kept(self):
        given = _condition("labels", fieldUuid="u-given")
        (filled,) = to_records_conditions([given], {"labels": {"u-1"}}, "301234567")
        assert filled.field_uuid == "u-given"

    def test_custom_field_with_fixed_slug_is_ambiguous(self):
        with pytest.raises(ValueError) as exc:
            to_records_conditions([_condition("labels")], {"labels": {"u-1"}}, "301")
        message = str(exc.value)
        assert "conditions[0].field 'labels' is both the fixed field LABELS" in message
        assert "Set fieldUuid" in message

    def test_slug_on_two_custom_fields_is_ambiguous(self):
        with pytest.raises(ValueError, match="matches 2 custom fields"):
            to_records_conditions(
                [_condition("status")], {"status": {"u-1", "u-2"}}, "301"
            )

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
