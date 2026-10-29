from __future__ import annotations

import pytest

from pipefy_sdk.graphql_problem import (
    GraphQLProblem,
    GraphQLProblemKind,
    classify_exception,
    classify_graphql_error_dicts,
)


@pytest.mark.parametrize(
    "code",
    [
        "FEATURE_BLOCKED",
        "FEATURE_NOT_ENABLED",
        "FEATURE_DISABLED",
        "FEATURE_UNAVAILABLE",
    ],
)
def test_feature_code_is_classified_as_feature_not_enabled(code: str) -> None:
    problem = classify_graphql_error_dicts(
        [{"message": "Feature unavailable", "extensions": {"code": code}}]
    )

    assert problem == GraphQLProblem(
        kind=GraphQLProblemKind.FEATURE_NOT_ENABLED,
        message="Feature unavailable",
        code=code,
    )


def test_html_validation_failed_is_classified_as_invalid_arguments() -> None:
    problem = classify_graphql_error_dicts(
        [{"message": "Invalid HTML", "extensions": {"code": "HTML_VALIDATION_FAILED"}}]
    )

    assert problem == GraphQLProblem(
        kind=GraphQLProblemKind.INVALID_ARGUMENTS,
        message="Invalid HTML",
        code="HTML_VALIDATION_FAILED",
    )


def test_padded_lowercase_feature_blocked_is_classified_with_code_verbatim() -> None:
    problem = classify_graphql_error_dicts(
        [
            {
                "message": "Feature unavailable",
                "extensions": {"code": " feature_blocked "},
            }
        ]
    )

    assert problem == GraphQLProblem(
        kind=GraphQLProblemKind.FEATURE_NOT_ENABLED,
        message="Feature unavailable",
        code=" feature_blocked ",
    )


def test_code_wins_over_message() -> None:
    problem = classify_graphql_error_dicts(
        [
            {
                "message": "Record not found",
                "extensions": {"code": "PERMISSION_DENIED"},
            }
        ]
    )
    assert problem is not None
    assert problem.kind is GraphQLProblemKind.PERMISSION_DENIED


def test_not_found_falls_back_to_message_marker() -> None:
    problem = classify_graphql_error_dicts(
        [{"message": "Couldn't find Repo with uuid x", "extensions": {}}]
    )
    assert problem is not None
    assert problem.kind is GraphQLProblemKind.NOT_FOUND
    assert problem.code is None


def test_invalid_arguments_and_feature_codes() -> None:
    invalid = classify_graphql_error_dicts(
        [{"message": "bad", "extensions": {"code": "RECORD_INVALID"}}]
    )
    feature = classify_graphql_error_dicts(
        [{"message": "off", "extensions": {"code": "FEATURE_NOT_ENABLED"}}]
    )
    assert invalid is not None and invalid.kind is GraphQLProblemKind.INVALID_ARGUMENTS
    assert (
        feature is not None and feature.kind is GraphQLProblemKind.FEATURE_NOT_ENABLED
    )


def test_unrecognized_error_is_runtime() -> None:
    problem = classify_graphql_error_dicts(
        [{"message": "boom", "extensions": {"code": "SOMETHING_ELSE"}}]
    )
    assert problem is not None
    assert problem.kind is GraphQLProblemKind.RUNTIME
    assert problem.code == "SOMETHING_ELSE"


def test_empty_list_returns_none() -> None:
    assert classify_graphql_error_dicts([]) is None


def test_blank_or_whitespace_message_becomes_unknown_error() -> None:
    for raw in ("", "   ", None):
        problem = classify_graphql_error_dicts(
            [{"message": raw, "extensions": {"code": "PERMISSION_DENIED"}}]
        )
        assert problem is not None
        assert problem.message == "Unknown error"
        assert problem.kind is GraphQLProblemKind.PERMISSION_DENIED


def test_classify_exception_reads_errors_attribute() -> None:
    class FakeTransportError(Exception):
        def __init__(self):
            super().__init__("gql error")
            self.errors = [
                {
                    "message": "Permission denied",
                    "extensions": {"code": "PERMISSION_DENIED"},
                }
            ]

    problem = classify_exception(FakeTransportError())
    assert problem is not None
    assert problem.kind is GraphQLProblemKind.PERMISSION_DENIED


def test_classify_exception_without_graphql_errors_returns_none() -> None:
    assert classify_exception(RuntimeError("socket closed")) is None
