# MCP reference

The skill runs the coverage check when the user names a pipe, the timed card read when they want lead time or time per phase, and a pipe report export for whole-pipe volume. Nothing else.

## Coverage check

```text
get_pipe pipe_id=<id>
```

```text
get_automations pipe_id=<id>
```

Pass `after=<pagination.end_cursor>` while `pagination.has_more` is true.

```text
get_ai_agents repo_uuid=<pipe.uuid>
```

For each active agent, read its behaviors:

```text
get_ai_agent uuid=<agent.uuid>
```

## Timed card read

```text
execute_graphql query=<the TimedCards document in the skill> variables={"pipeId": "<id>"}
```

## Pipe report export (whole-pipe volume)

```text
get_pipe_reports pipe_uuid=<pipe.uuid>
```

```text
get_pipe_report_columns pipe_uuid=<pipe.uuid>
```

```text
export_pipe_report pipe_id=<id> pipe_report_id=<report.id> columns=["title", "current_phase", "created_at", "finished_at", "duration_in_phase_<n>"]
```

```text
get_pipe_report_export export_id=<export.id>
```

When the state is `done`, the response has `fileURL`.
