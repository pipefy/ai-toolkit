"""Pydantic models for knowledge base data lookup inputs.

A data lookup's conditions are validated here, at the boundary, because the
backend only checks ``field`` and ``operator`` at write time: a static
condition saved without a ``value`` (or with a non-string one) is accepted by
the API and then breaks the lookup when an agent runs it. Parsing into
:class:`DataLookupCondition` up front keeps definitions that cannot work from
ever being persisted.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipefy_sdk.models.validators import NonBlankStr

# Attribute name → camelCase alias, so error messages name the field the same
# way the tool/docs teach it (``inputName``, not ``input_name``).
_FILL_WITH_AI_FIELDS = {
    "input_name": "inputName",
    "input_type": "inputType",
    "input_description": "inputDescription",
}


class DataLookupAttribute(StrEnum):
    """Fixed card or record attribute a data lookup condition can filter on."""

    ID = "ID"
    TITLE = "TITLE"
    CREATOR = "CREATOR"
    CREATED_AT = "CREATED_AT"
    DUE_DATE = "DUE_DATE"
    FINISHED_AT = "FINISHED_AT"
    CURRENT_PHASE = "CURRENT_PHASE"
    LABELS = "LABELS"
    ASSIGNEES = "ASSIGNEES"


class DataLookupOperator(StrEnum):
    """Operator of a data lookup condition.

    ``eq`` and ``not_eq`` compare the whole value and ``ilike`` matches a
    case-insensitive substring. ``contains`` matches an item of a list field
    (labels, assignees, checklists, connections). The knowledge base service
    checks each operator against the field type before the write.
    """

    EQ = "eq"
    NOT_EQ = "not_eq"
    CONTAINS = "contains"
    ILIKE = "ilike"


class DataLookupCondition(BaseModel):
    """One record-filter condition of a knowledge base data lookup.

    Accepts snake_case or camelCase keys (``usingFillWithAi``, ``inputName``,
    …); unknown keys are rejected so a typo cannot silently drop a constraint.
    Two mutually exclusive shapes exist:

    - **Static** (``using_fill_with_ai`` false, the default): ``value`` is
      required and must be a non-blank string — the agent runtime compares
      string values and rejects a condition saved without one.
    - **AI-filled** (``using_fill_with_ai`` true): ``input_name``,
      ``input_type``, and ``input_description`` are required (they describe
      the input the AI asks for at runtime) and ``value`` must be omitted
      (the runtime replaces it with the AI-provided input, so a static value
      here would be silently ignored).

    ``operator`` is a :class:`DataLookupOperator`. ``input_type`` is an
    opaque backend string (e.g. ``"text"``, ``"number"``). ``field`` is the
    field slug and is always required (the backend rejects a condition without
    one). The agent searches by ``field_uuid`` for a custom field or by
    ``attribute`` for a fixed one, so a condition carries at most one of the
    two. The knowledge base service fills in the missing one from ``field``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    field: NonBlankStr
    operator: DataLookupOperator
    value: NonBlankStr | None = None
    using_fill_with_ai: bool = Field(default=False, alias="usingFillWithAi")
    input_name: NonBlankStr | None = Field(default=None, alias="inputName")
    input_type: NonBlankStr | None = Field(default=None, alias="inputType")
    input_description: NonBlankStr | None = Field(
        default=None, alias="inputDescription"
    )
    attribute: DataLookupAttribute | None = None
    field_uuid: NonBlankStr | None = Field(default=None, alias="fieldUuid")

    @model_validator(mode="after")
    def _check_shape(self) -> DataLookupCondition:
        if self.attribute is not None and self.field_uuid is not None:
            raise ValueError(
                "set fieldUuid (custom field) or attribute (fixed field), not both"
            )
        if self.using_fill_with_ai:
            missing = [
                alias
                for name, alias in _FILL_WITH_AI_FIELDS.items()
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(
                    "an AI-filled condition (usingFillWithAi=true) requires "
                    f"non-blank {', '.join(missing)}"
                )
            if self.value is not None:
                raise ValueError(
                    "an AI-filled condition (usingFillWithAi=true) must not set "
                    "'value'; the AI provides it at runtime"
                )
        else:
            if self.value is None:
                raise ValueError(
                    "a static condition requires a non-blank string 'value' "
                    "(or set usingFillWithAi=true with inputName/inputType/"
                    "inputDescription)"
                )
            extras = [
                alias
                for name, alias in _FILL_WITH_AI_FIELDS.items()
                if getattr(self, name) is not None
            ]
            if extras:
                raise ValueError(
                    f"{', '.join(extras)} only apply to AI-filled conditions; "
                    "set usingFillWithAi=true or drop them"
                )
        return self

    def to_input(self) -> dict[str, Any]:
        """Serialize to the GraphQL condition input (camelCase, no nulls)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
