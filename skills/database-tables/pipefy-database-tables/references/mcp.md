# MCP controls and examples

- Same conventions as pipe building: `introspect_type` on inputs such as `CreateTableFieldInput` / `UpdateTableFieldInput`, `debug=true` on mutations.

- **Pagination:** `get_table_records` and `find_records` support `first` / `after`. With the unified MCP envelope, read top-level `pagination.has_more` and `pagination.end_cursor` (and `pagination.page_size`) and pass `after=end_cursor` for the next page (default page size is 50).

- **Legacy mutation envelope.** Several table mutation tools still return the GraphQL operation name as a nested key under `result` (for example `result.createTableRecord`). Read the payload inside that key; shape may differ from tools that already use the unified envelope.

Always call without `confirm=true` first, surface the preview (including `confirmation_token`) to the user, then call again with `confirm=true` and that token after explicit approval.

```text
get_tables organization_id=123
```

```text
find_records table_id=456 filter='{"column_id":"email","search_value":"user@example.com"}'
```

```text
set_table_record_field_value record_id=789 field_id="status" value="Active"
```

```text
update_table_record record_id=789 node_fields='[{"field_id":"status","field_value":"Active"}]'
```

Attachment uploads: exactly one source, `file_path` (local profile only) or `file_url` (downloaded, SSRF-guarded; any profile — required on the hosted server). See `pipefy-attachments`.

Never delete in a single call.

This workflow exposes 17 MCP tools.
