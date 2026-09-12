---
name: pipefy-ipaas-usage-health
description: >
  Use when the user wants an organization-wide health briefing of iPaaS
  (Advanced Automations) flow runs: adoption, failures, noisy flows, step
  volume, and how that compares with native automations and AI credit burn.
  Diagnose and report only. To build or publish a flow, use pipefy-ipaas.
  For native-automation logs and CSV job export only, use pipefy-observability.
tags: [pipefy, ipaas, observability, usage, flow-runs, health]
---

# iPaaS usage health

Produce an actionable **org briefing** on Advanced Automations: which pipes
have an iPaaS workspace, which flows fail, which runs are noisy, and whether
AI credits or native automations are the real cost driver. **10 MCP tools.**
Read-only by default. Retry a failed run only on explicit user intent.

This skill does **not** mint, cascade, or paste tokens. The MCP server already
authenticates the caller and mints the pipe-scoped iPaaS session per request.

---

## When to use

- "How healthy are our Advanced Automations / iPaaS flows?"
- "Which integration flows are failing this week?"
- "Show iPaaS adoption across the org" / "usage briefing for CS or admin."
- "Are we burning AI credits or automation runs — and where?"
- "Top failing flows, noisy pipes, what to retry."

Do not use this skill for:

- Building, editing, testing, or publishing a flow → [pipefy-ipaas](../pipefy-ipaas/SKILL.md).
- Native if/then rules or AI automations as the primary subject → [pipefy-automations](../../automations/pipefy-automations/SKILL.md).
- AI agent traces or automation-jobs CSV export only → [pipefy-observability](../../observability/pipefy-observability/SKILL.md).
- Redesigning a pipe's phases → [pipefy-process-intelligence](../../process-intelligence/pipefy-process-intelligence/SKILL.md).

## Prerequisites

- Caller is a member of the pipes to inspect (listings are **membership-scoped**).
- Pipe Admin or Org Admin when the catalog requires create-automations ability.
- iPaaS enabled on the organization. If not, `get_ipaas_tools` typically returns
  `PERMISSION_DENIED` (wording is backend-dependent).
- Hosted or local MCP is enough. iPaaS meta-tools have **no CLI twin**
  (deferred in [`docs/parity.md`](../../../docs/parity.md)). Observability
  twins are shipped.

## Tools needed

| Tool (MCP) | CLI equivalent | Read-only |
|------------|----------------|-----------|
| `list_organizations` | `pipefy org list` | Yes |
| `get_organization` | `pipefy org get` | Yes |
| `search_pipes` | `pipefy pipe list` | Yes |
| `get_pipe` | `pipefy pipe get` | Yes |
| `get_ipaas_tools` | — (deferred) | Yes |
| `call_ipaas_tool` | — (deferred) | No |
| `get_ai_credit_usage` | `pipefy usage credits` | Yes |
| `get_automations_usage` | `pipefy usage automations` | Yes |
| `get_automation_execution_metrics` | `pipefy usage execution-metrics` | Yes |
| `get_agents_usage` | `pipefy usage agents` | Yes |

Optional follow-up, only if the briefing must separate native rules from iPaaS:

| Tool (MCP) | CLI equivalent | Read-only |
|------------|----------------|-----------|
| `get_automations` | `pipefy automation list` | Yes |

## Identifiers (do not mix)

| Concept | What tools expect | How to obtain |
|---------|-------------------|---------------|
| Organization (usage / credits) | UUID **or** numeric id | `list_organizations` / `get_organization` |
| Organization (execution metrics) | numeric `organization_id` | same `id` as the Pipefy URL |
| Pipe for iPaaS | `pipe_id` string | `search_pipes` or user-supplied id |
| iPaaS catalog entry | runtime `name` from `get_ipaas_tools` | discover per pipe; never invent names |
| Flow | catalog flow id (not a pipe id) | list-flows entry |
| Flow run | catalog run id | run-listing entry; detail uses `flowRunId` |
| Native automation | `automation_id` | `get_automations` — not a flow id |

`pipesCount` on the org is the **org-wide total**. `search_pipes` returns only
pipes the caller is a member of, and may set `pipes_truncated`. Do not treat a
short list as a failed call. See [`docs/mcp/tools/organization.md`](../../../docs/mcp/tools/organization.md).

`get_automations_usage` counts **native automation executions**, not AI credits
and not iPaaS flow runs. `get_agents_usage` aligns with AI credit burn for
agents — compare it with `get_ai_credit_usage`, not with automation run totals.

## The meta-tool pattern (iPaaS)

The flow-run verbs live in the **per-pipe catalog**, not as fixed MCP tools.

1. `get_ipaas_tools pipe_id=<pipe_id>` — compact catalog.
2. `get_ipaas_tools pipe_id=<pipe_id> tool_name=<entry>` — one `inputSchema`.
3. `call_ipaas_tool pipe_id=<pipe_id> tool_name=<entry> arguments={...}`

Never expand more than the entry you are about to call. Argument names are
**not** uniform — read the schema.

After discover, look for entries whose descriptions match these jobs. Names
below are **typical** on the hosted catalog (Activepieces embed); if a name is
missing, use the description, never invent one.

| Job | Typical catalog name |
|-----|----------------------|
| List flows (status, trigger, published/draft) | `ap_list_flows` |
| List runs | `ap_list_runs` |
| Run detail (steps, errors, flow id) | `ap_get_run` |
| Steps **in** the flow | `ap_flow_structure` |
| Retry (only on explicit user intent) | `ap_retry_run` |

## Hosted catalog facts (do not assume dates on runs)

Verified against the live hosted iPaaS catalog. Re-read the schema every time;
if it disagrees with this table, **trust the schema**.

| Fact | What to do |
|------|------------|
| Run-listing has **no date filter** | `limit` default 10, max 50. The page is the **latest N PRODUCTION runs**, not "last 7 days". Say that in the briefing. |
| `environment` defaults to `PRODUCTION` when `flowId` is omitted | Cross-environment scans are slow; keep PRODUCTION unless the user asks for TESTING. |
| `status=FAILED` is a **narrow** enum | It does **not** include `TIMEOUT`, `CANCELED`, `QUOTA_EXCEEDED`, `INTERNAL_ERROR`, `MEMORY_LIMIT_EXCEEDED`. For health, list unfiltered (classify locally) **or** call once per status you will report. |
| Run listing often **omits the flow name** | Call run-detail: it still returns `Flow: <id>` after step data is gone. Map id → name via the list-flows payload. |
| Step payloads purge after **~30 days** | Detail then says "Steps: not available — execution data is purged". Keep status, duration, failed-step label, and flow id from that same payload. |
| `DISABLED` + `published` can still have old PRODUCTION runs | Do not treat historical failures as "the flow is live now". Report current `ENABLED`/`DISABLED` next to the run. |
| `ENABLED` + 0 PRODUCTION runs is not always dead | Subflow triggers (`piece-subflows`) only run when another flow calls them. Label them **enabled, caller-driven**. |
| Credit `limit: 0` | `active: false` vs `active: true` still matters — AI features may be on with **no quota**. Flag remaining 0. |

## Steps — org briefing

Default window: last 7 days for **native** usage tools (`filter_date_from` /
`filter_date_to` ISO8601). Credits: `period=current_month` unless the user
names another period. Execution metrics: `period=TWENTY_FOUR_HOURS` unless
asked otherwise. iPaaS runs use the **host page**, not this window.

1. **Resolve the organization** — no id required on the first call.

   MCP:
   ```
   list_organizations
   ```

   CLI:
   ```bash
   pipefy org list
   ```

   Several orgs: name them. If the user already asked for "the briefing" and
   every org is small (≤5 visible pipes each), brief **all** and say so.
   Otherwise ask which org.

   MCP:
   ```
   get_organization organization_id=<id>
   ```

   CLI:
   ```bash
   pipefy org get <id>
   ```

   Capture `id`, `uuid`, `name`, `planName`, `membersCount`, `pipesCount`.

2. **Org cost layer (native automations + AI)** — these do **not** include
   iPaaS flow runs.

   MCP:
   ```
   get_ai_credit_usage organization_uuid=<id-or-uuid> period=current_month
   get_automations_usage organization_uuid=<id-or-uuid> filter_date_from=<from> filter_date_to=<to>
   get_agents_usage organization_uuid=<id-or-uuid> filter_date_from=<from> filter_date_to=<to>
   get_automation_execution_metrics organization_id=<numeric-id> period=TWENTY_FOUR_HOURS
   ```

   CLI:
   ```bash
   pipefy usage credits --organization <id-or-uuid> --period current_month
   pipefy usage automations --organization <id-or-uuid> --from <from> --to <to>
   pipefy usage agents --organization <id-or-uuid> --from <from> --to <to>
   pipefy usage execution-metrics --organization <numeric-id> --period TWENTY_FOUR_HOURS
   ```

   Page execution metrics (`after=page_info.endCursor`, `first` ≤ 50).
   `partial_errors` is partial success, not a hard failure.

   Flag: remaining AI credits at 0; `limit: 0`; native automations with high
   `failureRate`; agents that dominate credit burn.

3. **Inventory pipes the caller can see.** If the user already gave `pipe_id`s,
   skip the search and use that list.

   MCP:
   ```
   search_pipes
   ```

   CLI:
   ```bash
   pipefy pipe list
   ```

   Respect `search_limits.max_pipes_per_org` (max 500). Raise the cap only when
   the returned count **hit** the applied cap. Unfiltered, `pipes_truncated`
   plus a list well under 500 usually means **membership**, not the cap.

4. **Bound the iPaaS probe.** Full-org walks are slow (one catalog hop per
   pipe). Default:

   - User-supplied pipe ids → probe all of them.
   - Otherwise probe at most **20** pipes (say so in the briefing).
   - Ask before scanning more.

   For each probed pipe, confirm the id:

   MCP:
   ```
   get_pipe pipe_id=<pipe_id>
   ```

   CLI:
   ```bash
   pipefy pipe get <pipe_id>
   ```

5. **Discover the iPaaS workspace, then list flows and runs.**

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id>
   ```

   Classify the pipe:

   | Catalog result | Meaning |
   |----------------|---------|
   | Compact catalog with flow/run entries | iPaaS workspace present |
   | `PERMISSION_DENIED` / "iPaaS is disabled" | Org or pipe cannot use iPaaS — stop probing this org |
   | "disabled on this server" | Hosted/local MCP missing the iPaaS OAuth client — stop and report |
   | Workspace present, list-flows returns 0 | **Enabled, unused** |

   When the workspace is present, expand **one** list-flows entry, then invoke
   it. Repeat for the run-listing entry. Read schemas first.

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<list-flows-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<list-flows-entry> arguments={limit=100}
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<run-listing-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<run-listing-entry> arguments={limit=50 environment=PRODUCTION}
   ```

   Only pass a date bound if **that** schema has one (hosted `ap_list_runs`
   does not). From the flow list, tally `ENABLED` vs `DISABLED` and
   `published` vs `draft`. From the run page, classify each status locally.

   How many of those runs fall inside the native 7-day window? Count from
   timestamps on the page. If **none** do, say "0 runs in the usage window;
   host page covers [oldest] → [newest]."

6. **Inspect failures — do not retry yet.** For each failed / timed-out /
   cancelled run you will mention, expand the run-detail entry.

   MCP:
   ```
   get_ipaas_tools pipe_id=<pipe_id> tool_name=<run-detail-entry>
   call_ipaas_tool pipe_id=<pipe_id> tool_name=<run-detail-entry> arguments={flowRunId=<id>}
   ```

   Use the run id the listing actually returned. After purge, keep the flow
   id + failed-step label and map the flow id through the list-flows payload.
   Do not call `ap_test_flow` to "refresh" data — that has side effects.

   Count steps from the flow-structure entry (steps **in the flow**) and from
   run detail when steps are still present (steps **executed**). Never treat
   those as the same metric.

7. **Retry only on explicit user intent.** Show run id, **flow name**, current
   ENABLED/DISABLED, last error, and whether step data is purged. After
   approval, expand the retry entry. If the MCP returns a destructive
   preview, follow `confirm=true` + `confirmation_token` — see
   [pipefy-ipaas](../pipefy-ipaas/SKILL.md). Prefer not to retry a purged run
   on a DISABLED flow: there is nothing left to diagnose.

## Briefing format

```
## iPaaS usage health — [Org name] ([id])

Usage window: [from] → [to]  |  Credits: [period]  |  Plan: [planName]
Pipes in org: [pipesCount]  |  Visible: [n]  |  iPaaS probed: [n]
iPaaS run page: latest [N] PRODUCTION runs ([oldest] → [newest]) — not a date filter

### Adoption
- iPaaS workspace present: [n] / [probed]
- Flows: [total]  |  ENABLED: [n]  |  DISABLED: [n]  |  published / draft
- Flows with ≥1 run in the usage window: [n]
- Enabled, unused (workspace, zero flows): [pipe names]
- Enabled, caller-driven (subflow, 0 PRODUCTION runs): [flow names]

### iPaaS run health
- Host page: [total]  |  SUCCEEDED / FAILED / TIMEOUT / CANCELED / other
- In usage window: [n] (may be 0 even when the host page is full)
- Top failing flows: [name] ([id]) — [count] — [last error] — [ENABLED/DISABLED]
- Noisiest pipes (host-page volume): [pipe] — [runs]

### Native automations & AI (not iPaaS runs)
- AI credits: consumed [x] / limit [y]  |  remaining [z]  |  dashboard active [true/false]
- Native automation executions (usage window): [count]  |  worst failureRate: [name]
- AI agent credit burn: [top agents]

### Recommended next actions
1. [Do not retry purged run … / add caller to hidden pipe … / enable or delete drafts …]
2. …

### Limits of this briefing
- Membership-scoped listing; pipesCount is not the probe size.
- iPaaS scanned [n] pipes; say so if capped.
- Run listing has no date filter; statuses other than FAILED need their own read.
- Step data older than ~30 days is purged.
- Native usage tools do not count iPaaS flow runs.
```

## Success criteria

- Briefing names the org, the **usage** window, and the **host run-page** range.
- Adoption uses **probed** pipes as the denominator, not `pipesCount`.
- At least one iPaaS catalog hop ran, **or** the skill stopped with a clear
  org-level / server-level disable reason.
- FAILED vs TIMEOUT (and other statuses) are not collapsed into one bucket
  from a single `status=FAILED` call.
- Native usage and iPaaS runs are labeled as different units.
- No retry or destructive catalog call happened without explicit approval.

## Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| `list_organizations` empty | Caller belongs to no org | Ask the user to sign in with a member account |
| `search_pipes` << `pipesCount` | Membership scope and/or cap | Do not retry blindly; add the caller to more pipes or raise cap only if the list hit the cap |
| `PERMISSION_DENIED` / iPaaS disabled on first `get_ipaas_tools` | Org feature off or no pipe-admin | Stop the iPaaS section; still deliver the native usage layer |
| "disabled on this server" | MCP missing iPaaS OAuth client | Hosted MCP should have the default client; if local, restore `PIPEFY_IPAAS_OAUTH_CLIENT_ID` |
| Catalog has no run-listing entry | Older workspace / unexpected catalog | Report flows only; do not invent a tool name |
| Wrong argument name on `call_ipaas_tool` | Schemas are not uniform (`flowRunId` ≠ `run_id`) | Re-expand that entry and rebuild arguments from `inputSchema` |
| Run listing has no dates | Hosted `ap_list_runs` has no date properties | Use `limit=50` + timestamps on the page; do not claim a 7-day iPaaS window |
| `status=FAILED` looks "healthy" | TIMEOUTs (and others) are excluded | Unfiltered list, or a second call with `status=TIMEOUT` |
| "Steps: not available — purged after 30 days" | Host retention | Keep flow id + failed-step label; do not test-run to refresh |
| Run listing has no flow name | Compact list payload | `ap_get_run` still returns `Flow: <id>` after purge |
| ENABLED + 0 PRODUCTION runs | Subflow / never triggered | Check trigger type (`piece-subflows` vs schedule/webhook) before calling it dead |
| DISABLED + old PRODUCTION failures | Flow was turned off | Report current status; do not recommend retry |
| Execution metrics `partial_errors` | Missing permission on some automation ids | Include permitted rows; list denied ids |
| Credit remaining 0 / `limit: 0` | Quota exhausted or Free without pack | Warn that AI features stop until credits are replenished |
| User asks to retry | Side effects on external apps | Confirm run id + flow name + ENABLED + purge state; then retry catalog entry |

## See also

- [skills/ipaas/pipefy-ipaas/SKILL.md](../pipefy-ipaas/SKILL.md) — build, test, publish, retry mechanics.
- [skills/observability/pipefy-observability/SKILL.md](../../observability/pipefy-observability/SKILL.md) — native logs, credits, job CSV.
- [skills/automations/pipefy-automations/SKILL.md](../../automations/pipefy-automations/SKILL.md) — native if/then and AI automations.
- [docs/mcp/tools/ipaas.md](../../../docs/mcp/tools/ipaas.md) — meta-tool semantics.
- [docs/mcp/tools/observability.md](../../../docs/mcp/tools/observability.md) — usage units and identifiers.
- [docs/mcp/tools/organization.md](../../../docs/mcp/tools/organization.md) — `pipesCount` vs membership listings.
