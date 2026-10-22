from __future__ import annotations

import pytest

from pipefy_sdk.exceptions import HtmlValidationError, HtmlViolation


def _script_violation() -> HtmlViolation:
    return HtmlViolation(
        code="SCRIPT_FORBIDDEN",
        message="Remove the script tag.",
        selector="script",
        attribute=None,
    )


@pytest.mark.parametrize(
    ("code", "message"), [("", "Remove the script tag."), ("SCRIPT_FORBIDDEN", "  ")]
)
def test_html_violation_rejects_a_blank_code_or_message(
    code: str, message: str
) -> None:
    with pytest.raises(ValueError, match="non-empty code and message"):
        HtmlViolation(code=code, message=message, selector=None, attribute=None)


@pytest.mark.parametrize(("selector", "attribute"), [("", None), ("button", "")])
def test_html_violation_rejects_an_empty_selector_or_attribute(
    selector: str | None, attribute: str | None
) -> None:
    with pytest.raises(ValueError, match="None or non-empty"):
        HtmlViolation(
            code="EVENT_HANDLER_FORBIDDEN",
            message="Remove the onclick handler.",
            selector=selector,
            attribute=attribute,
        )


def test_html_violation_from_extension_trims_text_and_reads_blanks_as_absent() -> None:
    violation = HtmlViolation.from_extension(
        {
            "code": " SCRIPT_FORBIDDEN ",
            "message": "Remove the script tag. ",
            "selector": "",
            "attribute": 5,
        }
    )

    assert violation == HtmlViolation(
        code="SCRIPT_FORBIDDEN",
        message="Remove the script tag.",
        selector=None,
        attribute=None,
    )


@pytest.mark.parametrize(
    "raw",
    [
        {"message": "Remove the script tag."},
        {"code": "SCRIPT_FORBIDDEN", "message": ""},
    ],
)
def test_html_violation_from_extension_without_code_or_message_is_none(
    raw: dict,
) -> None:
    assert HtmlViolation.from_extension(raw) is None


def test_html_validation_error_rejects_no_violations() -> None:
    with pytest.raises(ValueError, match="at least one violation"):
        HtmlValidationError(())


def test_html_validation_error_message_joins_violation_messages() -> None:
    assert str(HtmlValidationError((_script_violation(),))) == (
        "HTML validation failed: Remove the script tag."
    )
