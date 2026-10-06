# Observability

Monitor AI agent and automation execution, usage stats, credit consumption, and export job history.

Read-only observability tools use `readOnlyHint=True`. The async export mutation (`export_automation_jobs`) does not.

---

## Identifiers (avoid mixing pipe vs automation vs org)

> Full cross-tool map: [identifiers.md](identifiers.md#observability).

| Concept | What observability tools expect | How to obtain it |
|--------|--------------------------------|------------------|
| **Pipe for AI agent logs** | `repo_uuid` — the pipe **UUID** | `get_pipe` with numeric `pipe_id`; use `pipe.uuid` as `repo_uuid`. |
| **Pipe for automation logs (all rules)** | `repo_id` — pipe id as **string** (numeric id is fine) | Same id you see in the Pipefy URL / `get_pipe` → `pipe.id`. |
| **Single automation logs** | `automation_id` — **not** the pipe id | `get_automations` with `pipe_id` lists rules and their `id` values. |
| **Organization for usage queries** | `organization_uuid` — **UUID or numeric org id** | `get_organization(organization_id)` returns the `uuid`; a numeric org id also works (resolved server-side). |
| **Organization for credit dashboard** | `organization_uuid` in the tool | **UUID** or **numeric org id** (string); numeric ids are resolved server-side before calling the API. |
| **Organization for execution metrics** | `organization_id` on `get_automation_execution_metrics` | Numeric org id (same as URLs / exports); optional `automation_ids` from `get_automations`. |
| **Organization for export** | `organization_id` on `export_automation_jobs` | Numeric org id (as used in URLs / exports); differs from the usage tools’ UUID parameter name. |

Empty lists (`totalCount: 0`) are valid: the pipe or automation may have no recent executions in what the API returns.

---

## Recommended workflows

**AI agent logs (you know the pipe id)**  
1. `get_pipe(pipe_id)` → read `uuid`.  
2. `get_ai_agent_logs(repo_uuid=that uuid, first=…)` → list entries.  
3. `get_ai_agent_log_details(log_uuid=…)` for trace / `tracingNodes` (use `uuid` from step 2).

**Automation logs (you know the pipe id, not which rule ran)**  
1. Prefer `get_automation_logs_by_repo(repo_id=str(pipe_id), …)` to see logs across every automation in the pipe.  
2. Each node includes `automationId` — use that value with `get_automation_logs(automation_id=…)` when you only care about one rule.  

`get_automation_logs` **cannot** be called with a pipe id alone. If you guess an `automation_id` from `get_automations`, that rule may have **zero** log rows while another rule on the same pipe has rows — use `get_automation_logs_by_repo` first when exploring.

**Org usage and credits**  
1. `get_agents_usage` and `get_automations_usage` take the org **UUID or numeric org id** and ISO8601 `filter_date_from` / `filter_date_to` values.  
2. `get_ai_credit_usage` also accepts org UUID **or** numeric org id; `period` is `current_month`, `last_month`, or `last_3_months`.  
3. **`get_automations_usage` `usage`** is an **execution count** (runs), not AI credits. **`get_agents_usage` `usage`** aligns with AI credit consumption for agents — compare with `get_ai_credit_usage` for the dashboard view, not with automation run totals.

**Per-automation execution metrics (rolling window)**  
1. Call `get_automation_execution_metrics(organization_id=…)` with the numeric org id. Omit `automation_ids` to fetch every automation in the org (optionally narrowed by `repo_id`, `action_ids`, `event_id`, `active`, `search`).  
2. `period` is one of `FIFTEEN_MINUTES`, `SIXTY_MINUTES` (default), `TWELVE_HOURS`, `TWENTY_FOUR_HOURS`.  
3. A page holds at most 50 automations; pass `page_info.endCursor` back as `after` for the next page.  
4. Partial success is normal: metrics for permitted automations plus `partial_errors` for denied ids — not a hard failure.

**Automation jobs export (async file)**  
1. `export_automation_jobs(organization_id, period)` → read `result.createAutomationJobsExport.automationJobsExport.id`.  
2. Poll `get_automation_jobs_export(export_id=that id)` until `status` is `finished` or `failed`. `ExportStatus`: `created`, `processing`, `finished`, `failed`.  
3. When `finished`, use **`get_automation_jobs_export_csv`** with the same `export_id` to download the `.xlsx` from Pipefy’s signed URL (https hosts ending in `.pipefy.com` only), convert the **first worksheet** to **CSV** text, and return it in the tool payload for LLM use. Cap output with `max_output_chars` (default 400_000) and download size with `max_download_bytes` (default 50 MiB).  
4. Alternatively, read `fileUrl` from `get_automation_jobs_export` and download outside the MCP if you need the raw xlsx.

---

## See also

- [Automations & AI](automations-and-ai.md) — `get_automations` / `get_pipe` when resolving ids before calling observability tools.
- [Organization](organization.md) — `get_organization` for org UUID, plan, and member count (replaces `execute_graphql` workarounds for org discovery).
- [Introspection](introspection.md) — `execute_graphql` for ad-hoc queries; `introspect_query` / `introspect_mutation` to discover query shapes before calling `execute_graphql`.
