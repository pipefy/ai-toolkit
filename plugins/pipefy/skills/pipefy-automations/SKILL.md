---
name: pipefy-automations
description: >
  Use this skill when the user wants to create, read, update, or delete
  traditional automations (if/then rules) or AI automations (prompt-driven).
  For AI agents (conversational), see `pipefy-ai-agents`.
tags: [pipefy, automations, ai-automations, rules]
---

# Automations

Read only the reference for your active surface: [MCP](references/mcp.md) or [CLI](references/cli.md). The workflows below use shared operation names and arguments.

Traditional automations (if/then rules), AI automations (prompt-driven), task automations, and simulation.

For AI agents (conversational agents with behaviors), see `pipefy-ai-agents`.

---

## Start state

A build request defaults to `build`. The `build` and `build inactive` levels apply with or without a `pipefy-process-design` specification. Without a specification, the request that you restated to the user is the reference for each check in this section. Automations for a process created in this conversation start on. Test each part with acceptance cards before real cards arrive.

In this section, a pipe with cards has cards that existed before this build. Acceptance cards that the build creates do not count. After the tests, delete the acceptance cards with the usual delete confirmation.

Create an automation off only in these cases:

- The user asks for `build inactive`, in any words.
- The pipe existed before this conversation and has cards that the rule can match.
- A time rule or a scheduled rule runs in a pipe with cards.
- The rule reads a business assumption that the user did not confirm.
- A move needs a phase connection that does not exist.

For the existing-card and time-rule cases, read the saved rule and compare it with the specification, or with the restated request when no specification exists. If no other off case applies, activate the rule in the same build. Do not ask for another yes.

Keep a rule off when the user asked for it, until the user permits activation. Keep a rule with a pending assumption off until the user confirms that assumption. Keep a rule with a missing connection off until that connection exists. Activate only when none of these conditions still requires an off state. If the tool rejects a missing connection, skip that rule until the connection exists.

Create traditional and task automations with `active=false` for an off case. Otherwise, use `active=true`. For an AI automation that must start off, use "Create an AI automation inactive" below. Each webhook, email outside the company, or member invitation still needs its own yes. That yes does not change the build level.

---

## Traditional automations (rules engine)

| Operation | Purpose |
| ------------ | --------- |
| `get_automations` | List rules with `event_id`, `event_params`, `condition`, `actionEnabled`, and `disabledReason`. Empty condition expressions are API placeholders, not active filters. Pages hold at most 50 rules; continue with `after` before concluding a rule or filter does not exist. |
| `get_automation` | Single automation with full rule config — returns `event_params` and `action_params` (including `aiParams` for AI rules). |
| `create_automation` | Create an if/then rule. `active` defaults to true. First-class typed `condition` (see [Conditions](#conditions--gate-a-rule-on-field-tests)); other fields via `extra_input`. |
| `update_automation` | Patch a rule: first-class typed `condition` (see [Conditions](#conditions--gate-a-rule-on-field-tests)) and/or `extra_input`. |
| `delete_automation` | Destructive delete. |
| `simulate_automation` | **AI-only** dry-run (`generate_with_ai` action). |
| `get_automation_events` | Available trigger events. |
| `get_automation_event_attributes` | Official `field_map.value` event-attribute tokens. |
| `get_automation_actions` | Available action types for a pipe. |
| `create_send_task_automation` | Shortcut for send-a-task rules. |

Logs, usage, and job exports for automations live in `pipefy-observability` (`get_automation_logs`, `get_automation_logs_by_repo`, `get_automations_usage`, `export_automation_jobs`, and related tools).

---

## AI automations (prompt-driven)

**Consent:** create or suggest an AI automation only when the user explicitly asked for AI. If it seems useful but was not requested, ask first — never introduce AI automations without being asked.

| Operation | Purpose |
| ------------ | --------- |
| `get_ai_automations` | List `generate_with_ai` rules from the pipe's mixed listing. Each page contains at most 50 mixed rules; continue with `after` before concluding an AI rule does not exist. |
| `get_ai_automation` | Full config including prompt, fields, condition. |
| `create_ai_automation` | Create a prompt-driven automation (requires AI enabled on the pipe). |
| `update_ai_automation` | Change name, `active`, prompt, `field_ids`, or `condition`. |
| `delete_ai_automation` | Destructive delete. |
| `validate_ai_automation_prompt` | **Pre-flight check.** Returns `{valid, problems, warnings, field_map}` — also detects prompt `%{id}` ∩ `field_ids` overlap. |

---

## Steps — create an AI automation

1. **Discover field `internal_id`s** for any field referenced in the prompt:

   ```
   get_phase_fields phase_id="<phase_id>"
   ```

2. **Build the prompt** with `%{<internal_id>}` references. Pipefy silently rejects prompts with no field reference (returns `"Input parameters are required."`).

   **Important:** the `%{...}` wrapper and a **numeric** field `internal_id` from *your* pipe are required — the exact digits in examples below (e.g. `900000101`) are fictional placeholders. Discover real IDs via `get_phase_fields` / `get_start_form_fields`; do not copy example numbers from docs.

3. **Validate the prompt:**

   ```
   validate_ai_automation_prompt pipe_id=67890 prompt="Summarize %{900000102} into the summary field." field_ids=["900000101"]
   ```

   Returns `valid:true|false`, `problems`, `warnings`, `field_map`. Catches mistakes in one read-only call vs 2–3 failed mutation roundtrips.

4. **Create the automation** (only if `valid:true`): use the selected event ID, pipe ID, prompt, output field IDs, and a name. MCP accepts these as `event_id`, `pipe_id`, `prompt`, `field_ids`, and `name`; the SDK takes a `CreateAiAutomationInput` containing them. See the active surface reference for invocation syntax.

---

## Create an AI automation inactive

Use this recipe when "Start state" requires an inactive AI automation. `create_ai_automation` has no `active` input. It creates an active rule. Do not create an active rule and then disable it. Use one `create_automation` call with `active=false`.

1. Read the input and output field `internal_id` values from the pipe.
2. Run `validate_ai_automation_prompt` with the `pipe_id`, the prompt, the output `field_ids`, and the selected `event_id`. The `event_id` check catches an event that the pipe does not have, because `create_automation` does not run the event checks of `create_ai_automation`. Do not use `scheduler`: `create_ai_automation` rejects it as an AI automation event. Continue only when `valid` is true.

   ```text
   validate_ai_automation_prompt pipe_id=67890 prompt="Summarize %{900000102} into the summary field." field_ids=["900000101"] event_id=card_created
   ```

3. Use `action_id=generate_with_ai` and `active=false` in `create_automation`. Put the prompt in `extra_input.action_params.aiParams.value`. Put output field ids in `fieldIds` and AI skill ids in `skillsIds`. Use an empty `skillsIds` list when no AI skill applies. Preserve the selected `event_params` and `condition` in `extra_input`. Without a user condition, send the explicit default condition from the example.

The ids below are examples. Replace them with ids from the pipe. This example uses `card_created`, which needs no `event_params`:

```text
create_automation pipe_id=67890 name="Summarize intake" trigger_id=card_created action_id=generate_with_ai active=false extra_input={"action_params":{"aiParams":{"value":"Summarize %{900000102} into the summary field.","fieldIds":["900000101"],"skillsIds":[]}},"condition":{"expressions":[{"structure_id":0,"field_address":"","operation":"","value":""}],"expressions_structure":[[0]]}}
```

4. Read the created rule with `get_ai_automation`. Make sure that `active` is false and the prompt, fields, event, and condition match the request.
5. Test the saved prompt on acceptance cards with [Steps: simulate an AI automation](#steps-simulate-an-ai-automation). If the output differs from the expected result, keep the rule off.
6. For a temporary off case, use `update_ai_automation` with `active=true` after the read and acceptance tests. Keep the rule off if another off case still applies. Read the rule again after activation.

The [MCP reference](references/mcp.md#create-an-ai-automation-inactive) and the [CLI reference](references/cli.md#create-an-ai-automation-inactive) show where each surface returns the new automation id, and the activation call.

---

## Steps — create a traditional automation

1. **Discover events** for the pipe: `get_automation_events pipe_id=67890`.
2. **Discover actions** for the pipe: `get_automation_actions pipe_id=67890`. (Always discover first; never guess `trigger_id` / `action_id`.)
3. **Check event×action compatibility**: the pair is invalid when the chosen `event_id` appears in that action's `eventsBlacklist` (from `get_automation_actions`). Do not gate on `triggerEvents`, which lists something else. See [Event×action compatibility](#eventaction-compatibility).
4. **Build the rule** with the discovered IDs and call `create_automation`.
5. **Verify** by reading back with `get_automation`.

---

## Conditions — gate a rule on field tests

`create_automation` and `update_automation` take a first-class `condition`. Do **not** guess the shape from GraphQL introspection — it is:

```json
{
  "expressions": [
    {"field_address": "900000101", "operation": "equals", "value": "Done", "structure_id": 0}
  ],
  "expressions_structure": [[0]]
}
```

- `field_address` is the field **`internal_id`** (numeric, from `get_start_form_fields` / `get_phase_fields`), **not** the slug. For a connected card's field use `<connectorFieldId>.<targetFieldId>`.
- `operation` (soft enum — any value is passed through, the API validates): `equals`, `not_equals`, `present`, `blank`, `string_contains`, `string_not_contains`, `number_greater_than`, `number_less_than`, `date_is_today`, `date_is_yesterday`, `date_in_current_week`, `date_in_last_week`, `date_in_current_month`, `date_in_last_month`, `date_in_current_year`, `date_in_last_year`, `date_is`, `date_is_after`, `date_is_before`. Omit `value` for `present` / `blank`.
- `expressions_structure` groups expressions by `structure_id`, not by position. The expressions in one inner array are AND'd, and the inner arrays are OR'd: `[[0, 1], [2]]` is `(expr0 AND expr1) OR expr2`, `[[0, 1]]` is `expr0 AND expr1`, and `[[0], [1]]` is `expr0 OR expr1`. Give each expression its own `structure_id`. Two expressions that share one, sent as `[[0], [0]]`, save with `expressions` empty and `expressions_structure` still `[[0], [0]]`. That rule does not match cards.
- The API drops what it cannot use without returning an error: a number that matches no `structure_id`, an empty inner array, an expression whose `structure_id` is not listed, and an expression with no `field_address` or `operation`. Dropping one expression from an AND group makes that group easier to satisfy, so the rule can match more cards (`[[0, 1]]` with one expression dropped saves as `[[0]]`). Dropping the only expression in an OR group removes that group, so the rule matches fewer cards (`[[0], [1]]` with one expression dropped saves as `[[0]]`). Read the rule back with `get_automation` after a write. An empty `expressions_structure` matches every card. A number listed twice fails with `is invalid`.

Omit `condition` to leave a traditional rule unconditional (no default is injected). A `condition` argument wins over any `condition` in `extra_input`.

---

## Steps — update a card field with a dynamic value

Use when the user wants an if/then rule to **stamp or copy values** onto the triggering card (for example, set a datetime when `card_created` fires). This is **`create_automation`** with `action_id: update_card_field` and `extra_input.action_params.field_map` — **not** the one-off `update_card_field` operation (that tool uses field **slug** for one-off card edits).

1. **Discover field `internal_id`s** (digits only — never slug in `fieldId`):

   ```
   get_start_form_fields pipe_id=67890
   get_phase_fields phase_id="<phase_id>"
   ```

2. **Discover trigger, action, and event-attribute tokens:**

   ```
   get_automation_events pipe_id=67890
   get_automation_actions pipe_id=67890
   get_automation_event_attributes
   ```

   For `update_card_field`, `acceptedParameters` omits `field_map`; use the payload shape below (see [docs/mcp/tools/automations-and-ai.md](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/automations-and-ai.md)). Prefer `value_token` from `get_automation_event_attributes` when stamping execution time.

3. Use the state from "Start state". This example assumes a temporary off case. For that case, create disabled (`active=false`):

   ```
   create_automation pipe_id=67890 name="Stamp execution time on new cards" trigger_id=card_created action_id=update_card_field active=false extra_input={"action_params":{"card_id":"%{id}","field_map":[{"fieldId":"<destination_internal_id>","inputMode":"copy_from","value":"%{automation_event_execution_datetime}"}],"fields_map_order":["<destination_internal_id>"]}}
   ```

   Common `value` tokens when `inputMode` is `copy_from`: `%{id}` (also use in `card_id`), `%{created_at}`, `%{automation_event_execution_datetime}`, `%{<other_internal_id>}` to copy another field.

4. **Verify persisted config:**

   ```
   get_automation automation_id=<id>
   ```

   Confirm `action_params.field_map` round-tripped.

5. **Enable** when correct:

   ```
   update_automation automation_id=<id> extra_input={"active":true}
   ```

---

## Steps: simulate an AI automation

`simulate_automation` is **AI-only** today (only `generate_with_ai` `action_id` is accepted). For non-AI rules, watch `get_automation_logs` after the trigger fires.

1. Read the saved rule with `get_automation automation_id=<id>`. Keep its `event_id`. Use only its saved `aiParams` inside `action_params`.
2. Build `event_params` from the saved non-null values, without `phase`. For `card_created`, omit `event_params`.
3. Simulate on a sample card with those inputs. The example rule uses `card_created`:

   ```
   simulate_automation pipe_id=67890 action_id=generate_with_ai sample_card_id=456 event_id=card_created action_params={"aiParams":{"value":"Summarize %{900000102} into the summary field.","fieldIds":["900000101"],"skillsIds":[]}}
   ```

4. Read the immediate result. It can contain `simulation_id`, `status:"processing"`, and a null `simulationResult`. Keep the ID. Each `simulate_automation` call starts a new simulation. Read the existing simulation through `execute_graphql`:

   ```graphql
   query { automationSimulation(simulationId: "<simulation_id>") { status simulationResult details { errorType message } } }
   ```

   Re-read after a short wait until `status` leaves `processing`. If it is still processing after a few reads, report the result as pending with the ID.

---

## Traditional automation preflight

### Event×action compatibility

The constraint is a denylist. A pair is invalid when the `event_id` appears in that action's `eventsBlacklist` (`get_automation_actions`), which is the same thing as the `action_id` appearing in that event's `actionsBlacklist` (`get_automation_events`): the two lists agree on every entry of the catalog, so either one answers the question.

`triggerEvents` is not that list and must not be used as a gate. It reflects which pairings the builder offers first, so a membership test on it refuses pairs the denylist allows: `field_updated` + `move_single_card` is absent from `triggerEvents`, and that rule creates and moves the card. Three shapes in the catalog break such a test. `send_a_task` and `send_email_template` return `triggerEvents: []` while the denylist allows them on 7 and 9 of the 10 events; `schedule_create_card` and `move_multiple_cards` list their own `eventsBlacklist` entries inside `triggerEvents`; and every action with a non-empty `triggerEvents` is allowed by the denylist on events outside it.

`create_automation` enforces the denylist. It rejects a blacklisted pair with an untranslated error whose readable part is the key `event_action_blacklist`, and writes nothing. Read that key as "this event cannot drive this action" and pick another pair.

`update_automation` does not enforce it. Patching a stored rule's `event_id` to an event on its action's `eventsBlacklist` succeeds and persists: a rule created as `card_created` + `move_single_card` accepts an update to `scheduler` + `move_single_card`, which create refuses. So a blacklisted pair can exist on a rule that was updated into it, and checking the denylist before an update is the caller's job, not the API's.

### Catalog spelling is not input spelling

`get_automation_events` reports `acceptedParameters` in snake_case; `AutomationEventParamsInput` defines all but one of them in camelCase. Sending the catalog spelling fails with `Field is not defined on AutomationEventParamsInput`. The full mapping:

| Parameter | Catalog spelling | `event_params` key to send |
|---|---|---|
| Trigger fields | `trigger_field_ids` | `triggerFieldIds` |
| SLA kind | `kind_of_sla` | `kindOfSla`, values capitalized: `Expired`, `Late`, `Overdue` |
| Origin phase | `from_phase_id` | `fromPhaseId` |
| Current phase | `in_phase_id` | `inPhaseId` |
| Upstream rule | `trigger_automation_id` | `triggerAutomationId` |
| Destination phase | `to_phase_id` | `to_phase_id`, the only key that stays snake_case |

Recurring rules take their schedule outside `event_params`: `scheduler_frequency` (`hourly`, `daily`, `weekly`, `monthly`) plus `schedulerCron`, which is an object of five required strings (`minute`, `hour`, `dayOfMonth`, `month`, `dayOfWeek`), not a cron string.

### Field changes and phase restrictions

For `field_updated`, `triggerFieldIds` selects which fields changed. It does not limit the card's current phase. `get_automation_events` lists only `trigger_field_ids` for this event. `in_phase_id` belongs to `card_inbox_received_email`, not `field_updated`.

If the specification limits the current phase, preserve that restriction with a separate supported condition. Do not omit that restriction or invent an event parameter, condition field, or operation. If no supported condition preserves the restriction, create the rule off and report the requirement as pending or manual. Do not activate the rule or report it ready while the restriction is absent. Passing examples do not resolve that mismatch.

### Applying a label has no automation action

**Hard stop:** no action in the catalog applies a label to a card. The **action** is what is missing, not the trigger: `sla_based` is in the event catalog, so "when the card goes overdue" is a perfectly good trigger with nothing to attach to. `get_automation_actions(pipe_id)` is the dynamic source of truth for what a given pipe offers; read it before planning a rule and do not assume a label action exists.

What to do with that intent:

1. **Send the intent to the product, not to a script.** A label rule belongs in the customer's process, where it keeps firing without anyone driving it. The API cannot create it, so hand the user a manual step: configure the rule in Pipefy and confirm there what the interface offers for that trigger. State that step in the plan or summary you hand the user, the same way you would for an email template.
2. **Offer the rule that does exist, when it fits.** `update_card_field` accepts `sla_based`, so "when the card goes overdue, stamp a field on the card" is createable through `create_automation` today. A status or flag field carries the same signal as a label and keeps the rule inside the process. Discover a suitable destination field first with `get_start_form_fields` / `get_phase_fields`: many pipes have no field named Status, and the automation needs a real `internal_id`. Propose it, do not impose it: the user may want the label specifically.

   `sla_based` takes its parameter as `event_params.kindOfSla`, **camelCase**, even though `get_automation_events` reports it as `kind_of_sla`. Values are capitalized: `Expired`, `Late`, `Overdue`. Sending the catalog spelling fails with "Field is not defined on AutomationEventParamsInput". Shape the action with the `field_map` recipe below, including `inputMode`.
3. **`update_card(label_ids=[...])` is a one-off correction, not automation.** It **replaces** the card's whole label list: include every id that should remain; do not send only the new one. Something has to run the call every time. Nothing persists as process behavior once the session ends. Use it to fix specific cards the user points at, and say so plainly. **Do not call it across a set of cards to stand in for the rule**, and do not loop it on a schedule: that makes the agent the runtime instead of the process.
4. **Label CRUD is a different thing.** `create_label`, `update_label` and `delete_label` manage the label definitions on a pipe (name, color). None of them applies a label to a card, and none of them is the automation action.
5. **Do not offer an AI automation or agent behavior as the alternative.** Some organizations forbid AI in their processes, and the [consent rule](#ai-automations-prompt-driven) applies here: propose AI only when the user explicitly asked for it.

### `field_map` destination `fieldId`

On `create_automation`, when `extra_input.action_params.field_map` is present, the SDK checks each `fieldId` against numeric `internal_id` values on the action pipe (`action_repo_id`, default `pipe_id`). Slug-shaped `fieldId` values and unknown numeric ids fail before GraphQL with the offending id. Recovery: `get_start_form_fields` / `get_phase_fields` → use `internal_id`, not slug.

### Phase transition (`move_single_card`)

For `move_single_card` actions with trigger `card_moved`, **`create_automation` only** validates that the destination phase is reachable from the source via `cards_can_be_moved_to_phases` (same read-only data as `move_card_to_phase`). `update_automation` does not run this check.

If invalid, read the error message listing permitted destination phases and the UI-only transition configuration hint.

Recovery: read the allowed phases in `error.message`, or call `get_phase_allowed_move_targets(phase_id=<source_phase_id>)` on the source phase from `event_params.to_phase_id`, then re-issue `create_automation` with a permitted destination phase id.

---

## Notification disambiguation

Pick the right tool for "notification" intent:

| User signal words | Tool | Why |
|-------------------|------|-----|
| "notificação", "tarefa", "lembrete para alguém validar" | `create_send_task_automation` | Built-in: handles `event_id`, `task_title`, `recipients`, optional `event_params` and `condition`. |
| "enviar e-mail", "responder ao cliente" | `send_email_with_template` / `send_inbox_email` (`pipefy-members-email-webhooks`) | Email surface, not automations. |
| "webhook", "chamar serviço externo" | `create_webhook` (`pipefy-members-email-webhooks`) | HTTP callback on card events. |
| "automação", "regra if/then" | `create_automation` | Generic rules engine. |

Do NOT hand-build `action_params.taskParams` via `create_automation` when `create_send_task_automation` is the right tool.

An automation that sends email depends on a template that already exists: template create, edit and delete have no API path, only the Pipefy UI. When the process needs a new or changed template, state that manual UI step in the plan or summary you give the user.

---

## Agentic + human-in-the-loop pattern

Combine AI automations with task automations so AI handles routine work and humans validate high-impact decisions. The highest-leverage pattern in the catalog.

Example flow:

1. `create_ai_automation`: when card enters "Análise", AI fills classification and risk fields automatically.
2. `create_send_task_automation`: when the AI-filled field is updated, send a task to the manager — "Validate the classification on card [title]".
3. `create_automation` or `create_field_condition`: when the manager marks "Approved", move the card to the next phase.

Use this pattern for approvals, financial decisions, content publication, and any step where errors have real-world consequences. See also: `pipefy-process-design` Orchestration patterns.

---

## Success criteria

- `get_automation` returns the new rule with correct trigger and actions.
- `validate_ai_automation_prompt` returns `valid:true` before AI automation creation.
- `simulate_automation` (AI rules) returns a simulation ID; a follow-up `automationSimulation` read returns the final `simulationResult`, or the result is reported as pending with the ID.

## Failure modes

### Automation did not fire / empty logs

1. `get_automation` — re-read the rule and its `condition`.
2. Check the pairing against the denylist (see [Event×action compatibility](#eventaction-compatibility)). Create refuses a blacklisted pair, but update does not, so a rule that was patched after creation can hold one. Then confirm the event actually occurred on the card.
3. Empty logs are not proof of a platform outage. The rule may be inactive (`active: false`), have its action turned off (`actionEnabled: false`, with `disabledReason`), or simply not have been triggered yet.
4. Invalid `fieldId` in `field_map` may fail without updating the card (see below).
5. Read the tool error payload and required-field / phase-transition hints **before** concluding "service unavailable" or blaming the platform.

### Other failure modes

- **`simulate_automation` is AI-only.** Only `generate_with_ai` `action_id` accepted. For traditional rules, use `get_automation_logs` after the rule fires.
- **Async simulation result.** A `processing` response has no final result yet. Keep the `simulation_id` and read it with the `automationSimulation` query through `execute_graphql` (see [Steps: simulate an AI automation](#steps-simulate-an-ai-automation)). `get_automation_logs` requires a real automation ID, and another `simulate_automation` call starts a new simulation.
- **`validate_ai_automation_prompt` returns `valid:false`.** Read `problems` (per-field) and `warnings`. Most common: prompt missing `%{internal_id}` reference, or `field_ids` overlap with prompt `%{id}` tokens.
- **`create_automation` cycle detection.** Same-pipe `card_created` + `create_card` rejected with `"This automation can't be created! It would result in an endless card creation cycle."` Use a different trigger, target a different pipe, or use `update_card` instead.
- **`create_automation` fails with unknown event/action.** Always run `get_automation_events` + `get_automation_actions` first; do not guess IDs.
- **Planned a rule that applies a label.** No such action exists in the catalog. The trigger does: `sla_based` is available, so only the label action is missing. See [Applying a label has no automation action](#applying-a-label-has-no-automation-action) before offering anything else.
- **Phase transition error on `move_single_card`.** Only `create_automation` preflights transitions. Read allowed phase ids in the error text or call `get_phase_allowed_move_targets`, then re-issue with a permitted destination. UI is the only edit surface for transition rules.
- **Cross-pipe `PERMISSION_DENIED`.** SA must be member of both source and destination pipes for `create_connected_card` / cross-pipe `create_card`. Recovery: `get_pipe_members` + `invite_members`.
- **`get_automation_logs_by_repo` returns empty.** Pipe has no traditional automation executions; not an error. AI agent executions are separate (see `get_ai_agent_logs`).
- **`create_send_task_automation` fires immediately when `active=true`.** Pass `active=false` first if you want to wire it up before the rule starts firing. The 2026-04-16 orphaned-task incident is the cautionary tale.
- **`update_automation` API asymmetry.** `create_automation` takes a top-level `active` param; `update_automation` requires `extra_input={"active": false}`. Pass `active` through `extra_input` when toggling on an existing rule.
- **`action_repo_id` semantics.** For cross-pipe actions (`create_connected_card`, `create_card` into another pipe), this is the **destination** pipe, not the source.
- For simulation inputs, follow [Steps: simulate an AI automation](#steps-simulate-an-ai-automation). Use only the saved input fields. Remove response-only metadata.
- **`field_map` uses slug in `fieldId`.** Preflight rejects non-numeric `fieldId` before GraphQL; slugs (e.g. `due_date`) used to surface as `INTERNAL_SERVER_ERROR`. Recovery: `get_start_form_fields` / `get_phase_fields` → use `internal_id`.
- **Unknown `field_map` `fieldId`.** `create_automation` preflight fails with the offending id when the destination field is not on the action pipe. Re-discover ids on `action_repo_id` (not only the trigger pipe for cross-pipe actions).
- **Used `update_card_field` operation for a rule.** That tool updates one card by **slug**; automations need `create_automation` + `field_map` with numeric `fieldId`.
- **Missing or wrong `card_id`.** Set `action_params.card_id` to `"%{id}"` for the triggering card; empty/wrong values prevent the intended update.
- **Token typo in `field_map.value`.** Typos in `%{…}` templates leave fields unchanged at runtime. Compare with [Automation Event Attributes](https://developers.pipefy.com/reference/automation-event-attributes) and a working rule from `get_automation`.
- **Rule runs but field unchanged.** Check `get_automation_logs` / `get_automation_logs_by_repo` for execution errors; invalid `fieldId` may fail silently (no card update).

## See also

- `pipefy-building` — intent → domain skill router for build asks.
- `pipefy-ai-agents` — conversational agents with behaviors (different from AI automations).
- `pipefy-observability` — execution logs and usage stats.
- `pipefy-introspection` — discover trigger and action types via raw schema.
- `pipefy-process-design` — Orchestration patterns (agentic + human validation).
- [docs/mcp/tools/identifiers.md#field-references-slug-vs-internal_id](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/identifiers.md#field-references-slug-vs-internal_id) — canonical map of which tool/argument expects slug vs `internal_id` vs uuid vs numeric id (`field_address` and `field_map[].fieldId` want internal_id).
