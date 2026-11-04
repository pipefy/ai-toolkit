# Knowledge bases

Pipe-scoped AI knowledge bases: list every item on a pipe, full CRUD for plain-text, document (PDF), and data lookup sources, and a read-access probe. **14 tools.**

Knowledge bases are the data sources an AI agent draws on. Each item's `id` is what you attach to an agent (see [Automations & AI](automations-and-ai.md)). Put the knowledge base `id` in both the agent-level `data_source_ids` and the behavior's `dataSourceIds`. With the id on the behavior only, the agent fails to save. With the id on the agent only, the behavior does not use it. Use `get_ai_knowledge_bases` to discover the IDs, then `validate_ai_agent_behaviors(data_source_ids=[...])` to check membership before writing the agent.

---

| Tool | Read-only | Role |
|------|-----------|------|
| `get_ai_knowledge_bases` | Yes | Lists every knowledge base item on a pipe (plain texts, documents, data lookups) as one flat list — no pagination. Each item carries `id`, `type` (`knowledge_base_plain_texts`, `knowledge_base_documents`, or `data_lookups` — the data lookup discriminator is not prefixed), `name`, `description`, `updatedAt`. |
| `get_ai_knowledge_base_plain_text` | Yes | Fetches one plain text by `id`, including its full `content`. |
| `create_ai_knowledge_base_plain_text` | No | Creates a plain text. `name` (1-80 chars), `content` (1-3500 chars), and `description` (1-300 chars) are all required. |
| `update_ai_knowledge_base_plain_text` | No | Partial update by `plain_text_id`: pass any of `name` / `content` / `description` (at least one); omitted fields keep their stored value. |
| `delete_ai_knowledge_base_plain_text` | No | Deletes a plain text permanently. [Two-step](cross-cutting.md#destructive-operations): echo `confirmation_token` from the preview. |
| `get_ai_knowledge_base_document` | Yes | Fetches one document by `id`. `content` is the stored document URL, not the extracted text. |
| `create_ai_knowledge_base_document` | No | Creates a document from a local PDF in one shot (presigned URL, S3 PUT, create mutation). `name` (1-80 chars), `file_path`, and `description` (1-300 chars) are required. |
| `update_ai_knowledge_base_document` | No | Metadata-only partial update by `document_id`: pass `name` and/or `description` (at least one). The PDF file cannot be replaced. |
| `delete_ai_knowledge_base_document` | No | Deletes a document permanently. [Two-step](cross-cutting.md#destructive-operations): echo `confirmation_token` from the preview. |
| `get_ai_knowledge_base_data_lookup` | Yes | Fetches one data lookup by `id`. The payload never includes `conditions` (see below). |
| `create_ai_knowledge_base_data_lookup` | No | Creates a data lookup: a data source that searches records in a source pipe or database table by conditions and returns selected fields. `name` (1-80 chars), `description` (1-300 chars), `source_repo_id`, `output_fields`, and `conditions` are required. |
| `update_ai_knowledge_base_data_lookup` | No | Replaces a data lookup's full definition: `source_repo_id`, `output_fields`, and `conditions` are required on every call. Only `name`/`description` are partial. |
| `delete_ai_knowledge_base_data_lookup` | No | Deletes a data lookup permanently. [Two-step](cross-cutting.md#destructive-operations): echo `confirmation_token` from the preview. |
| `validate_knowledge_base_access` | Yes | Probes whether the current credential can read a pipe's knowledge bases, classifying failures into structured problems instead of opaque errors. |

## Identifiers: pipe UUID, not numeric ID

> Full cross-tool map: [identifiers.md](identifiers.md#ai-agents-and-knowledge-bases).

Every knowledge base operation is scoped by the pipe **UUID** (`pipe_uuid`), not the numeric pipe ID — this follows the Pipefy GraphQL API. `get_pipe` returns the `uuid` field; `get_ai_knowledge_bases` returns each item's `id` (a data-source UUID) for the by-id operations and for `dataSourceIds`. The one deliberate exception is a data lookup's `source_repo_id`, which is the **numeric** ID of the source pipe or the numeric `internal_id` of the source table (see below).

## Plain-text limits (enforced client-side)

The `name` and `description` limits are the limits the Pipefy UI forms enforce. An item over them cannot be saved from the UI until the user shortens it. Limits fail fast before the network call, so an over-limit value is rejected with an actionable message rather than a backend 422:

- `content`: required, 1-3500 characters.
- `description`: required, 1-300 characters. The GraphQL schema marks `description` optional, but the backend rejects a blank one, so the toolkit requires it on create.
- `name`: required, 1-80 characters.

On update, only the fields you pass are validated and sent; the others keep their stored values.

## Documents (one-shot PDF upload)

`create_ai_knowledge_base_document` takes a local `file_path` and does the whole upload in one call: read the file, request a presigned URL for the pipe's organization (resolved from the pipe UUID), PUT the bytes to S3, then run the create mutation with the persistent download URL. The MCP server reads the file as the user, so `file_path` is a local path (`~` is expanded); the create tool is therefore not exposed in the remote profile.

Client-side checks fail fast, before the upload starts:

- `file_path`: must be a `.pdf` (case-insensitive extension), under 20 MiB.
- `name`: required, 1-80 characters.
- `description`: required, 1-300 characters. As with plain text, the GraphQL schema marks it optional but the backend rejects a blank one.

Failures are tagged with the step that failed — `file_read`, `presigned_url`, `s3_upload`, or `kb_create` — carried on `error.details.step` (an S3 failure also carries `body_snippet`).

**Indexing is asynchronous.** A created document is not necessarily searchable by agents the moment the tool returns; vectorization runs in the background.

**Update is metadata-only.** `update_ai_knowledge_base_document` changes `name` / `description`; it cannot replace the PDF. `content` returned by `get_ai_knowledge_base_document` is the stored document URL, not the extracted text.

## Data lookups (typed conditions, full-replacement updates)

A data lookup lets an agent search records in a **source pipe or database table** by conditions and return the values of selected fields. Its definition has three parts: `source_repo_id` (the source), `output_fields` (which field values matching records return), and `conditions` (how records are filtered).

The toolkit validates the definition client-side because the API accepts shapes that only fail later, when an agent actually runs the lookup:

- **`source_repo_id` must be a numeric id**: the pipe ID for a pipe, or the table's `internal_id` (from `get_table` or `search_tables`) for a database table. The toolkit rejects a UUID or the table's alphanumeric `id`. The API accepts a UUID at create time, but the lookup then breaks when an agent runs it, long after the write succeeded.
- **`output_fields`**: 1-30 field IDs — start-form/phase field slugs (e.g. `customer_email`) plus static fields such as `id`, `title`, `current_phase`, `assignees`, `created_by`, `created_at`. For a table, the slugs are the `table_fields[].id` values from `get_table`.
- **`conditions`**: at least one object, each with `field` (a field ID as above) and `operator` (see "Operators follow the field type" below). A condition is one of two shapes:
  - **Static** — `value` is required and must be a string (the backend silently drops non-scalar values and the runtime rejects non-strings): `{"field": "title", "operator": "ilike", "value": "urgent"}`.
  - **AI-filled** — `usingFillWithAi: true` with `inputName`, `inputType` (opaque, e.g. `"text"`, `"number"`), and `inputDescription`; `value` must be omitted (the AI asks the user for it at runtime): `{"field": "customer_email", "operator": "eq", "usingFillWithAi": true, "inputName": "Customer email", "inputType": "text", "inputDescription": "The customer's email address"}`.

  Condition keys accept camelCase (as above) or snake_case; unknown keys are rejected so a typo cannot silently drop a constraint.

**Every write uses the records search.** Create and update write the same shape the Pipefy UI writes, and this search is the only one that can read a database table. Each condition names its target as `fieldUuid` (a custom field) or `attribute` (a fixed field), next to `field`. The toolkit sets it from `field`:

- The fixed slugs `id`, `title`, `created_by`, `created_at`, `due_date`, `finished_at`, `current_phase`, `labels`, and `assignees` get the `attribute` `ID`, `TITLE`, `CREATOR`, `CREATED_AT`, `DUE_DATE`, `FINISHED_AT`, `CURRENT_PHASE`, `LABELS`, or `ASSIGNEES`.
- Any other slug gets its field uuid.
- The toolkit reads the source's fields once when a condition does not set `attribute`. A `source_repo_id` that names no pipe or table the credential can read fails there, before the write.
- A slug fails before the write when it is not a field of the source, or when it names two targets. Pipefy gives a custom field labeled "Labels" the slug `labels`, so that slug names both the fixed field and the custom field. For these, set `fieldUuid` (from `get_start_form_fields`, `get_phase_fields`, or `get_table`) or `attribute` on the condition.

You can also pass `fieldUuid` or `attribute` yourself, with the values above. A condition takes one of the two, not both. The toolkit sends an `attribute` as given. It looks up a `fieldUuid` in the source's fields, because the operator check needs the field type. A `fieldUuid` that is not a field of the source also fails before the write.

**Operators follow the field type.** `operator` is `eq` (exact value), `not_eq`, or `ilike` (case-insensitive substring) on an ordinary field, and `contains` on a list field (labels, assignees, checklists, connections). Any other operator, `contains` on an ordinary field, or another operator on a list field fails before the write. The error names every failing condition by its index.

A list field is a custom field of type `label_select`, `assignee_select`, `checklist_vertical`, `checklist_horizontal`, or `connector`, or the fixed field `labels` or `assignees`. In the records search, `contains` on a text field returns no records, so `ilike` is the substring match on an ordinary field. The Pipefy UI also writes `contains` only on list fields.

**A table has no phases.** A condition on `current_phase` saves on a table source, and the lookup then fails when the agent runs.

**Reads never return `conditions`.** The API stores them but does not expose them on `get_ai_knowledge_base_data_lookup` (or on the create/update responses), so keep your lookup definition — including conditions — as the client-side source of truth.

**Updates replace the whole definition.** The backend rewrites the stored definition with exactly what the update carries: `source_repo_id`, `output_fields`, and `conditions` are required on every `update_ai_knowledge_base_data_lookup` call (pass the complete condition set, not a delta). Only `name`/`description` behave partially (omitted keeps the stored value). An update also moves a lookup that used the older card search to the records search. Change `contains` on an ordinary field to `ilike` when you resend the definition.

## Probe semantics and the write gate

- A green `validate_knowledge_base_access` proves **read access only** (`read_ai_agents` on the pipe) — never the `manage_ai_agents` entitlement that every knowledge base create / update / delete (plain text, document, data lookup) requires.
- An **empty knowledge base list** is a valid green result (`knowledge_base_count: 0`), not a failure.
- The **CLI gates writes** on the probe: `pipefy kb plain-text create` / `update`, `pipefy kb document create` / `update`, and `pipefy kb data-lookup create` / `update` run the read-access probe first and fail with the classified problem if it is denied, before attempting the mutation.
- **Clean-gate contract.** The probe can return a success that still carries a `problem` — when the API returns partial data alongside GraphQL errors, it surfaces the classified error rather than discarding it, and deliberately does not flip `ok`. The CLI write gate therefore treats the gate as clean only when it is **`ok` and carries no `problem`**; a present `problem` is partial denial and is never read as full access.
- The **MCP tools stay explicit-validate-first**: create / update do not auto-probe. Call `validate_knowledge_base_access` yourself before writing.
- **Deletes require confirmation**: MCP two-step with `confirmation_token` ([Destructive operations](cross-cutting.md#destructive-operations)); the CLI needs `--yes` (or an interactive prompt).

## Attaching a source to an agent

`validate_ai_agent_behaviors` accepts an optional `data_source_ids` (agent-level). A behavior `dataSourceIds` entry that `data_source_ids` leaves out is a **problem**, because the agent fails to save. Without `data_source_ids`, each behavior id is a warning. Every id is also checked against the pipe's knowledge bases, and an id that is not on the pipe is a **warning only**. If the knowledge base list cannot be read, a single warning is added and the membership check is skipped. A read failure is never reported as a broken reference.

## Error classification

Failures on this surface are classified by the shared SDK-level module (`pipefy_sdk.graphql_problem`) into structured problems — `permission_denied`, `not_found`, `invalid_arguments`, `feature_not_enabled`, or `runtime` — carried on `error.details.kind` alongside the GraphQL `extensions.code` and `correlation_id`. The same classifier backs the CLI (`pipefy kb ...`), so both surfaces report the same problem kinds.
