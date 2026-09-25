---
name: pipefy-observability
description: >
  Use this skill when the user wants to check AI agent logs, automation
  execution logs, org-level usage stats, AI credit consumption, or export
  automation job history. Covers 11 operations.
tags: [pipefy, observability, logs, usage, credits, exports]
---

# Observability

Read the [MCP reference](references/mcp.md) or [CLI reference](references/cli.md) for the surface you are using. Load only the relevant reference.

Monitor AI agent and automation execution, usage stats, credit consumption, and export job history. **11 operations.**

---

## Identifiers reference

Full identifier map: [observability identifiers](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/identifiers.md#observability).

| Concept | What tools expect | How to obtain |
|---------|-------------------|---------------|
| **Pipe for AI agent logs** | `repo_uuid` — the pipe **UUID** | `get_pipe` with numeric `pipe_id`; use `pipe.uuid`. |
| **Automation for logs** | `automation_id` — numeric | `get_automations pipe_id=...` |
| **Org for usage stats** | `organization_uuid` — UUID **or** numeric org id | `get_organization` returns the `uuid`; a numeric id also works (resolved server-side). Execution-metrics / export take numeric `organization_id`. |

---

## Tools

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_ai_agent_logs` | Yes | Execution history for a specific AI agent. |
| `get_ai_agent_log_details` | Yes | Single execution detail for an AI agent log entry. |
| `get_automation_logs` | Yes | Execution history for an automation (by automation ID). |
| `get_automation_logs_by_repo` | Yes | Automation logs filtered by pipe. |
| `get_agents_usage` | Yes | Org-level AI agent execution count and trends. |
| `get_automations_usage` | Yes | Org-level automation execution stats. |
| `get_automation_execution_metrics` | Yes | Per-automation execution metrics (totalRuns, success/failure rate, avg duration, lastRun) over a rolling window; partial success returns `partial_errors` for denied ids. |
| `get_ai_credit_usage` | Yes | AI credit consumption and remaining balance. |
| `export_automation_jobs` | Yes | Trigger async export of automation job history. |
| `get_automation_jobs_export` | Yes | Poll export job status (after `export_automation_jobs`). |
| `get_automation_jobs_export_csv` | Yes | Download finished automation-jobs export as CSV text. |

---

## Steps — diagnose a failing AI agent

1. **Get the pipe UUID** (not the numeric pipe ID):

   Operation: `get_pipe pipe_id=67890`

   Capture `pipe.uuid` from the response.

2. **Fetch recent agent logs:**

   Operation: `get_ai_agent_logs repo_uuid=<UUID> page=1`

3. **Identify the failed execution** — look for `status: failed` entries.

4. **Check credit usage** if the agent stopped unexpectedly:

   Operation: `get_ai_credit_usage organization_id=123`

5. **Fix and re-enable** — update the agent config (see `pipefy-ai-agents`) and toggle status:

   Operation: `toggle_ai_agent_status agent_id=456`

---

## Steps — export automation history as CSV

1. **Trigger the export:**

   Operation: `export_automation_jobs organization_id=123 period="current_month"`

2. **Poll for completion:**

   Operation: `get_automation_jobs_export export_id=<EXPORT_ID>`

   Repeat until `status` is `finished` or `failed`.

3. **Fetch CSV text** (when finished):

   Operation: `get_automation_jobs_export_csv export_id=<EXPORT_ID>`

---

## Success criteria

- Agent logs show execution timestamps and statuses.
- Credit usage shows remaining balance; no unexpected drops.
- CSV export downloads successfully and contains expected automation history.

## Failure modes

- **`get_ai_agent_logs` returns empty:** use the pipe **UUID** (e.g., `abc123-...`), not the numeric pipe ID. Get UUID from `get_pipe`.
- **`get_automation_jobs_export` stays in `processing`:** large exports take time. Wait at least 60 seconds between polls. If still `processing` after several minutes, retry the export trigger.
- **Credit usage shows 0 remaining:** alert the user — AI features will stop working until credits are replenished. Escalate to the Pipefy admin.

## See also

- `pipefy-ai-agents` — create and configure AI agents.
- `pipefy-automations` — create and debug automation rules.
