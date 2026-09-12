---
name: pipefy-automations-formulas
description: >
  Use when the user wants a native Pipefy automation to compute or stamp a
  field with a formula or %{token}: SUM, IF, string functions, weekdays,
  assignee/creator names, email/comment tokens, plus/minus on dates. Immediate
  on the card — prefer this over iPaaS when no external app is required.
  To create the if/then rule itself, also follow pipefy-automations.
  To orchestrate Slack/Sheets/webhooks, use pipefy-ipaas.
tags: [pipefy, automations, formulas, field-map, tokens]
---

# Automation formulas

Playbook for **`field_map.value`** on traditional automations: functions,
operators, event tokens, and field references that go beyond the official
event-attribute catalog (today `get_automation_event_attributes` returns
**one** row). Apply them with `create_automation` / `update_automation`
as in [pipefy-automations](../pipefy-automations/SKILL.md).

Native rules run **on the card, immediately**. iPaaS Advanced Automations
can lag by minutes. If the job is math, text, or a weekday on the same
card, stay here.

---

## When to use

- "Set this field to SUM / IF / CONCAT of other fields."
- "Stamp created_at + 1 hour" / "next business day."
- "Put the assignee names or last comment into a field."
- "Should this be iPaaS or a native automation?"
- **Timesheet:** decimal duration (days) on the card → formatted `HH:MM` text, on `field_updated`. See [Worked example — timesheet HH:MM](#worked-example--timesheet-hhmm).
- **SLA digest:** nested IF + `WEEKDAY` + `INTERVAL_WEEKDAYS` + `"%{assignees}"` into one filterable text field. See [Worked example — SLA digest](#worked-example--sla-digest).

Do not use this skill for:

- Choosing trigger × action, conditions, or AI prompts → [pipefy-automations](../pipefy-automations/SKILL.md).
- External apps, multi-step integrations, incoming webhooks → [pipefy-ipaas](../../ipaas/pipefy-ipaas/SKILL.md).
- iPaaS run health / repair → [pipefy-ipaas-usage-health](../../ipaas/pipefy-ipaas-usage-health/SKILL.md) / [pipefy-ipaas-flow-repair](../../ipaas/pipefy-ipaas-flow-repair/SKILL.md).

## Prerequisites

- Destination `internal_id` from `get_start_form_fields` / `get_phase_fields`
  (never the slug in `field_map[].fieldId`).
- Pipe Admin (or permission to create automations).
- At most **20 fields** referenced per automation.

## Tools needed

| Tool (MCP) | CLI equivalent | Read-only |
|------------|----------------|-----------|
| `get_start_form_fields` | `pipefy pipe start-form` | Yes |
| `get_phase_fields` | `pipefy field list --phase` | Yes |
| `get_automation_events` | `pipefy automation events list` | Yes |
| `get_automation_actions` | `pipefy automation actions list` | Yes |
| `get_automation_event_attributes` | `pipefy automation event-attributes` | Yes |
| `create_automation` | `pipefy automation create` | No |
| `update_automation` | `pipefy automation update` | No |
| `get_automation` | `pipefy automation get` | Yes |
| `get_pipe` | `pipefy pipe get` | Yes |

`get_automation_event_attributes` is the **official** token probe. Treat it
as incomplete: it currently returns only
`%{automation_event_execution_datetime}`. Use the tables below for the rest,
then verify with `get_automation` on a working rule.

## Native vs iPaaS

| Job | Where |
|-----|--------|
| Sum, IF, string, weekday, stamp, copy on the **same card** | Native formula (this skill) — immediate |
| Condition on a field (equals / blank / date_is) | Native `condition` on the rule — not a formula |
| Slack, Gmail, Sheets, HTTP, queue, subflow | iPaaS |
| More than 20 field references | Split rules or iPaaS |

## Steps — stamp a formula

1. **Discover `internal_id`s** (digits only).

   MCP:
   ```
   get_start_form_fields pipe_id=<pipe_id>
   get_phase_fields phase_id=<phase_id>
   ```

2. **Discover event × action.** `update_card_field` + `field_map` is the
   usual action. Confirm the event appears in the action's `triggerEvents`.

   MCP:
   ```
   get_automation_events pipe_id=<pipe_id>
   get_automation_actions pipe_id=<pipe_id>
   get_automation_event_attributes
   ```

3. **Build `value`.** Field refs are `%{INTERNAL_ID}`. Connector paths
   chain with `.` for as many hops as the card graph needs:
   `%{A.B}`, `%{A.B.C}`, `%{A.B.C.D.E.F…}` — each segment is an
   `internal_id`. Quote rules depend on the function — see below.
   Hard cap: **20 fields**.

4. **Create the rule disabled**, then read it back.

   MCP:
   ```
   create_automation pipe_id=<pipe_id> name="<name>" trigger_id=card_created action_id=update_card_field active=false extra_input={"action_params":{"card_id":"%{id}","field_map":[{"fieldId":"<dest_internal_id>","inputMode":"copy_from","value":"<formula>"}],"fields_map_order":["<dest_internal_id>"]}}
   get_automation automation_id=<id>
   ```

   CLI:
   ```bash
   pipefy automation create --pipe <pipe_id> --name "<name>" --trigger card_created --action update_card_field --active false
   pipefy automation get <id>
   ```

5. **Enable** only after `field_map` round-trips:
   `update_automation` with `extra_input={"active": true}`
   (`active` is not a top-level arg on update).

## Functions

Match argument **type** and **quotes** or the field stays blank. "Numeric"
means a number literal or a numeric `%{field}` — no quotes. "Any value"
means number, text, or token; **text** (and, where noted, **field tokens**)
must be wrapped in double quotes inside the function.

| Function | Arg type | Quotes |
|----------|----------|--------|
| `SUM( )` | numeric | none |
| `AVERAGE( )` | numeric | none — **returns an integer** |
| `MIN( )` / `MAX( )` | numeric | none |
| `MULTIPLY( )` / `DIVIDE( )` / `SUBTRACT( )` | numeric | none |
| `COUNT( )` | any | texts **including fields** in double quotes |
| `ROUND( )` | numeric | none; optional decimal-places argument |
| `ROUNDUP( )` / `ROUNDDOWN( )` | numeric | none; optional decimal places |
| `IF_NULL( )` | any | texts in double quotes; **do not** quote fields |
| `SIN( )` / `COS( )` / `TAN( )` | numeric | none. Radians, not degrees. `SIN(90)` = 0.8939966636005579 |
| `IF( )` | any | `IF(logical, valueIfTrue, valueIfFalse)`. Texts **including fields** in double quotes |
| `LEFT( )` / `RIGHT( )` | any | `LEFT("string", count)`. Texts **including fields** in double quotes |
| `MID( )` | any | `MID("string", position, count)`. `MID("Olá, mundo!", 1, 3)` = `Olá`. Texts **including fields** in double quotes |
| `LEN( )` | any | texts **including fields** in double quotes |
| `FIND( )` | any | `FIND("mundo", "Olá, mundo!")` = 6. Texts **including fields** in double quotes |
| `SUBSTITUTE( )` | any | `SUBSTITUTE("Olá, mundo!", "Olá", "Oi")` = `Oi, mundo!`. Texts **including fields** in double quotes |
| `CONCAT( )` | any | texts **including fields** in double quotes. `CONCAT("Olá", ", ", "mundo", "!")` = `Olá, mundo!` |
| `CONTAINS( )` | any | texts **including fields** in double quotes. `CONTAINS("Olá", "Olá, mundo!")` = true |
| `ADD_WEEKDAYS( )` | date only | `ADD_WEEKDAYS(date, interval)`. Token (`%{due_date}`, `%{created_at}`, `%{automation_event_execution_datetime}`, …) **or** handwritten `aaaa-mm-dd`. `ADD_WEEKDAYS(2026-01-31, 1)` = `2026-02-03T00:00:00Z` |
| `SUBTRACT_WEEKDAYS( )` | date only | same date args as `ADD_WEEKDAYS`. `SUBTRACT_WEEKDAYS(2026-01-31, 1)` = `2026-01-29T00:00:00Z` |
| `INTERVAL_WEEKDAYS( )` | date only | two dates (tokens or handwritten `aaaa-mm-dd`). `INTERVAL_WEEKDAYS(2026-01-31, 2026-02-03)` = 1 |
| `WEEKDAY( )` | date only | token or handwritten `aaaa-mm-dd`. `WEEKDAY(%{created_at})` is valid. `WEEKDAY(2026-01-31)` = 7 |
| `TO_HOURS( )` / `TO_MINUTES( )` | numeric | none. `TO_HOURS(1.5)` = 36.0; `TO_MINUTES(1.5)` = 2160.0 |

## Operators

- Math: `+` `-` `*` `/` `%` `^`
- Compare: `<` `>` `<=` `>=` `=` `!=`
- Date `+` / `-` number → date
- Date `-` date → day count
- Date `>` `<` `=` date → `true` / `false`

## Tokens (event & card)

Official docs and `get_automation_event_attributes` cover only a subset.
These work in `field_map.value` at runtime:

| Token | Meaning / format |
|-------|------------------|
| `%{automation_event_execution_datetime}` | Event time (`2026-12-01T23:59:59-03:00`) — the official catalog row |
| `%{id}` | Card id (also set `action_params.card_id` to this) |
| `%{title}` | Card title |
| `%{created_at}` / `%{finished_at}` / `%{due_date}` | Timestamps |
| `%{current_phase}` / `%{last_phase_in}` | Phase **name** |
| `%{labels}` | Label names |
| `%{assignees}` | Assignee **names** |
| `%{created_by}` | Creator **name** |
| `%{all_emails}` / `%{all_emails_with_attachments}` | Indexed FROM/TO/CC/BCC/SUBJECT/BODY block |
| `%{last_email}` / `%{last_email_with_attachments}` | Same shape, last message only |
| `%{all_comments}` / `%{last_comment}` | Comment text (indexed when "all") |
| `%{INTERNAL_ID}` | Field on the card |
| `%{A.B.C.D…}` | Connector chain, **any depth**. Each segment is an `internal_id` (not a slug). |

Date tokens accept `|plus:SECONDS` / `|minus:SECONDS` (the number is seconds).
Example: created-at plus one hour → `%{created_at|plus:3600}`.

## Quote and type rules (easy to get wrong)

- **Numeric-only** functions (`SUM`, `AVERAGE`, `MIN`, `MAX`, `MULTIPLY`,
  `DIVIDE`, `SUBTRACT`, `ROUND`/`ROUNDUP`/`ROUNDDOWN`, trig, `TO_HOURS`,
  `TO_MINUTES`): never quote the number or the numeric field token.
- **Any value + quotes including fields:** `COUNT`, `IF`, `LEFT`/`RIGHT`/`MID`,
  `LEN`, `FIND`, `SUBSTITUTE`, `CONCAT`, `CONTAINS`. A field token used as
  text is `"%{INTERNAL_ID}"` or `"%{assignees}"`, not a bare `%{assignees}`.
- **Any value, quote texts but not fields:** `IF_NULL` only.
- **Date-only:** `WEEKDAY`, `ADD_WEEKDAYS`, `SUBTRACT_WEEKDAYS`,
  `INTERVAL_WEEKDAYS`. Tokens (`%{created_at}`, `%{due_date}`,
  `%{automation_event_execution_datetime}`, field ids) are valid.
  Handwritten `aaaa-mm-dd` is a date typed literally in the formula.
- Trig functions take **radians**.
- `AVERAGE` truncates to an **integer**.
- Inside `CONCAT`, a numeric expression (`INTERVAL_WEEKDAYS(...)`,
  `ROUNDDOWN(...)`) stays unquoted; a text literal or a name token is quoted.
- `get_automation_event_attributes` will **not** list the functions or most
  tokens above. Missing from that tool is not evidence the formula is invalid.

## Worked example — timesheet HH:MM

Trigger: `field_updated` on a numeric field whose `internal_id` you substitute
for every `%{duration_decimal}` below (days in decimal, e.g. `0.5` = 12 hours).
Action: `update_card_field` into a **short/long text** destination (the
formatted duration). Guard: only format values `< 1` day; otherwise stamp
`00:00`.

Replace `%{duration_decimal}` with `%{<numeric_internal_id>}`. Pad hours and
minutes so `0.04167` (1 hour) becomes `01:00`, not `1:0`.

```
IF(
  %{duration_decimal} < 1,
  CONCAT(
    IF(
      ROUNDDOWN(TO_HOURS(%{duration_decimal})) < 10,
      CONCAT("0", ROUNDDOWN(TO_HOURS(%{duration_decimal}))),
      ROUNDDOWN(TO_HOURS(%{duration_decimal}))
    ),
    ":",
    IF(
      ROUND((TO_HOURS(%{duration_decimal}) - ROUNDDOWN(TO_HOURS(%{duration_decimal}))) * 60) < 10,
      CONCAT("0", ROUND((TO_HOURS(%{duration_decimal}) - ROUNDDOWN(TO_HOURS(%{duration_decimal}))) * 60)),
      ROUND((TO_HOURS(%{duration_decimal}) - ROUNDDOWN(TO_HOURS(%{duration_decimal}))) * 60)
    )
  ),
  "00:00"
)
```

This is Excel-style nested `IF` + `CONCAT` + `TO_HOURS` on the card, with
**no iPaaS delay**. Create the rule `active=false`, round-trip with
`get_automation`, then enable.

## Worked example — SLA digest

Trigger: `field_updated` on due date (or `card_created` if due date is on
the start form). Action: stamp a **text** field used for filters / reports.
The formula uses **tokens** (not handwritten dates): weekday of the deadline,
business-day span from creation, remaining business days from *this*
automation run, and assignee **names** (`%{assignees}` quoted inside
`CONCAT`, because CONCAT treats fields as text).

```
CONCAT(
  IF(
    WEEKDAY(%{due_date}) = 7,
    "FIM DE SEMANA | ",
    ""
  ),
  IF(
    INTERVAL_WEEKDAYS(%{created_at}, %{due_date}) <= 1,
    "SLA CRITICO | ",
    IF(
      INTERVAL_WEEKDAYS(%{created_at}, %{due_date}) <= 3,
      "SLA APERTADO | ",
      "SLA FOLGADO | "
    )
  ),
  "restam ",
  INTERVAL_WEEKDAYS(%{automation_event_execution_datetime}, %{due_date}),
  " dia(s) util(eis) | ",
  "%{assignees}"
)
```

Power the agent should copy: nested `IF`, `WEEKDAY` on `%{due_date}`,
`INTERVAL_WEEKDAYS` on `%{created_at}` / `%{automation_event_execution_datetime}`,
and `"%{assignees}"` (quoted — CONCAT, texts including fields). None of
this appears in `get_automation_event_attributes`. Do not send this to iPaaS.

## Success criteria

- `fieldId` is a numeric `internal_id`; `card_id` is `"%{id}"` for the
  triggering card.
- `get_automation` shows the formula in `action_params.field_map`.
- Field count in the expression is ≤ 20.
- The agent did not send the user to iPaaS for same-card math.

## Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| Field unchanged | Slug in `fieldId`, typo in `%{…}`, or missing quotes on a text/field inside CONCAT/IF/COUNT | `internal_id`; quote `"%{assignees}"` in CONCAT; do not quote numeric args |
| `get_automation_event_attributes` has one row | Official catalog is event-scoped and incomplete | Use the tables here; verify via `get_automation` |
| Create rejected | Unknown `fieldId` or incompatible event×action | Rediscover fields on `action_repo_id`; check `triggerEvents` |
| `update_automation` ignores `active` | `active` is not top-level on update | `extra_input={"active": true}` |
| Trig looks "wrong" | Argument was degrees | Convert to radians or avoid SIN(90) as a degrees test |
| Weekday / interval looks empty | Typo in the token, not the format | Tokens are valid; `aaaa-mm-dd` is only for handwritten literals |
| More than 20 fields | Platform cap | Split into two rules |
| iPaaS suggested for SUM/IF | Agent routed to the wrong skill | Stay on native `update_card_field` |

## See also

- [skills/automations/pipefy-automations/SKILL.md](../pipefy-automations/SKILL.md) — create/update the rule, conditions, AI prompts.
- [docs/mcp/tools/automations-and-ai.md](../../../docs/mcp/tools/automations-and-ai.md) — official token subset and `field_map` shape.
- [skills/ipaas/pipefy-ipaas/SKILL.md](../../ipaas/pipefy-ipaas/SKILL.md) — when an external app is required.
