# Connections & Relations

Link processes and cards across workflows.

## Key concepts

- **Pipe relations** define parent/child structure between pipes (who connects to whom, constraints, auto-fill). Use `get_pipe_relations` on a pipe to list relation IDs and metadata.
- **Card relations** connect individual cards through an existing pipe relation: pass `source_id` = that pipe relation's ID (from `get_pipe_relations`). Default `sourceType` is `PipeRelation`; use `extra_input` (e.g. `sourceType: Field`) when the API requires a field-based link — see `introspect_type` on `CreateCardRelationInput`. The GraphQL `Card` type exposes **`child_relations`** and **`parent_relations`** (snake_case); the MCP maps them to tool output keys of the same shape.
- **Table relations** in GraphQL are loaded by table-relation ID, not by database table ID: `get_table_relations` takes a non-empty list of those IDs (root `table_relations` query).

## Common mistakes (agents)

- **`get_table_relations` + `table_id`:** The tool argument is `relation_ids` (table **relation** IDs). The database table id from `search_tables` / `get_table` is the wrong kind of id — the MCP client may reject the call or GraphQL will not find what you expect.
- **`create_card_relation` + wrong `source_id`:** `source_id` must be a **pipe relation** id from `get_pipe_relations`. It is not a table-relation id, not a `table_id`, and not a pipe/card id.
- **Symmetry trap:** `get_pipe_relations(pipe_id)` takes a pipe id, but `get_table_relations(relation_ids)` does **not** take a table id — the APIs differ by design.
