"""GraphQL operations for Pipefy pipe, table, and card relations.

``CreatePipeRelationInput`` / ``UpdatePipeRelationInput`` require all boolean flags. Create fills
the ones the caller leaves out from ``_PIPE_RELATION_CONSTRAINT_DEFAULTS``; update fills them from
the relation's current values. ``CreateCardRelationInput.sourceType`` is
``PipeRelation`` | ``Field`` (default constant: PipeRelation).

Merged ``**attrs`` / ``extra_input``: ``None`` values are omitted from GraphQL input (leave
unchanged on the server). Explicit API null to clear a field is not supported — same as
``PipeConfigService`` / ``TableService``.
"""

from __future__ import annotations

from typing import Any

from pipefy_sdk.graphql_executor import GraphQLExecutor
from pipefy_sdk.queries.relation_queries import (
    CREATE_CARD_RELATION_MUTATION,
    CREATE_PIPE_RELATION_MUTATION,
    DELETE_PIPE_RELATION_MUTATION,
    GET_PIPE_RELATION_CONSTRAINTS_QUERY,
    GET_PIPE_RELATIONS_QUERY,
    GET_TABLE_RELATIONS_QUERY,
    INTERNAL_DELETE_CARD_RELATION_MUTATION,
    UPDATE_PIPE_RELATION_MUTATION,
)

_PIPE_RELATION_CONSTRAINT_DEFAULTS: dict[str, Any] = {
    "allChildrenMustBeDoneToFinishParent": False,
    "allChildrenMustBeDoneToMoveParent": False,
    "autoFillFieldEnabled": False,
    "canConnectExistingItems": True,
    "canConnectMultipleItems": True,
    "canCreateNewItems": True,
    "childMustExistToFinishParent": False,
    "childMustExistToMoveParent": False,
}

_DEFAULT_CARD_RELATION_SOURCE_TYPE = "PipeRelation"


class RelationService:
    """Reads and mutations for pipe relations, table relations (by relation ID), and card links."""

    def __init__(
        self,
        *,
        executor: GraphQLExecutor,
        internal_executor: GraphQLExecutor,
    ) -> None:
        self._executor = executor
        self._internal_executor = internal_executor

    async def get_pipe_relations(self, pipe_id: str | int) -> dict[str, Any]:
        """Fetch parent and child pipe relations for a pipe (`parentsRelations`, `childrenRelations`).

        Args:
            pipe_id: Pipe ID.
        """
        return await self._executor.execute_query(
            GET_PIPE_RELATIONS_QUERY,
            {"pipeId": str(pipe_id)},
        )

    async def get_table_relations(
        self, relation_ids: list[str | int]
    ) -> dict[str, Any]:
        """Batch-fetch table relations by ID (root `table_relations` query).

        Args:
            relation_ids: One or more **table relation** IDs (not the database table ID).
        """
        return await self._executor.execute_query(
            GET_TABLE_RELATIONS_QUERY,
            {"ids": [str(r) for r in relation_ids]},
        )

    async def create_pipe_relation(
        self,
        parent_id: str | int,
        child_id: str | int,
        name: str,
        **attrs: Any,
    ) -> dict[str, Any]:
        """Create a parent-child pipe relation (`CreatePipeRelationInput`).

        Args:
            parent_id: Parent pipe ID.
            child_id: Child pipe ID.
            name: Relation label.
            **attrs: Extra `CreatePipeRelationInput` fields (camelCase keys), e.g. ``ownFieldMaps``.
        """
        input_obj: dict[str, Any] = {
            "parentId": str(parent_id),
            "childId": str(child_id),
            "name": name,
            **_PIPE_RELATION_CONSTRAINT_DEFAULTS,
        }
        for key, value in attrs.items():
            if value is not None:
                input_obj[key] = value
        return await self._executor.execute_query(
            CREATE_PIPE_RELATION_MUTATION,
            {"input": input_obj},
        )

    async def update_pipe_relation(
        self,
        relation_id: str | int,
        name: str,
        **attrs: Any,
    ) -> dict[str, Any]:
        """Update a pipe relation (`UpdatePipeRelationInput`).

        The API requires every constraint flag on update, so the flags the caller
        leaves out are read from the relation and sent back unchanged. ``ownFieldMaps``
        is optional on the API, which keeps the current maps when it is omitted.

        Args:
            relation_id: Pipe relation ID.
            name: Relation name (required by the API).
            **attrs: Extra `UpdatePipeRelationInput` fields (camelCase keys), overriding
                the relation's current flags.

        Raises:
            ValueError: No pipe relation has ``relation_id``.
        """
        input_obj: dict[str, Any] = {
            "id": str(relation_id),
            "name": name,
            **await self._current_constraint_flags(relation_id),
        }
        for key, value in attrs.items():
            if value is not None:
                input_obj[key] = value
        return await self._executor.execute_query(
            UPDATE_PIPE_RELATION_MUTATION,
            {"input": input_obj},
        )

    async def _current_constraint_flags(self, relation_id: str | int) -> dict[str, Any]:
        """Read the relation's constraint flags, keyed like ``UpdatePipeRelationInput``."""
        data = await self._executor.execute_query(
            GET_PIPE_RELATION_CONSTRAINTS_QUERY,
            {"ids": [str(relation_id)]},
        )
        relations = data.get("pipe_relations") or []
        if not relations:
            msg = f"Pipe relation '{relation_id}' was not found."
            raise ValueError(msg)
        current = relations[0]
        return {flag: current[flag] for flag in _PIPE_RELATION_CONSTRAINT_DEFAULTS}

    async def delete_pipe_relation(self, relation_id: str | int) -> dict[str, Any]:
        """Delete a pipe relation by ID (permanent).

        Args:
            relation_id: Pipe relation ID.
        """
        return await self._executor.execute_query(
            DELETE_PIPE_RELATION_MUTATION,
            {"input": {"id": str(relation_id)}},
        )

    async def create_card_relation(
        self,
        parent_id: str | int,
        child_id: str | int,
        source_id: str | int,
        **attrs: Any,
    ) -> dict[str, Any]:
        """Connect two cards via a pipe relation (`CreateCardRelationInput`).

        Args:
            parent_id: Parent card ID.
            child_id: Child card ID.
            source_id: Pipe relation ID (from ``get_pipe_relations`` / ``parentsRelations`` / ``childrenRelations``).
            **attrs: Optional overrides, e.g. ``sourceType`` (default ``PipeRelation``; API also allows ``Field``).
        """
        input_obj: dict[str, Any] = {
            "parentId": str(parent_id),
            "childId": str(child_id),
            "sourceId": str(source_id),
            "sourceType": _DEFAULT_CARD_RELATION_SOURCE_TYPE,
        }
        for key, value in attrs.items():
            if value is not None:
                input_obj[key] = value
        return await self._executor.execute_query(
            CREATE_CARD_RELATION_MUTATION,
            {"input": input_obj},
        )

    async def delete_card_relation(
        self,
        child_id: str | int,
        parent_id: str | int,
        source_id: str | int,
    ) -> dict[str, Any]:
        """Delete a relation link between two cards (Internal API, requires OAuth).

        The ``deleteCardRelation`` mutation is not exposed on the public GraphQL
        schema, only on the Internal API (core_api / internal_v1), so it routes
        through the injected internal executor rather than the public one.

        Args:
            child_id: Child card ID.
            parent_id: Parent card ID.
            source_id: Pipe relation ID linking the two cards.
        """
        return await self._internal_executor.execute_query(
            INTERNAL_DELETE_CARD_RELATION_MUTATION,
            {
                "childId": str(child_id),
                "parentId": str(parent_id),
                "sourceId": str(source_id),
            },
        )
