"""Unit tests for shared MCP tool validation helpers."""

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from pipefy_mcp.core.tool_error_envelope import tool_error_message
from pipefy_mcp.tools.validation_helpers import (
    format_validation_error_message,
    mutation_error_if_not_optional_dict,
    valid_repo_id,
    validate_optional_tool_id,
    validate_tool_id,
)


@pytest.mark.unit
def test_valid_repo_id_positive_int_and_non_empty_str():
    assert valid_repo_id(1) is True
    assert valid_repo_id("abc") is True
    assert valid_repo_id("  x  ") is True


@pytest.mark.unit
def test_valid_repo_id_rejects_zero_negative_empty_and_other_types():
    assert valid_repo_id(0) is False
    assert valid_repo_id(-1) is False
    assert valid_repo_id("") is False
    assert valid_repo_id("   ") is False
    assert valid_repo_id(None) is False
    assert valid_repo_id([1]) is False


@pytest.mark.unit
def test_mutation_error_if_not_optional_dict_none_and_dict_ok():
    assert mutation_error_if_not_optional_dict(None, arg_name="extra_input") is None
    assert mutation_error_if_not_optional_dict({}, arg_name="extra_input") is None
    assert mutation_error_if_not_optional_dict({"a": 1}, arg_name="x") is None


@pytest.mark.unit
def test_mutation_error_if_not_optional_dict_rejects_non_mapping():
    err = mutation_error_if_not_optional_dict("x", arg_name="extra_input")
    assert err is not None
    assert err["success"] is False
    assert "extra_input" in tool_error_message(err)
    err_list = mutation_error_if_not_optional_dict([], arg_name="extra_input")
    assert err_list is not None
    assert err_list["success"] is False


@pytest.mark.unit
class TestValidateToolId:
    def test_positive_int_coerced_to_str(self):
        val, err = validate_tool_id(42, "card_id")
        assert val == "42"
        assert err is None

    def test_non_empty_str_passes(self):
        val, err = validate_tool_id("abc-123", "pipe_id")
        assert val == "abc-123"
        assert err is None

    def test_str_is_stripped(self):
        val, err = validate_tool_id("  99  ", "id")
        assert val == "99"
        assert err is None

    def test_rejects_empty_str(self):
        val, err = validate_tool_id("", "card_id")
        assert val is None
        assert err["success"] is False
        assert "card_id" in tool_error_message(err)

    def test_rejects_whitespace_only(self):
        val, err = validate_tool_id("   ", "card_id")
        assert val is None
        assert err["success"] is False

    def test_rejects_zero(self):
        val, err = validate_tool_id(0, "card_id")
        assert val is None
        assert err["success"] is False

    def test_rejects_negative_int(self):
        val, err = validate_tool_id(-1, "card_id")
        assert val is None
        assert err["success"] is False

    def test_rejects_negative_str(self):
        val, err = validate_tool_id("-5", "card_id")
        assert val is None
        assert err["success"] is False

    def test_rejects_bool(self):
        val, err = validate_tool_id(True, "card_id")
        assert val is None
        assert err["success"] is False


@pytest.mark.unit
class TestValidateOptionalToolId:
    def test_none_passes_through(self):
        ok, val, err = validate_optional_tool_id(None, "org_id")
        assert ok is True
        assert val is None
        assert err is None

    def test_valid_value_cleaned(self):
        ok, val, err = validate_optional_tool_id("  42  ", "org_id")
        assert ok is True
        assert val == "42"
        assert err is None

    def test_invalid_returns_error(self):
        ok, val, err = validate_optional_tool_id("", "org_id")
        assert ok is False
        assert val is None
        assert err["success"] is False
        assert "org_id" in tool_error_message(err)


@pytest.mark.unit
def test_format_validation_error_message_strips_pydantic_noise():
    class _Probe(BaseModel):
        x: int
        items: list[str] = Field(min_length=1)

    message = None
    try:
        _Probe.model_validate({"items": []})
    except ValidationError as exc:
        message = format_validation_error_message(exc)

    assert message is not None
    # The leaked parts of ``str(exc)`` must be gone.
    assert "input_value=" not in message
    assert "pydantic.dev" not in message
    assert "_Probe" not in message
    # ...but the message still names the field and the constraint that failed, not just
    # the field name (a renderer that dropped the constraint text would still say "items").
    assert "missing required argument 'x'" in message
    assert "items:" in message
    assert "at least 1 item" in message


@pytest.mark.unit
def test_format_validation_error_message_drops_value_error_prefix():
    # A custom validator raises ValueError; Pydantic renders it as "Value error, <text>".
    # The formatter must surface only <text>, keyed by field, with no leaked prefix.
    class _Probe(BaseModel):
        name: str

        @field_validator("name")
        @classmethod
        def _check(cls, value: str) -> str:
            if not value.strip():
                raise ValueError("name must not be blank")
            return value

    message = None
    try:
        _Probe.model_validate({"name": "  "})
    except ValidationError as exc:
        message = format_validation_error_message(exc)

    assert message is not None
    assert "Value error" not in message
    assert "name: name must not be blank" in message


@pytest.mark.unit
def test_format_validation_error_message_renders_missing_and_extra():
    class _Strict(BaseModel):
        model_config = ConfigDict(extra="forbid")
        a: int

    message = None
    try:
        _Strict.model_validate({"b": 1})
    except ValidationError as exc:
        message = format_validation_error_message(exc)

    assert message is not None
    assert "missing required argument 'a'" in message
    assert "unknown argument 'b'" in message
    assert "; " in message
