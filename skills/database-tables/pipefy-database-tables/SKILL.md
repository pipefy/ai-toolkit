---
name: pipefy-database-tables
description: >
  Use this skill when the user wants to work with Pipefy Database Tables —
  creating/reading/updating/deleting tables, records (rows), or table fields
  (schema columns).
tags: [pipefy, database, tables, records, fields]
---

# Database Tables

MCP clients: read [references/mcp.md](references/mcp.md). CLI users: read [references/cli.md](references/cli.md). Examples below describe shared operation arguments.

Tables, records (rows), schema columns (table fields), and attachments for Pipefy Database Tables.

---

## Cross-cutting patterns

- Use `introspect_type` on inputs such as `CreateTableFieldInput` / `UpdateTableFieldInput`.
- **Pagination:** `get_table_records` and `find_records` support `first` / `after`; default page size is 50.
- **`find_records` over paginated `get_table_records`** when you know the field value. One call with `field_id` and `field_value` beats N pages of `get_table_records`.

---

## Table operations

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_tables` | Yes | Load database tables by their IDs. |
| `search_tables` | Yes | Search tables by name. |
| `get_table` | Yes | Table metadata and field schema. |
| `create_table` | No | Create a new database table. |
| `update_table` | No | Rename or change settings. |
| `delete_table` | No | **Destructive; review and approve first.** |

---

## Table field (schema column) operations

| Operation | Purpose |
| ------------ | --------- |
| `create_table_field` | Add a column to a table schema. |
| `update_table_field` | Rename or change column description, required status, or options. |
| `delete_table_field` | **Destructive; review and approve first.** Requires `table_id`. |

---

## Record operations

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_table_records` | Yes | Paginated list of all records in a table. |
| `find_records` | Yes | Filter records by `field_id` and `field_value` — preferred over paginating `get_table_records`. |
| `get_table_record` | Yes | Single record with all populated field values. |
| `create_table_record` | No | Add a row to a table. |
| `update_table_record` | No | Update a row's `title`, `due_date` or `status_id`. It accepts no other keys. |
| `set_table_record_field_value` | No | Set one field value on a row. Use it for every table field. |
| `delete_table_record` | No | **Destructive; review and approve first.** |

---

## Steps — find and update a record

1. **Get table ID** (if not known):

   Operation: `search_tables(table_name="Customers")` and select the table ID from the results.

2. **Find the record** (use `find_records`, not pagination):

   Operation: `find_records(table_id=456, field_id="email", field_value="user@example.com")`

3. **Update one field** (targeted):

   Operation: `set_table_record_field_value(record_id=789, field_id="status", value="Active")`

   **Update record metadata** (such as title, due date, or status):

   Operation: `update_table_record(record_id=789, fields={"title":"Updated title"})`

---

## Review destructive changes

Before deletion, show the affected data and obtain explicit approval. Preview content per operation:

- **`delete_table`** — show table **name** and **field count**. `get_table` does not return a record count; obtain one through schema-checked GraphQL or by paging through all records if practical. State clearly when the count is unknown. Deleting a table destroys all rows and schema.
- **`delete_table_record`** — show record **title** and **key field values** so the user can identify which row will vanish.
- **`delete_table_field`** — show field **name** and **type**; warn explicitly that **all column data will be permanently lost**.

Never delete without first reviewing the affected data.

---

## Success criteria

- `get_table_records` returns the created/updated records with correct field values.
- Schema changes reflect immediately in `get_table`.

## Failure modes

- **`get_table_record` / `get_table_records` omit empty fields.** Records only return populated fields, so you cannot tell "field unset" from "field doesn't exist" without calling `get_table` for the full schema.
- **`create_table_record` title silently overridden.** When the first table field is a start-form-style label column, Pipefy uses that field's value as the record `title`, ignoring the `title` parameter. Don't rely on `title` if the first field auto-populates a label-like column.
- **`create_table_field` rejects type:** call `introspect_type(type_name="CreateTableFieldInput")` for valid field types.
- **`find_records` returns empty:** check that `field_id` matches a field's **ID** (not label) from `get_table`.
- **Pagination cursor expired:** re-fetch from the beginning; cursors are short-lived.

## See also

- `pipefy-relations` — connect tables to pipes (and the table-relation ID namespace gotcha).
- `pipefy-introspection` — discover field input schemas.
