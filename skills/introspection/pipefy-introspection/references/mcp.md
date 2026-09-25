# MCP reference — pipefy-introspection

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

## The `include_parsed` flag

`execute_graphql`, `introspect_type`, `introspect_mutation`, `introspect_query`, and `get_organization` all accept an optional `include_parsed: bool` (default `false`).

- **Default (`false`):** response is `{ success, result }` where `result` is the raw GraphQL JSON as a **string**.
- **`true`:** response includes **both** `result` (the raw JSON string) AND `data` (the parsed dict). Drill into `data` programmatically; keep `result` to forward verbatim.

Use `include_parsed=true` whenever you plan to read nested fields (e.g. iterating over `phases[].fields[]`). Leave it off for one-shot reads where the raw string is sufficient.

Example: `introspect_mutation mutation_name="createCard" max_depth=2 include_parsed=true`.

## Mutation preview

Mutations use two steps. The first call returns a preview with `confirmation_token` and does not mutate. The preview names the mutation; it does not claim the write is irreversible, because this server cannot tell create from delete. Resend the call unchanged with `confirm=true` and the token; if the document changed, the response is a fresh preview whose token is bound to the new document.

   ```
   execute_graphql query="mutation CreateLabel($input: CreateLabelInput!) { createLabel(input: $input) { label { id name } } }" variables='{"input": {"pipe_id": 67890, "name": "Urgent", "color": "#FF0000"}}'
   ```

   Then after the preview:

   ```
   execute_graphql query="mutation CreateLabel($input: CreateLabelInput!) { createLabel(input: $input) { label { id name } } }" variables='{"input": {"pipe_id": 67890, "name": "Urgent", "color": "#FF0000"}}' confirm=true confirmation_token="<token from preview>"
   ```

`create_phase_field` does not accept options. Create first, then update. MCP mutations are two-step: preview, then `confirm=true` plus `confirmation_token`. Resend the call unchanged with `confirm=true` and the token; if the document changed, the response is a fresh preview whose token is bound to the new document.

Then after the preview:

```
execute_graphql query='mutation($id: ID!, $options: [String!]) { updatePhaseField(input: { id: $id, options: $options }) { phase_field { id label options } } }' variables='{"id":"<field-id>","options":["High","Medium","Low"]}' confirm=true confirmation_token="<token from preview>"
```

## Optional schema cache

For long-running agent sessions, the MCP can reuse the fetched GraphQL schema across requests instead of re-introspecting on every call. Enable via the `gql_reuse_fetched_graphql_schema` setting (env or settings file). Off by default. After a breaking Pipefy schema change, the process must be restarted to pick up the new schema. Single-session agents rarely benefit — leave it off unless you measure real improvement.

---

- **`execute_graphql` returns GraphQL errors** — check `path` and `message`; pass `debug=true` on the next call to surface the `correlation_id`.

Queries through `execute_graphql` are ungated. Mutations require the unchanged document and variables plus `confirm=true` and the preview token. Documents too deeply nested to classify are rejected without sending them.
