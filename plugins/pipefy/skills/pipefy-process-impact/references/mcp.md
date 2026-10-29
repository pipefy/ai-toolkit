# MCP reference

The skill runs the coverage check when the user names a pipe, the timed card read when they want lead time or time per phase, and a pipe report export for whole-pipe volume. Nothing else.

## Coverage check

```text
get_pipe pipe_id=<id>
```

Keep both `pipe.id` and `pipe.uuid` from the response.

```text
get_automations pipe_id=<id>
```

The listing is complete only when `pagination.has_more` is false; pass `after=<pagination.end_cursor>` for the next page.

```text
get_ai_agents repo_uuid=<pipe.uuid>
```

For each active agent, read its behaviors:

```text
get_ai_agent uuid=<agent.uuid>
```

## Timed card read

```text
execute_graphql query=<document below> variables={"pipeId": "<id>"}
```

```graphql
query TimedCards($pipeId: ID!, $first: Int = 25, $after: String) {
  cards(pipe_id: $pipeId, first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id done createdAt finished_at started_current_phase_at current_phase_age updated_at
      current_phase { name }
      phases_history { phase { name } firstTimeIn lastTimeOut duration }
    } }
  }
}
```

`duration` is seconds; `lastTimeOut` is null on the phase the card is in. Pass `"after": <pageInfo.endCursor>` in `variables` for the next page. A page of 25 cards with `phases_history` is about 40 thousand characters; raise `first` (the API caps it at 50) only when the client can hold it.

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

Poll until the state is `done`; the response then has `fileURL` (an XLSX file). The report reads take the pipe `uuid`; the export takes the numeric pipe id.
