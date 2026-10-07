# Pipes & Cards

Read, create, update, and delete pipes, phases, phase fields, labels, cards, and field conditions. For the ids that the card relation tools take, see [Identifiers](identifiers.md#organization-portal-relations-reports).

## Cross-cutting patterns

- **Field types** are not validated locally — use `introspect_type` (e.g. on `CreatePhaseFieldInput`) for allowed values.
- Successful mutations return a structured `result` (GraphQL payload).
- Most write tools support optional `debug=true` on errors (GraphQL codes + `correlation_id`).
- `extra_input` merges extra API keys (camelCase); keys that would duplicate primary arguments are ignored.
- **Destructive deletes** (`delete_pipe`, `delete_card`, and the other deletes in this guide) follow [Destructive operations](cross-cutting.md#destructive-operations): echo `confirmation_token` from the preview with `confirm=true`.

### Pipefy IDs (type safety)

Which **form** each tool wants (slug vs `internal_id` vs uuid vs numeric id) is the canonical [Identifiers map](identifiers.md#field-references-slug-vs-internal_id); this section covers string-vs-int type safety and coercion.

Pipefy’s GraphQL API uses **string** IDs for pipes, phases, cards, and most other nodes.

- **Prefer string arguments** when calling tools (e.g. `card_id: "1332881010"`, `pipe_id: "306996634"`). This matches API responses (`get_pipe`, `get_card`, `create_card`, etc.).
- **Integer JSON values** (e.g. `1332881010` without quotes) are still accepted on many tools: they are **coerced to strings** before variables are sent to GraphQL, so behavior matches the API.
- **Validation:** empty strings, whitespace-only IDs, and non-positive numeric IDs are rejected with a clear tool error (no spurious `ValueError` from type mixing).
- **`delete_card`:** `card_id` follows the same rule — use a **string** (recommended) or a positive integer; the tool normalizes to a string for `getCard` / `deleteCard`. On success, `card_id` in the payload is a **string**.

---

## Cards and phases

**Choosing card updates:** `update_card` + `field_updates` = several custom fields at once (prefer `operation` ADD/REMOVE for list-valued fields: connections, attachments, checklists). Pipe labels and assignees are card attributes (`label_ids` / `assignee_ids`, replace-all), not fields — `field_updates` cannot address them. `update_card_field` = one field, full replacement of the entire list — for connectors that means related-card **ids**; `get_card` field `value` is display titles only, so do not rebuild from it (read ids via `get_card_relations`, or GraphQL `array_value`). `update_card` with attribute args = metadata. The two modes are exclusive: if `field_updates` is present, `title` / `assignee_ids` / `label_ids` / `due_date` are discarded.

### Headless / agent clients

`create_card` and `fill_card_phase_fields` ask for missing field values when they can. Three things stop them: the client declares no elicitation capability, the caller passes `skip_elicitation=true`, or the connection carries no server-initiated request, which is how these tools ask today. They therefore never ask on protocol revision **2026-07-28**, whatever the transport, or on a deployment that answers a POST as plain JSON rather than SSE, which **the hosted server** does. A deployment you run yourself keeps SSE, so these tools ask there.

When they cannot ask, both tools still work:

1. The tool fetches the start-form or phase field definitions internally.
2. For `create_card`, provided `fields` are **filtered to editable field IDs only** — keys that do not match an editable field are silently discarded (no error). The filtered dict is sent directly to the Pipefy API.
3. For `fill_card_phase_fields`, keys the phase does not expose as editable are returned in `skipped_field_ids`. When nothing survives the filter, nothing is written.

Agents should discover fields first and pass all required values explicitly:

```text
get_start_form_fields(pipe_id)   → learn field IDs, types, required flag
create_card(pipe_id, fields={…}) → supply every required field ID

get_pipe(pipe_id)                → phases[].id / cards_count for workflow inventory
create_card(
  pipe_id,
  phase_id="340012345",
  skip_elicitation=true,
  title="Seeded card",
  fields={…},
)                                → card created in that phase (fields via get_phase_fields + get_start_form_fields)

get_phase_fields(phase_id)                     → learn phase field IDs
fill_card_phase_fields(card_id, phase_id, fields={…}) → supply values
pipefy card fill <card_id> --phase <phase_id> --fields '{"…"}'  → CLI equivalent (non-interactive)
```

With `phase_id`, interactive clients may still elicit start-form fields when elicitation is supported; set `skip_elicitation=true` for agent workflows. When `fields` is non-empty, keys are filtered against both `get_phase_fields(phase_id)` and `get_start_form_fields(pipe_id)` so pipes that still require start-form values on `CreateCardInput` receive them alongside phase fields. Optional `title` is sent on `CreateCardInput` (no separate `update_card` on the happy path).

### `get_pipe` inventory fields

MCP tool results use the standard envelope; inventory fields live under the `pipe` object:

| JSON path | Meaning |
|-----------|---------|
| `pipe.start_form_fields` | Start-form field definitions (intake) |
| `pipe.phases[].id` | Workflow phase IDs (start form excluded) |
| `pipe.phases[].name` | Phase display name |
| `pipe.phases[].index` | Float sort key; `phases[]` is in ascending key order (see `create_phase`) |
| `pipe.phases[].cards_count` | Native card count for that workflow phase |

CLI `pipefy pipe get <pipe_id> --json` returns the same GraphQL shape.

### Phase inventory (`get_phase_cards_count` / `get_phase_cards`)

Use these when you need per-phase totals or card lists without pipe-wide `CardSearch`:

| Tool | CLI | When to use |
|------|-----|-------------|
| `get_phase_cards_count` | `pipefy phase count <phase_id>` | Quick scalar; empty phases for seeding. |
| `get_phase_cards` | `pipefy phase cards <phase_id> --first 50 --after <cursor>` | Verify cards after create/move; paginate with `pageInfo.endCursor`. |

Discovery path: `get_pipe(pipe_id)` → `phases[].id` for workflow phases; omit `phase_id` on `create_card` for start-form intake.

```text
get_phase_cards_count(phase_id="340012345")
get_phase_cards(phase_id="340012345", first=50, include_fields=true)
```

### Phase transitions (`get_phase_allowed_move_targets`)

Outbound moves are constrained by UI-configured connections — there is no API to add edges.

1. Resolve source phase: `get_card(card_id).current_phase.id` (or known `phase_id` before move).
2. `get_phase_allowed_move_targets(phase_id=<source>)` → `allowed_phases` (`{id, name}`).
3. `move_card_to_phase(card_id, destination_phase_id=<allowed id>)`.

CLI: `pipefy phase targets <phase_id> --json`.

Empty `allowed_phases` means no outbound transitions are configured in the UI.

## Field condition tools

These tools read and configure conditional visibility on phase fields.

- `create_field_condition` maps to `createFieldConditionInput`: `phase_id`, `condition`, `actions`.
- Action entries use `phaseFieldId` with the target field's `internal_id` from `get_phase_fields` (not the slug `id`).
- The tool rejects an empty `condition`, an empty `expressions` list, and slug-like `phaseFieldId` values.
- Use `introspect_type('createFieldConditionInput')` / `UpdateFieldConditionInput` for optional keys in `extra_input`.

## Notes

- `upload_attachment_to_card`: a `field_id` given as the field uuid returns `RESOURCE_NOT_FOUND`. Pass the field slug.
- `upload_attachment_to_card`: when `file_url` has no basename, pass `file_name` explicitly.

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/mcp/tools/pipes-and-cards.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/mcp/tools/pipes-and-cards.md).
