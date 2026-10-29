# CLI reference

The skill runs the coverage check (`get_pipe`, `get_automations`, `get_ai_agents`, `get_ai_agent`) when the user names a pipe, the timed card read when they want lead time or time per phase, and a pipe report export for whole-pipe volume. Nothing else.

| Operation | Command |
|-----------|---------|
| `search_pipes` | `pipefy pipe list --name <text>` |
| `get_pipe` | `pipefy pipe get <PIPE_ID> --json` |
| `get_automations` | `pipefy automation list --pipe <PIPE_ID> --json` |
| `get_ai_agents` | `pipefy agent list --repo <PIPE_UUID> --json` |
| `get_ai_agent` | `pipefy agent get <AGENT_UUID> --json` |
| `execute_graphql` | `pipefy graphql exec -q '<document below>' --vars '{"pipeId": "<PIPE_ID>"}' --json` |
| `get_pipe_reports` | `pipefy report-pipe list --pipe <PIPE_UUID> --json` |
| `get_pipe_report_columns` | `pipefy report-pipe columns --pipe <PIPE_UUID> --json` |
| `export_pipe_report` | `pipefy report-pipe export --pipe <PIPE_ID> --report-id <REPORT_ID> --columns '<JSON array of column names>' --format csv > report.xlsx` |

`--repo` takes the pipe UUID that `pipefy pipe get` returns, not the numeric pipe id. The report `list` and `columns` commands also take the pipe UUID; `export` takes the numeric pipe id.

`pipefy automation list` without `--json` prints a table that leaves out `event_params` (the phase a rule acts on). The listing returns one page of up to 50 rules; while `pageInfo.hasNextPage` is true, run it again with `--after <pageInfo.endCursor>`.

`--format csv` waits for the export and writes the file's bytes to stdout. For a pipe report the file is XLSX, whatever the flag name, so redirect it to a `.xlsx` path.

The timed card read is a query, so `pipefy graphql exec` runs it without `--yes`:

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

`duration` is seconds; `lastTimeOut` is null on the phase the card is in. Pass `"after"` (and `"first"`, up to 50) in `--vars` for the next page.
