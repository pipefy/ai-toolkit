# Database Tables

Tables, records (rows), and schema columns (table fields) for org Database Tables.

## Cross-cutting patterns

- Same conventions as pipe building: `introspect_type` on inputs such as `CreateTableFieldInput` / `UpdateTableFieldInput`, `debug=true` on mutations, `extra_input` where the tool exposes it.
- **IDs:** `table_id`, record IDs, and related parameters are **strings** in GraphQL (numeric strings for many org tables, or opaque tokens such as `fIVcd19N`). Prefer quoted strings in MCP/JSON; unquoted numeric JSON may be coerced where the tool uses the shared ID type. See [Pipes & cards — Pipefy IDs](pipes-and-cards.md#pipefy-ids-type-safety).
- **Pagination:** `get_table_records` and `find_records` support `first` / `after`. With the unified MCP envelope, read top-level `pagination.has_more` and `pagination.end_cursor` (and `pagination.page_size`) and pass `after=end_cursor` for the next page (default page size for listing records is 50; caps apply — see tool docstrings).
