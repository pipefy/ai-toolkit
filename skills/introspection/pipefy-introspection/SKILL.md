---
name: pipefy-introspection
description: >
  Use this skill when you need to discover GraphQL type shapes, mutation
  signatures, enum values, or execute arbitrary GraphQL as a fallback.
  This is the first fallback tier (Tier 2) when dedicated operations fail
  or don't exist for an operation. 7 operations.
tags: [pipefy, introspection, graphql, schema, fallback]
---

# Introspection & Raw GraphQL

Read only the reference for your active surface: [MCP](references/mcp.md) or [CLI](references/cli.md). The workflows below use shared operation names and arguments.

Schema discovery, organization info, and a fallback executor. **7 operations.**

This is **Tier 2** in the resolution strategy: when a dedicated operation fails or doesn't exist, use introspection to understand the API, then `execute_graphql` to run the operation directly.

**Tier 1:** dedicated operation exists — use it.
**Tier 2:** use introspection + `execute_graphql` (this skill).
**Tier 3:** direct curl/httpx fallback — see `pipefy-api-fallback`.

---

## Tools

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `introspect_type` | Yes | Type shape: `fields`, `inputFields`, `enumValues`. Optional `max_depth`. |
| `introspect_query` | Yes | Root query arguments and return type. Optional `max_depth`. |
| `introspect_mutation` | Yes | Root mutation arguments and return type. Optional `max_depth`. |
| `search_schema` | Yes | Keyword search on type names/descriptions. Optional `kind` filter. |
| `execute_graphql` | No | Execute arbitrary GraphQL. |
| `get_organization` | Yes | Load organization info (name, plan, UUID, member count, pipe count). |
| `list_organizations` | Yes | List organizations the caller can access — no id required. The zero-knowledge entry point for org discovery. |

---

## `max_depth` (introspect_type / query / mutation)

`max_depth` defaults to `1`.

- **`1`** — type/field info only (no inlined sub-types).
- **`2+`** — resolves referenced input/output types inline (`resolvedType`), so one call can replace introspecting the mutation then each input type separately.

Example:

```
introspect_mutation mutation_name="createCard" max_depth=2
```

Scalars (`ID`, `String`, `Int`, …) are never expanded.

## `kind` on `search_schema`

Optional filter: `OBJECT`, `INPUT_OBJECT`, `ENUM`, `SCALAR`, `INTERFACE`, `UNION`.

```
search_schema keyword="automation" kind="INPUT_OBJECT"
```

---

## When to use introspection

- A dedicated tool returned an error and you need to understand why — introspect the input type to check argument names/types.
- Before creating fields: `introspect_type('CreatePhaseFieldInput')` to discover valid `type` enum values.
- Before using `extra_input`: introspect the corresponding input type to find optional keys.
- Unknown mutation signature: `introspect_mutation('createSomething')` before `execute_graphql`.
- Schema exploration: `search_schema('automation')` to find related types and inputs.

## When to use `execute_graphql`

- No dedicated operation exists for the operation.
- A dedicated tool failed and you've used introspection to understand the correct payload.
- Ad-hoc queries like resolving an org UUID via `pipe(id: $id) { organization { uuid } }`.
- Complex nested queries that no single tool covers.

**Always prefer dedicated operations.** They validate inputs, handle pagination, and format errors consistently. `execute_graphql` is the fallback when dedicated tools can't solve the problem.

---

## Steps — discover a mutation signature

1. **Search for the mutation by keyword:**

   ```
   search_schema keyword="label"
   ```

2. **Get the full mutation signature:**

   ```
   introspect_mutation mutation_name="createLabel"
   ```

3. **Discover input type fields:**

   ```
   introspect_type type_name="CreateLabelInput"
   ```

4. **Execute** `execute_graphql` with the discovered mutation and its variables.

---

## Common fallback recipes

Ready-to-use patterns for situations where dedicated tools are insufficient.

### Recipe 1 — Discover valid field types for `create_phase_field`

```
introspect_type('CreatePhaseFieldInput')
```

Look for the `type` field; it references an enum. Introspect the enum to get all valid values.

### Recipe 2 — Get full behavior config of an AI agent

`get_ai_agent` returns behavior headers only. To inspect the full config (`event_params`, `actionParams`, `actionsAttributes`):

```
execute_graphql query='query($uuid: ID!) { aiAgent(uuid: $uuid) { uuid name instruction behaviors { id name active event_id event_params { to_phase_id triggerFieldIds fromPhaseId } action_params { aiBehaviorParams { instruction referencedFieldIds actionsAttributes { name actionType referenceId metadata { destinationPhaseId pipeId fieldsAttributes { fieldId inputMode value } } } } } } } }' variables='{"uuid":"<agent-uuid>"}'
```

### Recipe 3 — Find a card by title (not possible with `find_cards`)

`find_cards` only searches custom field values. To search by title:

```
execute_graphql query='query($pipeId: ID!, $first: Int) { cards(pipe_id: $pipeId, first: $first) { edges { node { id title current_phase { name } } } } }' variables='{"pipeId":"<pipe-id>","first":50}'
```

Filter by title client-side. For large pipes, paginate with `after`.

### Recipe 4 — Discover what `extra_input` accepts for any mutation

When a tool accepts `extra_input` (e.g. `create_automation`, `update_label`), discover all optional keys:

```
introspect_mutation('createAutomation')     # find the input type name
introspect_type('CreateAutomationInput')    # see all inputFields
```

Compare with the tool's primary arguments to know which keys are additive via `extra_input`.

### Recipe 5 — Discover organization IDs

To answer "which organizations do I have access to?" with nothing in hand, call `list_organizations` — it needs no id and returns each org's `id`, `uuid`, `name`, and your role. That is the entry point; reach for the GraphQL fallbacks below only when you already have a pipe.

When the user only has a pipe ID and needs its `organization_id`:

```
execute_graphql query='query($id: ID!) { pipe(id: $id) { organization { id uuid name } } }' variables='{"id":"<pipe-id>"}'
```

### Recipe 6 — Update a select field's options after creation

`create_phase_field` does not accept options. Create first, then update.

```
execute_graphql query='mutation($id: ID!, $options: [String!]) { updatePhaseField(input: { id: $id, options: $options }) { phase_field { id label options } } }' variables='{"id":"<field-id>","options":["High","Medium","Low"]}'
```

### Recipe 7 — Check phase transition rules

When `move_card_to_phase` fails with "not a valid target phase":

```
execute_graphql query='query($id: ID!) { phase(id: $id) { id name cards_can_be_moved_to_phases { id name } } }' variables='{"id":"<current-phase-id>"}'
```

Returns the valid destination phases from the current phase.

---

## Success criteria

- `introspect_type` returns the complete field list for the input type.
- `execute_graphql` returns the expected data without errors.

## Failure modes

- **`introspect_type` returns `null`** — type name is case-sensitive; try PascalCase (e.g., `CreateLabelInput`, not `create_label_input`).
- **`search_schema` returns many hits** — case-insensitive substring matching; broad keywords like `"card"` flood results. Prefer specific names like `"AiAgent"`, `"FieldCondition"`.
- **`introspect_mutation` is expensive** — fetches all root mutation fields and filters client-side (single large query). Prefer `introspect_type` on the specific input type when you already know the mutation name.
- **`execute_graphql` returns GraphQL errors** — check `path` and `message`.
- **Endpoint confusion** — introspection uses `app.pipefy.com/graphql`; real operations use `api.pipefy.com/graphql`. The toolkit routes these automatically; raw-API users must distinguish (see `pipefy-api-fallback`).

## See also

- [docs/mcp/tools/introspection.md](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/introspection.md) — MCP parameters, query/mutation mismatch hints on `execute_graphql`.
- `pipefy-api-fallback` — Tier 3: direct HTTP fallback when the toolkit is unavailable.
- `pipefy-pipes-and-cards` — most common dedicated tools (prefer over `execute_graphql`).
