"""Unit tests for the data lookup records search planner (pure, no I/O)."""

import pytest
from _shared.query_selection import selected_field_names

from pipefy_sdk.models.knowledge_base import DataLookupAttribute, DataLookupCondition
from pipefy_sdk.queries.knowledge_base_queries import (
    GET_DATA_LOOKUP_SOURCE_FIELDS_QUERY,
)
from pipefy_sdk.services.data_lookup_records import (
    SourceFields,
    needs_source_fields,
    source_fields_from_response,
    to_records_conditions,
)

LIST_FIELD_TYPES = [
    "assignee_select",
    "checklist_horizontal",
    "checklist_vertical",
    "connector",
    "label_select",
]


def _condition(field, operator="eq", **extra):
    return DataLookupCondition.model_validate(
        {"field": field, "operator": operator, "value": "x", **extra}
    )


def _source(*fields):
    """SourceFields from ``(slug, uuid, type)`` triples."""
    return source_fields_from_response(
        {
            "pipes": [
                {
                    "start_form_fields": [
                        {"id": slug, "uuid": uuid, "type": field_type}
                        for slug, uuid, field_type in fields
                    ]
                }
            ]
        },
        "301234567",
    )


def test_source_fields_query_selects_slug_uuid_and_type():
    for path in (("pipes", "start_form_fields"), ("pipes", "phases", "fields")):
        assert {"id", "uuid", "type"} <= selected_field_names(
            GET_DATA_LOOKUP_SOURCE_FIELDS_QUERY, *path
        )


class TestNeedsSourceFields:
    def test_condition_without_target_needs_source(self):
        assert needs_source_fields([_condition("title")])

    def test_given_field_uuid_needs_source_for_its_type(self):
        assert needs_source_fields([_condition("customer_email", fieldUuid="u-1")])

    def test_given_attributes_do_not(self):
        conditions = [
            _condition("labels", "contains", attribute="LABELS"),
            _condition("title", attribute="TITLE"),
        ]
        assert not needs_source_fields(conditions)


class TestSourceFieldsFromResponse:
    def test_maps_start_form_and_phase_fields(self):
        response = {
            "pipes": [
                {
                    "start_form_fields": [
                        {"id": "email", "uuid": "u-1", "type": "email"}
                    ],
                    "phases": [
                        {
                            "fields": [
                                {"id": "tags", "uuid": "u-2", "type": "label_select"}
                            ]
                        },
                        {"fields": []},
                    ],
                }
            ]
        }
        assert source_fields_from_response(response, "301234567") == SourceFields(
            uuids_by_slug={"email": {"u-1"}, "tags": {"u-2"}},
            type_by_uuid={"u-1": "email", "u-2": "label_select"},
        )

    def test_slug_repeated_across_phases_keeps_every_uuid(self):
        response = {
            "pipes": [
                {
                    "phases": [
                        {"fields": [{"id": "status", "uuid": "u-1", "type": "select"}]},
                        {"fields": [{"id": "status", "uuid": "u-2", "type": "select"}]},
                    ]
                }
            ]
        }
        source = source_fields_from_response(response, "301234567")
        assert source.uuids_by_slug == {"status": {"u-1", "u-2"}}

    @pytest.mark.parametrize("pipes", [[], None, [None]])
    def test_missing_source_names_the_source_id(self, pipes):
        with pytest.raises(ValueError, match="source_repo_id '301234567': no pipe"):
            source_fields_from_response({"pipes": pipes}, "301234567")

    def test_field_without_uuid_is_skipped(self):
        response = {
            "pipes": [
                {"start_form_fields": [{"id": "email", "uuid": None, "type": "email"}]}
            ]
        }
        assert source_fields_from_response(response, "301234567") == SourceFields()


class TestToRecordsConditions:
    @pytest.mark.parametrize(
        ("slug", "attribute"),
        [
            ("id", DataLookupAttribute.ID),
            ("title", DataLookupAttribute.TITLE),
            ("created_by", DataLookupAttribute.CREATOR),
            ("current_phase", DataLookupAttribute.CURRENT_PHASE),
        ],
    )
    def test_fixed_slug_gets_attribute(self, slug, attribute):
        (filled,) = to_records_conditions(
            [_condition(slug)], SourceFields(), "301234567"
        )
        assert filled.attribute is attribute
        assert filled.field_uuid is None
        assert filled.field == slug

    def test_custom_slug_gets_uuid(self):
        source = _source(("email", "u-1", "email"))
        (filled,) = to_records_conditions([_condition("email")], source, "301234567")
        assert filled.field_uuid == "u-1"
        assert filled.attribute is None

    def test_given_field_uuid_of_the_source_is_kept(self):
        source = _source(("labels", "u-given", "short_text"))
        given = _condition("labels", fieldUuid="u-given")
        (filled,) = to_records_conditions([given], source, "301234567")
        assert filled.field_uuid == "u-given"

    def test_given_field_uuid_outside_the_source_is_rejected(self):
        given = _condition("email", fieldUuid="u-other")
        with pytest.raises(ValueError) as exc:
            to_records_conditions([given], _source(), "301234567")
        message = str(exc.value)
        assert "conditions[0].fieldUuid 'u-other'" in message
        assert "no field with this uuid in source 301234567" in message

    def test_custom_field_with_fixed_slug_is_ambiguous(self):
        source = _source(("labels", "u-1", "short_text"))
        with pytest.raises(ValueError) as exc:
            to_records_conditions([_condition("labels", "contains")], source, "301")
        message = str(exc.value)
        assert "conditions[0].field 'labels' is both the fixed field LABELS" in message
        assert "Set fieldUuid" in message

    def test_slug_on_two_custom_fields_is_ambiguous(self):
        source = _source(("status", "u-1", "select"), ("status", "u-2", "select"))
        with pytest.raises(ValueError, match="matches 2 custom fields"):
            to_records_conditions([_condition("status")], source, "301")

    def test_unknown_slugs_listed_in_one_error(self):
        conditions = [_condition("email"), _condition("title"), _condition("ghost")]
        with pytest.raises(ValueError) as exc:
            to_records_conditions(conditions, SourceFields(), "301234567")
        message = str(exc.value)
        assert "conditions[0].field 'email'" in message
        assert "conditions[2].field 'ghost'" in message
        assert "title" not in message
        assert "301234567" in message

    def test_serialized_condition_carries_field_and_target(self):
        (filled,) = to_records_conditions(
            [_condition("created_at")], SourceFields(), "301234567"
        )
        assert filled.to_input() == {
            "field": "created_at",
            "operator": "eq",
            "value": "x",
            "usingFillWithAi": False,
            "attribute": "CREATED_AT",
        }


class TestOperatorFieldTypeRule:
    @pytest.mark.parametrize("operator", ["eq", "not_eq", "ilike"])
    def test_ordinary_field_takes_eq_not_eq_and_ilike(self, operator):
        source = _source(("email", "u-1", "email"))
        conditions = [_condition("email", operator), _condition("title", operator)]
        filled = to_records_conditions(conditions, source, "301234567")
        assert [c.operator for c in filled] == [operator, operator]

    @pytest.mark.parametrize("field_type", LIST_FIELD_TYPES)
    def test_list_field_type_takes_contains(self, field_type):
        source = _source(("tags", "u-1", field_type))
        (filled,) = to_records_conditions(
            [_condition("tags", "contains")], source, "301234567"
        )
        assert filled.field_uuid == "u-1"

    @pytest.mark.parametrize("slug", ["labels", "assignees"])
    def test_fixed_list_field_takes_contains(self, slug):
        (filled,) = to_records_conditions(
            [_condition(slug, "contains")], SourceFields(), "301234567"
        )
        assert filled.operator == "contains"

    def test_given_list_attribute_takes_contains(self):
        given = _condition("assignees", "contains", attribute="ASSIGNEES")
        (filled,) = to_records_conditions([given], SourceFields(), "301234567")
        assert filled.attribute is DataLookupAttribute.ASSIGNEES

    def test_given_field_uuid_uses_the_source_type(self):
        source = _source(("tags", "u-1", "label_select"))
        given = _condition("tags", "contains", fieldUuid="u-1")
        (filled,) = to_records_conditions([given], source, "301234567")
        assert filled.field_uuid == "u-1"

    @pytest.mark.parametrize("slug", ["title", "email"])
    def test_contains_on_ordinary_field_points_to_ilike(self, slug):
        source = _source(("email", "u-1", "short_text"))
        with pytest.raises(ValueError) as exc:
            to_records_conditions([_condition(slug, "contains")], source, "301")
        message = str(exc.value)
        assert f"conditions[0].operator 'contains' on field '{slug}'" in message
        assert "Use ilike" in message

    @pytest.mark.parametrize("operator", ["eq", "not_eq", "ilike"])
    def test_list_field_rejects_other_operators(self, operator):
        source = _source(("tags", "u-1", "label_select"))
        with pytest.raises(ValueError) as exc:
            to_records_conditions([_condition("tags", operator)], source, "301")
        message = str(exc.value)
        assert f"conditions[0].operator '{operator}' on field 'tags'" in message
        assert "takes only the operator contains" in message

    def test_given_list_attribute_rejects_eq(self):
        given = _condition("labels", attribute="LABELS")
        with pytest.raises(ValueError, match="takes only the operator contains"):
            to_records_conditions([given], SourceFields(), "301")

    def test_every_bad_condition_listed_in_one_error(self):
        source = _source(("tags", "u-1", "label_select"))
        conditions = [
            _condition("title", "contains"),
            _condition("title", "ilike"),
            _condition("tags", "eq"),
            _condition("ghost"),
            _condition("assignees", "not_eq"),
        ]
        with pytest.raises(ValueError) as exc:
            to_records_conditions(conditions, source, "301234567")
        message = str(exc.value)
        assert "conditions[0].operator 'contains' on field 'title'" in message
        assert "conditions[1]" not in message
        assert "conditions[2].operator 'eq' on field 'tags'" in message
        assert "conditions[3].field 'ghost'" in message
        assert "conditions[4].operator 'not_eq' on field 'assignees'" in message
        assert message.isascii()
