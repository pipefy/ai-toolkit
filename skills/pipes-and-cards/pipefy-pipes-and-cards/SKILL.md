---
name: pipefy-pipes-and-cards
description: >
  Use this skill when the user wants to read, create, update, or delete
  pipes, phases, phase fields, labels, cards, comments, or field conditions.
  Covers 40 operations for the core pipe and card lifecycle. Use the
  seed-pipe-across-phases workflow when populating empty phases for demos or QA.
tags: [pipefy, pipes, cards, phases, fields, labels, comments, field-conditions]
---

# Pipes & Cards

Read only the reference for your active surface: [MCP](references/mcp.md) or [CLI](references/cli.md). The workflows below use shared operation names and arguments.

Read, create, update, and delete pipes, phases, phase fields, labels, cards, attachments, and field conditions. **40 operations.**

---

## Cross-cutting patterns

- **Field types** are not validated locally — use `introspect_type` (e.g., on `CreatePhaseFieldInput`) for allowed values.

- `extra_input` merges extra API keys (camelCase); keys that duplicate primary arguments are ignored.
- **Phase connections are UI-only.** Creating or reordering phases does not wire Phase Connections / `allowed_phases`. Configure edges in the Pipefy UI; use `get_phase_allowed_move_targets` before moves. The API cannot add transition edges.
- **Verify-after-write.** After create/update, re-read with the matching get tool (`get_pipe`, `get_card`, `get_phase_fields`, etc.) before reporting success. Do not treat the write response alone as proof.

---

## Pipe operations

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_pipe` | Yes | Fetch pipe metadata including phases and fields. |
| `search_pipes` | Yes | Search by name pattern. |
| `create_pipe` | No | Create a new pipe in the org. |
| `update_pipe` | No | Rename or change pipe settings. |
| `delete_pipe` | No | Destructive delete. |
| `clone_pipe` | No | Clone an existing pipe. |
| `get_pipe_members` | Yes | List members of a pipe. |

### Steps — create a pipe with phases

1. **Create the pipe:**

   `create_pipe name="Customer Onboarding" organization_id=123`

2. **Add phases** — call `create_phase` for each phase (see Phase section below). Omit `index` to append after existing workflow phases, or pass a **1-based** `index` to insert among phases returned by `get_pipe`. Prefer `1` or higher; `index: 0` creates a phase that does not appear in `get_pipe`'s `phases` list. `index` only controls order — it does **not** wire Phase Connections / `allowed_phases` (configure those in the Pipefy UI; use `get_phase_allowed_move_targets` before moves).

3. **Add start form fields** — call `create_phase_field` on the start form phase.

---

## Phase operations

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_pipe` | Yes | Read phase metadata from the pipe response. |
| `create_phase` | No | Add a phase to a pipe. |
| `update_phase` | No | Rename, reorder, set done flag. |
| `delete_phase` | No | Destructive delete. |
| `get_phase_allowed_move_targets` | Yes | Valid destination phases before `move_card_to_phase` (UI-configured edges only). |
| `get_phase_cards_count` | Yes | Native per-phase card count via `get_phase`. |
| `get_phase_cards` | Yes | Paginated cards in a phase. |

---

## Seed pipe across phases

Use this workflow to place at least one card in each workflow phase (demos, QA checklists, chaos pipes) **without** `execute_graphql`. Transition edges must already exist in the Pipefy UI.

### Tools needed

| Operation | Read-only |
| ------------ | ----------- |
| `get_pipe` | Yes |
| `get_phase_cards_count` | Yes |
| `create_card` | No |
| `get_phase_cards` | Yes |
| `get_phase_allowed_move_targets` | Yes |
| `move_card_to_phase` | No |

Before `move_card_to_phase`, call `get_phase_allowed_move_targets`. Required empty fields may prevent a move.

### Steps

1. **Load phase IDs** — `get_pipe(pipe_id)` → collect `phases[].id` for workflow phases. Omit `phase_id` on `create_card` for start-form intake.

   `get_pipe pipe_id="306996634"`

2. **Find empty phases** — for each candidate `phase_id`, call `get_phase_cards_count`. Target phases where `cards_count` is 0 (if the start form shows 0 but you suspect cards, call `get_phase_cards` before creating duplicates).

   `get_phase_cards_count phase_id="340012345"`

3. **Create cards in empty phases** — loop `create_card` with `phase_id`. When `fields` is non-empty, keys are filtered via `get_phase_fields(phase_id)` and `get_start_form_fields(pipe_id)`.

   ```
   create_card pipe_id="306996634" phase_id="340012345" title="Seeded"
   ```

4. **Verify inventory** — `get_phase_cards(phase_id, first=50)` and confirm expected card IDs/titles.

5. **Before moves** — on the card's current phase, `get_phase_allowed_move_targets` then `move_card_to_phase` only to an `allowed_phases[].id`.

   `get_phase_allowed_move_targets phase_id="<current_phase_id>"`

### Success criteria

- Every targeted phase reports `cards_count >= 1` (or `get_phase_cards` lists the seeded cards).
- Moves use only phases returned in `allowed_phases`.

### Failure modes

- **Empty `allowed_phases`:** configure **Phase → Connections** in the Pipefy UI; the API cannot add edges.
- **Unexpected empty count:** use `get_phase_cards` to list cards before creating duplicates.

---

## Phase field operations

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_phase_fields` | Yes | List fields on a phase. |
| `get_start_form_fields` | Yes | List start-form fields for card creation. |
| `create_phase_field` | No | Add field to a phase. |
| `update_phase_field` | No | Rename, reorder, change required flag. |
| `delete_phase_field` | No | Destructive delete. |

**Discover field types:**

`introspect_type type_name="CreatePhaseFieldInput"`

This returns valid `type` enum values and their descriptions.

---

## Card operations

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_card` | Yes | Title, phase, pipe, optional fields. Does not return labels or assignees. |
| `get_cards` | Yes | Paginated card list by pipe. |
| `find_cards` | Yes | Filter by a single field value. |
| `create_card` | No | Default: start form. Optional `phase_id` creates in that phase. |
| `fill_card_phase_fields` | No | Fill phase fields; filters to editable IDs. |
| `update_card` | No | Update title, assignees, labels, due date, or fields. For list-valued **fields** (connections, attachments, checklists), prefer `field_updates` with `operation` ADD/REMOVE. Pipe labels and assignees are card attributes (`label_ids` / `assignee_ids`, replace-all), not fields — see Label operations. If `field_updates` is set, attribute args are discarded. For connectors, send related **card ids**. |
| `update_card_field` | No | Single-field `updateCardField`; list-valued fields are **replace-all**. For connectors, values are related **card ids** (not display titles). Do not rebuild from `get_card` `value` (titles only); read ids via `get_card_relations`. Prefer `update_card` + ADD/REMOVE for fields. Pipe labels use `label_ids`, not this tool. |
| `move_card_to_phase` | No | Call `get_phase_allowed_move_targets` first; required empty fields may block the move. |
| `delete_card` | No | Destructive delete. |
| `add_card_comment` | No | Add a text comment to a card. |
| `update_comment` | No | Update an existing card comment. |
| `delete_comment` | No | Destructive delete. |
| `upload_attachment_to_card` | No | Attach a file to an attachment field (`field_id` = slug). See `pipefy-attachments`. |

### Steps — create a card

1. **Get start form fields** (required — never skip):

   `get_start_form_fields pipe_id=67890`

2. **Create the card with fields:**

   ```
   create_card pipe_id=67890 title="My Card" fields_attributes='[{"field_id":"field_slug","field_value":"value"}]'
   ```

3. **Report result** with card ID and link: `https://app.pipefy.com/open-cards/<CARD_ID>`

### Pagination for get_cards

```
get_cards pipe_id=67890 first=50 after=<endCursor>
```

Read `pageInfo.hasNextPage` and `pageInfo.endCursor` from the response; pass `after=<endCursor>` for the next page.

---

## Label operations

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_labels` | Yes | List pipe labels. |
| `create_label` | No | Create a label with a color. |
| `update_label` | No | Rename or recolor. |
| `delete_label` | No | Destructive delete. |

These tools manage label definitions on the pipe. Applying a pipe label to a card is `update_card(label_ids=[...])`, which **replaces** the card's whole label list: include every id that should remain; do not send only the new one. `get_card` does not return labels — read current ids via `execute_graphql` (`card(id: ...) { labels { id } }`), merge, then write. `field_updates` with `operation` ADD/REMOVE is for list-valued **fields**, not for card-attribute labels. When the user wants a label applied **automatically** ("mark it late when it goes past the due date"), stop and read `pipefy-automations` (applying a label has no automation action): no automation action does it, and driving `update_card` over a set of cards makes the agent the runtime instead of the process.

---

## Field condition operations

| Operation | Purpose |
| ------------ | --------- |
| `get_field_conditions` | List all field conditions on a phase. |
| `get_field_condition` | Load one field condition by ID. |
| `create_field_condition` | Create show/hide rule. Verify that the rule is on the requested phase before reporting success. |
| `update_field_condition` | Update condition action or rule. |
| `delete_field_condition` | Destructive delete. |

Do not hide a required field; clear `required` first.

---

## Success criteria

- Pipe and phases visible in Pipefy UI.
- `get_pipe` returns the new pipe ID and phases.
- Cards created via `create_card` appear in the pipe's first phase.

## Failure modes

- **`create_field_condition` fails with missing/wrong phase:** delete the returned condition before recreating; do not blind-retry create on the same requested phase.
- **`create_card` fails with missing required fields:** call `get_start_form_fields` first to discover required `field_id` values.
- **`create_card` / write reports failure (empty or unclear message):** do not blind-retry. Re-read `get_cards` / `get_phase_cards_count` (or pipe `cards_count`) before any retry — see `pipefy-api-fallback` (ambiguous write failure re read before retry).
- **Connections missing after a connector field update:** `update_card_field` is replace-all — writing one related card id drops the rest (same replace-all applies to other list-valued fields: attachments, checklists). Prefer `update_card` with `operation` ADD/REMOVE and related **card ids**. Do not rebuild a full list from `get_card` `value` (display titles only); for REMOVE or a safe full rewrite, get current related-card ids from `get_card_relations` (or GraphQL `array_value`). For *writes* via a pipe relation (not a connector field), use `create_card_relation` / `delete_card_relation` — see `pipefy-relations`. Pipe labels and assignees are not fields: use `update_card(label_ids=)` / `assignee_ids` (replace-all); `field_updates` ADD cannot address them.
- **`create_phase_field` rejects type:** call `introspect_type type_name="CreatePhaseFieldInput"` to get valid values.

## See also

- `pipefy-relations` — link pipes and cards across workflows.
- `pipefy-automations` — add automation rules to a pipe.
- `pipefy-introspection` — discover field types and mutation signatures.
- [docs/mcp/tools/identifiers.md#field-references-slug-vs-internal_id](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/identifiers.md#field-references-slug-vs-internal_id) — canonical map of which tool/argument expects slug vs `internal_id` vs uuid vs numeric id (e.g. `update_card_field` uses a field slug).
