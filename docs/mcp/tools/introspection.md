# Introspection & Raw GraphQL

Schema discovery tools plus a last-resort executor. Same OAuth client as everything else.

Prefer dedicated tools for standard operations. Use these when the schema shifts or no dedicated tool exists.

---

Responses: `success` / `result` or `error`; transport GraphQL errors are surfaced clearly.

## `max_depth` parameter

`introspect_type`, `introspect_query`, and `introspect_mutation` accept an optional `max_depth` (default `1`).

- **`max_depth=1`** (default) — returns the type/field info as-is. No sub-type resolution.
- **`max_depth=2`** — resolves one level of referenced types. Each non-scalar field/arg gets a `resolvedType` key with the full type definition inlined.

This eliminates the common multi-call pattern where the agent first introspects a mutation, then separately introspects each input type. With `max_depth=2`, a single call like `introspect_mutation("createCard", max_depth=2)` returns `CreateCardInput` with all its `inputFields` inlined.

Scalar types (`ID`, `String`, `Int`, `Float`, `Boolean`, `DateTime`) are never resolved.

## `kind` filter on `search_schema`

`search_schema` accepts an optional `kind` parameter to filter results by GraphQL type kind:

- `OBJECT` — output types (Card, Pipe, User, ...)
- `INPUT_OBJECT` — mutation inputs (CreateCardInput, ...)
- `ENUM` — enumeration types (CardStatus, ...)
- `SCALAR`, `INTERFACE`, `UNION` — other type kinds

Example: `search_schema("automation", kind="INPUT_OBJECT")` returns only automation-related input types.

## Query/mutation mismatch hint

When `execute_graphql` fails with a "field not found" error, the service checks if the field exists on the other root type (Query vs Mutation). If found, the error includes a `hint` key:

```json
{
  "message": "Cannot query field 'createCard' on type 'Query'.",
  "hint": "Hint: 'createCard' exists as a mutation, not a query. Use a mutation operation instead."
}
```

This catches the common mistake of using `query { createCard(...) }` instead of `mutation { createCard(...) }`.

## Notes

- `execute_graphql` checks the syntax of the document before it sends the request.

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/mcp/tools/introspection.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/mcp/tools/introspection.md).
