---
name: pipefy-relations
description: >
  Use this skill when the user wants to link pipes, tables, or cards across
  workflows — creating or managing pipe relations, table relations, or card
  relations. Covers 8 operations.
tags: [pipefy, relations, connections, pipes, cards, tables]
---

# Connections & Relations

MCP clients: read [references/mcp.md](references/mcp.md). CLI users: read [references/cli.md](references/cli.md). Examples below describe shared operation arguments.

Link processes and cards across workflows. **8 operations.**

---

## Key concepts

- **Pipe relations** define parent/child structure between pipes (who connects to whom, constraints, auto-fill). Use `get_pipe_relations` on a pipe to list relation IDs and metadata.
- **Card relations** connect individual cards through an existing pipe relation: pass `source_id` = the pipe relation's ID (from `get_pipe_relations`). Default `sourceType` is `PipeRelation`; use `extra_input` (e.g., `sourceType: Field`) when the API requires a field-based link — see `introspect_type` on `CreateCardRelationInput`.
- **Table relations** in GraphQL are loaded by table-relation ID, not by database table ID: `get_table_relations` takes a non-empty list of those IDs.
- **Connector fields** are card fields (connection type), not pipe relations for *writes*. Prefer `update_card` + `field_updates` with `operation` ADD/REMOVE (related **card ids**). `update_card_field` is **replace-all** of the full id list; `get_card` `value` is display titles only — do not rebuild from it. This skill's `get_card_relations` still **reads** connector-field links (with card ids). `create_card_relation` / `delete_card_relation` write links through a pipe relation and are incremental — pick the surface that matches the link type.

---

## Tools

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_pipe_relations` | Yes | List pipe-to-pipe relations for a pipe. |
| `create_pipe_relation` | No | Create a new pipe-to-pipe relation. |
| `update_pipe_relation` | No | Change relation config (auto-fill, constraints). |
| `delete_pipe_relation` | No | **Destructive; review and approve first.** |
| `get_table_relations` | Yes | Load table relations by relation ID. |
| `get_card_relations` | Yes | List all card-to-card relations on a card. |
| `create_card_relation` | No | Link two cards through an existing pipe relation. |
| `delete_card_relation` | No | **Destructive; review and approve first.** |

---

## Steps — link two cards via an existing pipe relation

1. **Get the pipe relation ID:**

   Operation: `get_pipe_relations(pipe_id=67890)`

   Note the `id` field on the relation (not the pipe ID).

2. **Create the card relation:**

   Operation: `create_card_relation(source_id=<PIPE_RELATION_ID>, source_card_id=<PARENT_CARD_ID>, target_card_id=<CHILD_CARD_ID>)`

3. **Verify:**

   Operation: `get_card_relations(card_id=<CHILD_CARD_ID>)`

---

## Steps — create a new pipe relation

1. **Create the relation between two pipes:**

   Operation: `create_pipe_relation(parent_pipe_id=111, child_pipe_id=222, name="Support Escalation", auto_fill_field_id=<field_id>)`

2. **Use the relation** — cards in the parent pipe can now be linked to cards in the child pipe using `create_card_relation`.

---

## Success criteria

- `get_pipe_relations` returns the new relation with both pipe IDs.
- `get_card_relations` shows the linked card ID after `create_card_relation`.

## Failure modes

- **`create_card_relation` fails with "relation not found":** `source_id` must be the **pipe relation ID** (from `get_pipe_relations`), not the pipe ID. These are different values.
- **Table relations return empty:** `get_table_relations` requires table-relation IDs, not table IDs. Get table-relation IDs from the table's connection config.
- **Deletion:** show the affected relation and obtain approval before removing it.

## See also

- `pipefy-pipes-and-cards` — create the pipes and cards before linking them; connector field updates and `update_card_field` replace-all live there.
- [`docs/mcp/tools/identifiers.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/identifiers.md) — which args expect slug vs numeric id for field and relation tools.
- `pipefy-introspection` — discover `CreateCardRelationInput` when non-standard `sourceType` is needed.
