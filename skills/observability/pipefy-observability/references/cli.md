# CLI reference

| Command | Read-only | Purpose |
| ----- | ----------- | --------- |
| `pipefy agent logs list` | Yes | Execution history for a specific AI agent. |
| `pipefy agent logs get` | Yes | Single execution detail for an AI agent log entry. |
| `pipefy automation logs --automation` | Yes | Execution history for an automation (by automation ID). |
| `pipefy automation logs --repo` | Yes | Automation logs filtered by pipe. |
| `pipefy usage agents` | Yes | Org-level AI agent execution count and trends. |
| `pipefy usage automations` | Yes | Org-level automation execution stats. |
| `pipefy usage execution-metrics` | Yes | Per-automation execution metrics (totalRuns, success/failure rate, avg duration, lastRun) over a rolling window; partial success returns `partial_errors` for denied ids. |
| `pipefy usage credits` | Yes | AI credit consumption and remaining balance. |
| `pipefy export automation-jobs` | Yes | Trigger async export of automation job history. |
| `pipefy automation export status` | Yes | Poll export job status (after `export_automation_jobs`). |
| `pipefy export automation-jobs-csv` | Yes | Download finished automation-jobs export as CSV text. |
