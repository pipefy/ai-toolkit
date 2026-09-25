---
name: pipefy-reports
description: >
  Use this skill when the user wants to create, read, update, delete, or
  export pipe reports or organization reports. Covers the async export
  workflow (trigger, poll, download). 17 operations.
tags: [pipefy, reports, exports, pipe-reports, organization-reports]
---

# Reports

Read the [MCP reference](references/mcp.md) or [CLI reference](references/cli.md) for the surface you are using. Load only the relevant reference.

Pipe reports and organization reports: discovery, CRUD, and async exports. **17 operations.**

---

## Cross-cutting patterns

- Build `ReportCardsFilter` using `get_pipe_report_columns` and `get_pipe_report_filterable_fields`; use `introspect_type` for uncommon inputs.
- `get_pipe_reports` omits `cardCount` in the query (Pipefy can error when resolving it).

---

## Pipe report tools

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_pipe_reports` | Yes | List all reports for a pipe. |
| `get_pipe_report` | Yes | Single report data. |
| `get_pipe_report_columns` | Yes | Discover available columns for a report filter. |
| `get_pipe_report_filterable_fields` | Yes | Discover filterable fields for a report. |
| `create_pipe_report` | No | Create a new pipe report. |
| `update_pipe_report` | No | Update report name or filters. |
| `delete_pipe_report` | No | Destructive deletion; use the selected surface’s confirmation flow. |
| `export_pipe_report` | No | Trigger async export. |

## Organization report tools

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_organization_reports` | Yes | List all org-level reports. |
| `get_organization_report` | Yes | Single org report data. |
| `create_organization_report` | No | Create an org-wide report. |
| `update_organization_report` | No | Update report config. |
| `delete_organization_report` | No | Destructive deletion; use the selected surface’s confirmation flow. |
| `export_organization_report` | No | Trigger async export. |

## Export status & download

| Operation | Purpose |
| ------------ | --------- |
| `get_pipe_report_export` | Poll pipe report export status (after `export_pipe_report`). |
| `get_organization_report_export` | Poll org report export status (after `export_organization_report`). |
| `export_pipe_audit_logs` | Export pipe audit logs (separate from card report exports). |

---

## Steps — export a pipe report

1. **List available reports:**

   Operation: `get_pipe_reports pipe_id=67890`

2. **Trigger the export:**

   Operation: `export_pipe_report report_id=123`

3. **Poll until finished:**

   Operation: `get_pipe_report_export export_id=<EXPORT_ID>`

   Repeat every 5–10 seconds until the response indicates `finished` (or `failed`).

4. **Download:** use the signed `fileUrl` from the finished export response over HTTPS (returned in the export payload).

---

## Steps — create a filtered pipe report

1. **Discover filterable fields:**

   Operation: `get_pipe_report_filterable_fields pipe_id=67890`

2. **Create the report with a `ReportCardsFilter` shape** (not a top-level `current_phase` array):

   Arguments:
   ```
   create_pipe_report pipe_id=67890 name="Phase subset" filter='{"operator":"and","queries":[{"field":"current_phase","operator":"eq","type":"select","value":"<phase_id>"}]}'
   ```

   Use the exact `field` string from step 1. Invalid shapes are rejected before GraphQL with a message pointing at `get_pipe_report_filterable_fields`.

---

## Success criteria

- `get_pipe_report_export` (or `get_organization_report_export`) reaches a terminal `finished` or `failed` state.
- Downloaded export contains the expected card/report data.

## Failure modes

- **Export stuck in `processing`:** large pipes with many cards can take minutes. Wait at least 60 seconds per poll. Retry the export trigger if still `processing` after several minutes.
- **`get_pipe_reports` returns `null` for `cardCount`:** known Pipefy API behavior; the tool omits that field automatically.
- **Filter rejected before GraphQL:** do not pass `{"current_phase":["id"]}`; use `operator` + `queries` (see step 2 above).
- **Filter not working after create:** use `get_pipe_report_filterable_fields` to confirm the exact `field` string and `value` format.

## See also

- `pipefy-observability` — export automation job history (different from pipe reports).
- `pipefy-introspection` — discover `ReportCardsFilter` input shape for complex filters.
