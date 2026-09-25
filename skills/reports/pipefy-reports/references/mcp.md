# MCP reference

Use the operation names in the workflow as MCP tool names.

## Invocation examples

```text
get_pipe_reports pipe_id=67890
```

```text
export_pipe_report report_id=123
```

```text
get_pipe_report_export export_id=<EXPORT_ID>
```

```text
get_pipe_report_filterable_fields pipe_id=67890
```

```
create_pipe_report pipe_id=67890 name="Phase subset" filter='{"operator":"and","queries":[{"field":"current_phase","operator":"eq","type":"select","value":"<phase_id>"}]}'
```

For destructive deletes, echo `confirmation_token` from the preview with `confirm=true`.
Use `debug=true` on writes like other mutation tools.
