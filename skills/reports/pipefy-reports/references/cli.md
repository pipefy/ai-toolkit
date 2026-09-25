# CLI reference

| Command | Read-only | Purpose |
| ----- | ----------- | --------- |
| `pipefy report-pipe list` | Yes | List all reports for a pipe. |
| `pipefy report-pipe get` | Yes | Single report data. |
| `pipefy report-pipe columns` | Yes | Discover available columns for a report filter. |
| `pipefy report-pipe filterable-fields` | Yes | Discover filterable fields for a report. |
| `pipefy report-pipe create` | No | Create a new pipe report. |
| `pipefy report-pipe update` | No | Update report name or filters. |
| `pipefy report-pipe delete` | No | Destructive deletion; pass `--yes`. |
| `pipefy report-pipe export` | No | Trigger async export. |

| Command | Read-only | Purpose |
| ----- | ----------- | --------- |
| `pipefy report-org list` | Yes | List all org-level reports. |
| `pipefy report-org get` | Yes | Single org report data. |
| `pipefy report-org create` | No | Create an org-wide report. |
| `pipefy report-org update` | No | Update report config. |
| `pipefy report-org delete` | No | Destructive deletion; pass `--yes`. |
| `pipefy report-org export` | No | Trigger async export. |

| Command | Purpose |
| ----- | --------- |
| poll via `pipefy report-pipe export --format json` | Poll pipe report export status (after `export_pipe_report`). |
| poll via `pipefy report-org export --format json` | Poll org report export status (after `export_organization_report`). |
| `pipefy audit export` | Export pipe audit logs (separate from card report exports). |
