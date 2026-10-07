# Reports

Pipe reports and organization reports: discovery, CRUD, single pipe report fetch, and async exports.

## Cross-cutting patterns

- Build `ReportCardsFilter` using `get_pipe_report_columns` and `get_pipe_report_filterable_fields`; use `introspect_type` for uncommon inputs.
- **Filter shape:** nested `operator` (`and` | `or`) plus `queries` (and optional `groups`). Do **not** pass a top-level `current_phase` array — that is not valid GraphQL input. The SDK validates filter structure before calling the API; MCP and CLI surface the same error.

### Example phase filter (`create_pipe_report` / `update_pipe_report`)

Discover the exact `field` string for your pipe via `get_pipe_report_filterable_fields`, then:

```json
{
  "operator": "and",
  "queries": [
    {
      "field": "current_phase",
      "operator": "eq",
      "type": "select",
      "value": "<phase_id>"
    }
  ]
}
```

Replace `field` / `value` when filterable-field metadata uses different names or option ids.

- `get_pipe_reports` omits `cardCount` in the query (Pipefy can error when resolving it).
- `debug=true` on writes like other mutation tools.
- **Async export pattern:** trigger export -> poll the matching `get_*_report_export` until `state` is done -> use `fileURL`. `export_pipe_audit_logs` only returns `success` (no export ID to poll — the file is delivered to the requesting user).
