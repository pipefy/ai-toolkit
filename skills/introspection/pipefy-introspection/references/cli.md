# CLI reference — pipefy-introspection

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

| Operation | CLI |
|---|---|
| `introspect_type` | `pipefy introspect type` |
| `introspect_query` | `pipefy introspect query` |
| `introspect_mutation` | `pipefy introspect mutation` |
| `search_schema` | `pipefy introspect schema search` |
| `execute_graphql` | `pipefy graphql exec` |
| `get_organization` | `pipefy org get` |
| `list_organizations` | `pipefy org list` |

`--max-depth` controls recursion depth (default `1`).

Example (CLI):

```bash
pipefy introspect mutation createCard --max-depth 2 --json
```

```bash
pipefy introspect schema search automation --kind INPUT_OBJECT --json
```

## Execute a mutation

   ```bash
   pipefy graphql exec --query "mutation …" --vars '{"input":{…}}' --yes --json
   ```

   > **Mutations:** the CLI exits with code 2 unless `--yes` is passed (guardrail for agents and scripts). It also exits 2, with or without `--yes`, when the document is too deeply nested to parse: nothing is sent, because a document that cannot be classified could carry an unconfirmed mutation. `execute_graphql` refuses the same document with an error payload.
