---
name: pipefy-ipaas-flow-repair
description: >
  Use when the user wants to diagnose and edit an existing iPaaS
  (Advanced Automations) flow from a failed or timed-out run: read the
  failing step, patch it, validate, and optionally test. Do not publish or
  retry unless the user asks. To build a new flow from scratch, use
  pipefy-ipaas. For an org-wide run briefing, use pipefy-ipaas-usage-health.
  Same-card math or field stamps belong in native automations, not iPaaS.
tags: [pipefy, ipaas, repair, flow-runs, advanced-automations]
---

# iPaaS flow repair

Surgical edit of one Advanced Automations flow, starting from a **run id**
or a finding from [pipefy-ipaas-usage-health](../pipefy-ipaas-usage-health/SKILL.md).
**Read, patch, validate.** Publish, retry, and delete stay behind an explicit
ask. **4 MCP meta-tools** over the per-pipe catalog.

Prefer a native automation when the job is a calculation or field stamp on
the **same card** — those rules fire immediately. iPaaS can lag by minutes.
See [pipefy-automations](../../automations/pipefy-automations/SKILL.md)
(`field_map` + formulas).

---

## When to use

- "This Advanced Automation run failed — fix the step."
- "TIMEOUT / Failed: Retornar Resposta / Failed: Code — what do I change?"
- "Edit the existing flow; do not rebuild it."
- A usage-health briefing named a flow id and a failed step.

Do not use this skill for:

- Building a **new** flow from scratch → [pipefy-ipaas](../pipefy-ipaas/SKILL.md).
- Org-wide adoption / credit briefing → [pipefy-ipaas-usage-health](../pipefy-ipaas-usage-health/SKILL.md).
- Native if/then, `field_map`, or formulas → [pipefy-automations](../../automations/pipefy-automations/SKILL.md).

## Prerequisites

- `pipe_id` plus a **run id** and/or **flow id**. Discover via usage-health
  or the list-runs / list-flows catalog entries.
- Pipe Admin (create-automations ability) and iPaaS enabled on the org.
- Hosted or local MCP. iPaaS meta-tools have **no CLI twin** (deferred).

## Tools needed

| Tool (MCP) | CLI equivalent | Read-only |
|------------|----------------|-----------|
| `get_ipaas_tools` | — (deferred) | Yes |
| `call_ipaas_tool` | — (deferred) | No |
| `get_ipaas_connection_auth_url` | — (deferred) | No |
| `create_ipaas_connection` | — (deferred) | No |

## Catalog entries to look for

Discover first (`get_ipaas_tools`). Names below are **typical** on the hosted
Activepieces embed; if a name is missing, match the description.

| Job | Typical name |
|-----|----------------|
| List flows | `ap_list_flows` |
| List runs | `ap_list_runs` |
| Run detail (`flowRunId`) | `ap_get_run` |
| Step tree / validity | `ap_flow_structure` |
| Full step settings | `ap_read_step_settings` |
| CODE source | `ap_read_step_code` |
| Validate step before write | `ap_validate_step_config` |
| Patch one step | `ap_update_step` |
| Patch trigger | `ap_update_trigger` |
| Validate the flow | `ap_validate_flow` |
| Test one step / whole flow | `ap_test_step` / `ap_test_flow` |
| Retry a run | `ap_retry_run` |
| Enable / disable published | `ap_change_flow_status` |
| Publish draft | `ap_lock_and_publish` |
| List / create connections | `ap_list_connections` + MCP connection tools |

Never rebuild with `ap_build_flow` when the user asked to **edit**.

## Hosted catalog facts

Same live facts as usage-health; trust the schema if it disagrees.

- Run listing has **no date filter** (`limit` max 50, default PRODUCTION).
- `status=FAILED` excludes `TIMEOUT` and other enums.
- Step payloads purge after **~30 days**. Detail still returns `Flow: <id>`
  and the failed-step label. Do not `ap_test_flow` just to refresh history.
- `DISABLED` + old PRODUCTION runs ≠ "the flow is live."
- `ENABLED` + 0 PRODUCTION runs may be a **subflow** (`piece-subflows`).
- Argument names are not uniform (`flowRunId` ≠ `run_id`). Expand first.

## Steps — repair from a run

1. **Resolve ids.** If the user gave only a run id, list runs on the pipe
   (or use the usage-health finding), then expand run-detail.

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id>
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<run-detail-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<run-detail-entry> arguments={flowRunId=<id>}
   ```

   Capture: flow id, status, duration, failed-step name, purge warning,
   environment (PRODUCTION vs TESTING).

2. **Map the flow.** Expand list-flows if you need the human name, ENABLED
   vs DISABLED, published vs draft, trigger type.

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<list-flows-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<list-flows-entry> arguments={limit=100}
   ```

3. **Read structure, then the failing step only.**

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<structure-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<structure-entry> arguments={...}
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<read-settings-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<read-settings-entry> arguments={...}
   ```

   For a CODE step, use the read-code entry (structure truncates source).
   Count steps **in the flow** from structure; do not confuse with steps
   **executed** on the run.

4. **Classify the failure before writing.**

   | Signal | First fix to try |
   |--------|------------------|
   | Auth / 401 on an external piece | List connections; create or rotate; pass `externalId` as `auth` |
   | Failed: Retornar Resposta / empty output | Read the step that feeds the return; fix mapping, not the wrapper |
   | Failed: Loop on Items | Items expression empty or not a list — fix the loop input |
   | Failed: Code | Read full source; prefer a piece + inline formula over more CODE |
   | TIMEOUT | Long external call or delay step; tighten, split, or disable schedule |
   | Purged + DISABLED | Report only; do not retry; ask whether to edit the draft at all |
   | Same-card math / stamp | Stop. Offer a native automation + formula instead of iPaaS |

5. **Propose the patch. Wait for approval.** Show flow id, step name, current
   ENABLED/DISABLED, and the exact field you will change. Then expand
   validate-step-config (if present) and update-step.

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<validate-step-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<validate-step-entry> arguments={...}
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<update-step-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<update-step-entry> arguments={...}
   ```

   Prefer `ap_update_step` / `ap_update_trigger` over delete. Deleting a step
   drops sample data.

6. **Validate the flow** (no publish).

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<validate-flow-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<validate-flow-entry> arguments={...}
   ```

7. **Test only on explicit intent.** `ap_test_flow` / `ap_test_step` run in
   TESTING and **have real side effects** for Slack/Gmail/Sheets/HTTP.
   Keep test data disposable. ~120s budget.

8. **Retry / enable / publish only on explicit intent.**
   - Retry a purged run on a DISABLED flow: refuse and explain.
   - `ap_retry_run` may hit the live external app.
   - `ap_lock_and_publish` enables the flow. Confirm first.
   - Destructive catalog calls use MCP `confirm=true` + `confirmation_token`
     — see [pipefy-ipaas](../pipefy-ipaas/SKILL.md).

## Steps — repair from a flow id (no run)

If the user points at a draft that never ran: skip run-detail; start at
structure → invalid/unconfigured steps → same patch / validate path.

## Success criteria

- The failing step (or invalid structure node) was identified by **id + name**.
- The write was an **update**, not a rebuild, unless the user asked to rebuild.
- `ap_validate_flow` ran after the patch.
- No retry, test with external side effects, enable, or publish happened
  without a clear ask.
- If the job belonged on a native formula, the agent said so and did not
  add an iPaaS step.

## Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| Run detail purged | Host retains ~30 days | Keep flow id + failed-step label; edit structure, do not retry |
| `status=FAILED` list looks clean | TIMEOUTs excluded | Unfiltered list or `status=TIMEOUT` |
| Wrong argument name | Schemas are not uniform | Re-expand; hosted run-detail wants `flowRunId` |
| Auth error after patch | Missing / stale connection | `ap_list_connections` + `create_ipaas_connection` |
| Validate fails on trigger | Required trigger props unset | Read piece props; `ap_update_trigger` |
| Test-run fires Slack/email | TESTING still calls the app | Disposable data; or test a self-contained piece only |
| Subflow never runs | `piece-subflows` needs a caller | Find the parent flow; do not enable a schedule that is not there |
| Agent rebuilt the flow | `ap_build_flow` used for an edit | Stop; revert to granular update tools |
| User wanted instant card math | iPaaS delay vs native formula | Switch to [pipefy-automations](../../automations/pipefy-automations/SKILL.md) (`field_map`) |

## See also

- [skills/ipaas/pipefy-ipaas-usage-health/SKILL.md](../pipefy-ipaas-usage-health/SKILL.md) — find which run/flow to repair.
- [skills/ipaas/pipefy-ipaas/SKILL.md](../pipefy-ipaas/SKILL.md) — build new, connect apps, publish mechanics.
- [skills/automations/pipefy-automations/SKILL.md](../../automations/pipefy-automations/SKILL.md) — same-card `field_map` / formulas (immediate).
- [docs/mcp/tools/ipaas.md](../../../docs/mcp/tools/ipaas.md) — meta-tool semantics.
