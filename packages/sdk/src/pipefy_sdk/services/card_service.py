from __future__ import annotations

import json
from typing import Any, NoReturn

from pipefy_sdk.exceptions import PartialCardUpdateError
from pipefy_sdk.graphql_executor import GraphQLExecutor
from pipefy_sdk.queries.card_queries import (
    CREATE_CARD_MUTATION,
    CREATE_COMMENT_MUTATION,
    DELETE_CARD_MUTATION,
    DELETE_COMMENT_MUTATION,
    FIND_CARDS_QUERY,
    GET_CARD_FIELD_IDS_QUERY,
    GET_CARD_QUERY,
    GET_CARD_RELATIONS_QUERY,
    GET_CARDS_QUERY,
    MOVE_CARD_TO_PHASE_MUTATION,
    UPDATE_CARD_FIELD_MUTATION,
    UPDATE_CARD_MUTATION,
    UPDATE_COMMENT_MUTATION,
    UPDATE_FIELDS_VALUES_MUTATION,
)
from pipefy_sdk.services.types import CardSearch
from pipefy_sdk.utils.formatters import (
    convert_fields_to_array,
    convert_values_to_camel_case,
)


def _decode_user_error_message(raw: Any) -> str:
    """Flatten one ``UserError.message`` into plain text.

    The API sends this field two ways: a bare sentence ("Field not found"), and a
    JSON-encoded array of sentences (``'["Value \\"x\\" is not in a valid
    format"]'``). Returning the second verbatim hands the caller a doubly escaped
    string, so decode it when it parses and fall back to the raw text otherwise.
    """
    if not isinstance(raw, str):
        return str(raw)
    text = raw.strip()
    if not text.startswith("["):
        return text
    try:
        decoded = json.loads(text)
    except ValueError:
        return text
    if isinstance(decoded, list):
        parts = [str(item) for item in decoded if item]
        return "; ".join(parts) if parts else text
    return text


def _rejected_entries(payload: dict) -> list[dict[str, str]]:
    """Read ``updateFieldsValues.userErrors`` into ``{field_id, message}`` rows.

    ``UserError.field`` is ``[String!]``, a path whose last element is the field
    id the entry named (``["values", "fieldId", "contact_email"]``). An entry
    whose path is empty keeps an empty ``field_id`` so the message still reaches
    the caller.
    """
    block = payload.get("updateFieldsValues")
    if not isinstance(block, dict):
        return []
    raw_errors = block.get("userErrors")
    if not isinstance(raw_errors, list):
        return []

    rows: list[dict[str, str]] = []
    for item in raw_errors:
        if not isinstance(item, dict):
            continue
        path = item.get("field")
        field_id = ""
        if isinstance(path, list) and path:
            field_id = str(path[-1])
        elif isinstance(path, str):
            field_id = path
        rows.append(
            {
                "field_id": field_id,
                "message": _decode_user_error_message(item.get("message", "")),
            }
        )
    return rows


def _applied_candidate_ids(
    requested_ids: list[str], rejected: list[dict[str, str]]
) -> list[str]:
    """Ids that might have been written: requested minus named rejections.

    Any unattributed ``userErrors`` row (empty or missing ``field_id``) fail-closes
    the set: a pre-filled field on the card is not evidence this batch wrote it.
    """
    if any(not entry.get("field_id") for entry in rejected):
        return []
    rejected_ids = {entry["field_id"] for entry in rejected}
    return [fid for fid in requested_ids if fid not in rejected_ids]


def _filled_field_ids(readback: dict) -> set[str]:
    """Field ids present on the card after the write.

    ``card.fields`` lists filled fields only, so absence here means the value did
    not land.
    """
    card = readback.get("card")
    if not isinstance(card, dict):
        return set()
    fields = card.get("fields")
    if not isinstance(fields, list):
        return set()

    present: set[str] = set()
    for item in fields:
        if not isinstance(item, dict):
            continue
        definition = item.get("field")
        if isinstance(definition, dict) and definition.get("id") is not None:
            present.add(str(definition["id"]))
    return present


class CardService:
    """Service for Card-related operations."""

    def __init__(self, *, executor: GraphQLExecutor) -> None:
        self._executor = executor

    async def create_card(
        self,
        pipe_id: str | int,
        fields: dict[str, Any] | list[dict[str, Any]],
        *,
        phase_id: str | int | None = None,
        title: str | None = None,
    ) -> dict:
        """Create a card in the specified pipe with the given fields."""
        card_input: dict[str, Any] = {
            "pipe_id": str(pipe_id),
            "fields_attributes": convert_fields_to_array(fields),
        }
        if phase_id is not None:
            card_input["phase_id"] = str(phase_id)
        if title is not None:
            card_input["title"] = title
        return await self._executor.execute_query(
            CREATE_CARD_MUTATION, {"input": card_input}
        )

    async def create_comment(self, card_id: str | int, text: str) -> dict:
        """Create a text comment on the specified card."""
        variables = {"input": {"card_id": str(card_id), "text": text}}
        return await self._executor.execute_query(CREATE_COMMENT_MUTATION, variables)

    async def update_comment(self, comment_id: str | int, text: str) -> dict:
        """Update an existing comment by its ID. Returns raw GraphQL response (see issue #23)."""
        variables = {"input": {"id": str(comment_id), "text": text}}
        return await self._executor.execute_query(UPDATE_COMMENT_MUTATION, variables)

    async def delete_comment(self, comment_id: str | int) -> dict:
        """Delete a comment by its ID. Returns raw GraphQL response (see issue #23)."""
        variables = {"input": {"id": str(comment_id)}}
        return await self._executor.execute_query(DELETE_COMMENT_MUTATION, variables)

    async def delete_card(self, card_id: str | int) -> dict:
        """Delete a card by its ID."""
        variables = {"input": {"id": str(card_id)}}
        return await self._executor.execute_query(DELETE_CARD_MUTATION, variables)

    async def get_card_relations(self, card_id: str | int) -> dict:
        """Load parent and child relations for a card (full lists; no pagination)."""
        variables = {"cardId": str(card_id)}
        return await self._executor.execute_query(GET_CARD_RELATIONS_QUERY, variables)

    async def get_card(self, card_id: str | int, include_fields: bool = False) -> dict:
        """Get a card by its ID.

        Args:
            card_id: The ID of the card.
            include_fields: If True, include the card's custom fields (name, value) in the response.
        """
        variables = {"card_id": str(card_id), "includeFields": include_fields}
        return await self._executor.execute_query(GET_CARD_QUERY, variables)

    async def get_cards(
        self,
        pipe_id: str | int,
        search: CardSearch | None = None,
        include_fields: bool = False,
        *,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        """Get cards in the pipe with optional pagination.

        Args:
            pipe_id: The ID of the pipe.
            search: Optional search filters.
            include_fields: If True, include each card's custom fields (name, value) in the response.
            first: Max cards to return per page.
            after: Cursor for fetching the next page (from ``pageInfo.endCursor``).
        """
        variables: dict[str, Any] = {
            "pipe_id": str(pipe_id),
            "search": {},
            "includeFields": include_fields,
        }
        if search is not None:
            variables["search"] = search
        if first is not None:
            variables["first"] = first
        if after is not None:
            variables["after"] = after
        return await self._executor.execute_query(GET_CARDS_QUERY, variables)

    async def find_cards(
        self,
        pipe_id: str | int,
        field_id: str,
        field_value: str,
        include_fields: bool = False,
        *,
        first: int | None = None,
        after: str | None = None,
    ) -> dict:
        """Find cards in the pipe where the given field equals the given value.

        Args:
            pipe_id: The ID of the pipe to search in.
            field_id: Pipefy field identifier (e.g. from get_start_form_fields or get_phase_fields).
            field_value: Value to match for that field (string; use format expected by field type).
            include_fields: If True, include each card's custom fields (name, value) in the response.
            first: Max cards per page (optional).
            after: Cursor from ``pageInfo.endCursor`` for the next page (optional).
        """
        variables: dict[str, Any] = {
            "pipeId": str(pipe_id),
            "search": {"fieldId": field_id, "fieldValue": field_value},
            "includeFields": include_fields,
        }
        if first is not None:
            variables["first"] = first
        if after is not None:
            variables["after"] = after
        return await self._executor.execute_query(FIND_CARDS_QUERY, variables)

    async def move_card_to_phase(
        self, card_id: str | int, destination_phase_id: str | int
    ) -> dict:
        """Move a card to a specific phase.

        Args:
            card_id: The ID of the card to move.
            destination_phase_id: The ID of the destination phase.
        """
        variables = {
            "input": {
                "card_id": str(card_id),
                "destination_phase_id": str(destination_phase_id),
            }
        }
        return await self._executor.execute_query(
            MOVE_CARD_TO_PHASE_MUTATION, variables
        )

    async def update_card_field(
        self, card_id: str | int, field_id: str, new_value: Any
    ) -> dict:
        """Update a single field of a card.

        Args:
            card_id: The ID of the card containing the field to update.
            field_id: The ID of the field to update.
            new_value: The new value for the field (string, number, list, etc.).

        Returns:
            dict: GraphQL response with success status and updated card information.
        """
        variables = {
            "input": {
                "card_id": str(card_id),
                "field_id": field_id,
                "new_value": new_value,
            }
        }
        return await self._executor.execute_query(UPDATE_CARD_FIELD_MUTATION, variables)

    async def update_card(
        self,
        card_id: str | int,
        title: str | None = None,
        assignee_ids: list[str | int] | None = None,
        label_ids: list[str | int] | None = None,
        due_date: str | None = None,
        field_updates: list[dict] | None = None,
    ) -> dict:
        """Update a card's fields and attributes with intelligent mutation selection.

        This method automatically chooses between two modes based on parameters:

        **Attribute Mode** (uses `updateCard` mutation):
        For updating card attributes like title, assignees, labels, due_date.

        **Field Mode** (uses `updateFieldsValues` mutation):
        For updating custom fields via field_updates list.

        The two modes are exclusive: if field_updates is present, Field Mode
        runs and title, assignee_ids, label_ids, and due_date are discarded.

        If field_updates is empty or omitted, only card attributes will be updated.
        """
        if field_updates:
            return await self._execute_update_fields_values(card_id, field_updates)

        return await self._execute_update_card(
            card_id=card_id,
            title=title,
            assignee_ids=assignee_ids,
            label_ids=label_ids,
            due_date=due_date,
        )

    async def _execute_update_card(
        self,
        card_id: str | int,
        title: str | None,
        assignee_ids: list[str | int] | None,
        label_ids: list[str | int] | None,
        due_date: str | None,
    ) -> dict:
        """Execute updateCard mutation for card attributes (title, assignees, labels, due_date)."""
        input_data: dict[str, Any] = {"id": str(card_id)}

        if title is not None:
            input_data["title"] = title
        if assignee_ids is not None:
            input_data["assignee_ids"] = assignee_ids
        if label_ids is not None:
            input_data["label_ids"] = label_ids
        if due_date is not None:
            input_data["due_date"] = due_date

        variables = {"input": input_data}
        return await self._executor.execute_query(UPDATE_CARD_MUTATION, variables)

    async def _execute_update_fields_values(
        self, card_id: str | int, values: list[dict]
    ) -> dict:
        """Execute updateFieldsValues mutation (incremental mode).

        Raises:
            PartialCardUpdateError: When the payload carries ``userErrors``. The
                mutation validates each entry in ``values`` separately, so this
                covers both the batch that wrote nothing and the batch that
                wrote part of itself; the re-read tells them apart.
        """
        formatted_values = convert_values_to_camel_case(values)
        variables = {"input": {"nodeId": str(card_id), "values": formatted_values}}
        payload = await self._executor.execute_query(
            UPDATE_FIELDS_VALUES_MUTATION, variables
        )

        rejected = _rejected_entries(payload)
        if not rejected:
            return payload

        requested_ids = [
            str(entry["fieldId"]) for entry in formatted_values if entry.get("fieldId")
        ]
        await self._raise_partial_card_update(
            card_id=str(card_id),
            candidate_ids=_applied_candidate_ids(requested_ids, rejected),
            rejected=rejected,
        )

    async def _raise_partial_card_update(
        self,
        *,
        card_id: str,
        candidate_ids: list[str],
        rejected: list[dict[str, str]],
    ) -> NoReturn:
        """Confirm which candidates actually persisted, then raise.

        ``updatedNode`` on the mutation payload is not consulted: it has been
        observed omitting a field that a follow-up read showed had been written.
        """
        try:
            readback = await self._executor.execute_query(
                GET_CARD_FIELD_IDS_QUERY, {"card_id": card_id}
            )
        except Exception:  # noqa: BLE001 - the mutation outcome is the story, not this read
            raise PartialCardUpdateError(
                card_id=card_id,
                applied_field_ids=[],
                rejected=rejected,
                verified=False,
            ) from None

        present = _filled_field_ids(readback)
        raise PartialCardUpdateError(
            card_id=card_id,
            applied_field_ids=[fid for fid in candidate_ids if fid in present],
            rejected=rejected,
        )
