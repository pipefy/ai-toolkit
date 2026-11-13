---
name: pipefy-ai-agents
description: >
  Use this skill when the user wants to create, read, update, delete,
  or troubleshoot AI agents (conversational agents with behaviors).
  Includes pre-flight validation and pipe-scoped
  knowledge bases (list, plain text/document/data lookup CRUD, access probe) attached via dataSourceIds.
  For traditional automations and AI automations, see `pipefy-automations`.
tags: [pipefy, ai-agents, behaviors, conversational]
---

# AI Agents

Read only the reference for your active surface: [MCP](references/mcp.md) or [CLI](references/cli.md). The workflows below use shared operation names and arguments.

Conversational AI agents attached to pipes. Each agent has an agent-level instruction and 1–5 behaviors, each with its own trigger event, prompt, and actions.

For traditional automations and AI automations (prompt-driven), see `pipefy-automations`.

---

## Tools

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_ai_agents` | Yes | List AI agents for a pipe (`repo_uuid` = pipe UUID, not numeric `id`). |
| `get_ai_agent` | Yes | Full agent config including behaviors. |
| `create_ai_agent` | No | Create a new conversational agent (active by default; see [Active lifecycle](#active-lifecycle) to start disabled). |
| `update_ai_agent` | No | **Full-replace** (not patch). Always send complete `behaviors`. Preserves disabled state. |
| `delete_ai_agent` | No | **Destructive; review and approve first.** |
| `toggle_ai_agent_status` | No | Explicit activate/deactivate. |
| `validate_ai_agent_behaviors` | Yes | **Pre-flight check before create/update.** |

Execution logs live in `pipefy-observability` (`get_ai_agent_logs`, `get_ai_agent_log_details`).

---

## Active lifecycle

A build request defaults to `build`. The `build` and `build inactive` levels apply with or without a `pipefy-process-design` specification. Without a specification, the request that you restated to the user is the reference for each check in this section. Agents for a process created in this conversation start on. Test each agent with acceptance cards before real cards arrive.

In this section, a pipe with cards has cards that existed before this build. Acceptance cards that the build creates do not count. After the tests and the log checks in "Verify", delete the acceptance cards with the usual delete confirmation.

Create an agent off only in these cases:

- The user asks for `build inactive`, in any words.
- The pipe existed before this conversation and has cards that the agent can match.
- A behavior uses a time limit in a pipe with cards.
- A behavior reads a business assumption that the user did not confirm.
- A move needs a phase connection that does not exist.

For the existing-card and time-limit cases, read the saved agent and compare it with the specification, or with the restated request when no specification exists. If no other off case applies, activate the agent in the same build. Do not ask for another yes.

Keep an agent off when the user asked for it, until the user permits activation. Keep an agent with a pending assumption off until the user confirms that assumption. Keep an agent with a missing connection off until that connection exists. Activate only when none of these conditions still requires an off state. If the tool rejects a missing connection, skip that agent until the connection exists.

An agent never uses `scheduler`. Use a traditional automation or an integration flow for a schedule. Each webhook, email outside the company, or member invitation still needs its own yes. That yes does not change the build level.

- Agents are **active by default**. Create-active clears the API default disabled shell via the configure update (omits `disabledAt`). Create-inactive (`disabled_at` set on the input to the current time, as an ISO-8601 UTC timestamp) sets `disabled_at` explicitly on create and the chained update.
- Routine `update_ai_agent` **preserves** disabled state — it does not intentionally reactivate. Prefer passing `disabled_at` from a prior `get_ai_agent` (`disabledAt`) to skip the preserve re-read; when omitted, the SDK re-reads and re-sends.
- Explicit activate/deactivate: `toggle_ai_agent_status`.
- After create/update, check the response's `disabled_at` and `active` (`active` is true when `disabled_at` is null). On `get_ai_agent`, `disabledAt` null means active; `behaviors[].active` is not agent enablement. An agent with no active behavior is disabled by the API regardless of enablement flags.

---

## Creation workflow (discover → validate → create → verify)

Choose the part for each step with "Choose the Pipefy part for each step" in `pipefy-process-design`, then apply the consent rule. The user can ask for a specific part when the table points at another one. An example is an AI part for a step that a native rule covers. In that case, recommend the part from the table, and build the part that the user picks.

Create AI only after the user's yes:

- A request for AI or for an agent is a yes.
- A confirmed AI line in a `pipefy-process-design` specification is a yes. Do not ask again.
- Without either yes, ask before you create AI.
- "No AI" removes AI from the recommendations and the build, even after an earlier yes. Each step that loses its AI part uses its recorded alternative.

Never guess event IDs, phase IDs, action types, or field IDs.

### 1 — Get pipe metadata

Call `get_pipe(pipe_id)` and extract:

- `uuid` → use as `repo_uuid` in all AI-agent tools.
- `phases[].id` / `phases[].name` → needed for `move_card` actions.
- Fields via `get_start_form_fields(pipe_id)` and/or `get_phase_fields(phase_id)` → needed for `update_card` actions.

### 2 — Check existing agents

`get_ai_agents(repo_uuid)` to avoid duplicates. To modify an existing agent, use `update_ai_agent` (not create). For full config, use `get_ai_agent(uuid)`.

### 3 — Discover valid trigger events

`get_automation_events(pipe_id)` lists the trigger events. An AI agent behavior accepts every event on that list except `scheduler`. The table maps each trigger that the Pipefy UI shows under "Every time..." to its `event_id`:

| Pipefy UI trigger | `event_id` | `event_params` |
|---|---|---|
| A card enters a phase | `card_moved` | `{"to_phase_id": "<phase_id>"}` |
| A field is updated | `field_updated` | `{"triggerFieldIds": ["<field_id>", ...]}` |
| A card is created | `card_created` | None |
| An alert is triggered | `sla_based` | `{"kindOfSla": "Late"}`, or `Expired`, or `Overdue` |
| A card leaves a phase | `card_left_phase` | `{"fromPhaseId": "<phase_id>"}` |
| An email is received | `card_inbox_received_email` | `{"inPhaseId": "<phase_id>"}` |
| All connected cards are moved to a phase | `all_children_in_phase` | `{"to_phase_id": "<phase_id>"}` |
| An HTTP response is received | `http_response_received` | `{"triggerAutomationId": "<automation_id>"}` |
| An interface button is clicked | `manually_triggered` | None |

For `card_moved` and `field_updated`, you MUST include `event_params`. Omitting it makes the behavior fire on every occurrence.

- `get_automation_events` lists the parameters in snake_case (`from_phase_id`, `kind_of_sla`). The table shows the spelling that the API reads. The toolkit accepts both spellings and sends the API spelling.
- `scheduler` is on the event list, but AI agents do not accept it. `create_ai_agent`, `update_ai_agent`, and `validate_ai_agent_behaviors` reject it before any API call.
- For `all_children_in_phase`, use a phase from the agent's pipe. Read its phases with `get_pipe`. `validate_ai_agent_behaviors` rejects a phase outside that pipe.
- For `http_response_received`, `triggerAutomationId` is the id of the traditional automation that sends the HTTP request. Check the id with `get_automation` first.
- For `manually_triggered`, the "interface button" is a `button`/`automationButton` element on a Pipefy **Interface** page (a portal, outside the pipe) wired to a `triggerAutomation` action naming this behavior's automation id — building it is a separate workflow (see `pipefy-portal-setup`). For a quick test or demo, the closest card-level equivalent is a `field_updated` trigger on a single-option checklist field (e.g. one option named "Run"): checking it fires the behavior without building an Interface.

### 4 — Discover valid action types

`get_automation_actions(pipe_id)`. Known `actionType` values and their required `metadata`:

| Action (`actionType` value) | `metadata` required |
|--------------|---------------------|
| update_card | `pipeId` + `fieldsAttributes` (each entry needs `fieldId` + `inputMode`) |
| move_card | `destinationPhaseId` |
| create_card | `pipeId` + `fieldsAttributes` |
| create_connected_card | `pipeId` + `fieldsAttributes` (requires pipe relation) |
| create_table_record | `tableId` + `fieldsAttributes` (table field IDs; **no** `pipeId`) |
| send_email_template | `emailTemplateId`; optional `allowTemplateModifications` (bool) |
| human_validation | `emails` (recipient list) and `title`. The API accepts either one alone but rejects empty `metadata` |
| mcp_tool | `mcpServerId` + `toolName`; optional `toolInputs`, each with `name` and `source`: `fixed_value` with a `value`, or `card_field` with a `fieldId` |

`fieldId` values for card actions accept slug or numeric `internal_id`; for `create_table_record` they are **table** field IDs (validate with `get_table` / `get_table_record`, not the pipe).

Leave `pipeId` and `tableId` out of an action that does not need them. Never send either as an empty string: Pipefy reads it as an id you cannot access and rejects the agent with "references a pipe or table you do not have access to". Any `pipeId` or `tableId` you send must be in the same organization, and one where the caller can create cards.

### 5 — Build the behavior dict

Name each conditional action in the behavior instruction. State when the agent must run it and when the agent must skip it. Test both outcomes.

```json
{
  "name": "<descriptive name>",
  "event_id": "<from step 3>",
  "event_params": {},
  "actionParams": {
    "aiBehaviorParams": {
      "instruction": "<prompt for the AI when this event fires>",
      "actionsAttributes": [
        { "name": "<action label>", "actionType": "<from step 4>", "metadata": { } }
      ]
    }
  }
}
```

- Each behavior MUST have at least one action in `actionsAttributes`.
- **Maximum 5 behaviors per agent.**

- **`inputMode` is required on every `fieldsAttributes` entry** (omitting it fails model validation). Values: `fill_with_ai` (AI writes the value into an **output** field), `fixed_value` (use the literal `value`), `copy_from` (`value` is a `%{…}` template copying another field).
- **Input** field references (`%{field:<internal_id>}` in the behavior `instruction`, auto-populated into `referencedFieldIds` on create/update) are needed **only when** the AI must read card field values, not for every `fill_with_ai` (e.g. instruction-only, OCR/attachment, or knowledge-base context). When card inputs are needed and omitted, `card.fields` arrives empty at trigger time and the model may hallucinate. A wrong **numeric** input id is accepted silently (validate and create/update) and becomes a dead `referencedFieldId`; a wrong **slug** never resolves and is dropped by the digits-only extractor (unresolved token). Either way `card.fields` stays empty (same hallucination); confirm the id with `get_start_form_fields` / `get_phase_fields`. Dotted connected-pipe refs (`%{field:<parent>.<child>}`) are not forwarded at runtime; to read a connected card field, use a field on the current pipe.
- For `update_card`: set `destinationPhaseId: ""` when not moving the card.

#### Example identifiers (fictional)

Use real values from `get_pipe` / `get_start_form_fields` for your org. Placeholders below match unit-test fixtures in this repo. **The syntax matters** (`pipeId`, `fieldId`, `%{field:<internal_id>}`, `inputMode`) — **the example digits do not**; substitute each pipe's numeric `internal_id` and phase id.

| Role | Example value |
|------|----------------|
| Pipe (numeric repo id) | `987654321` |
| Field `internal_id` | `900000101` |
| Destination phase (`move_card`) | `900000201` |
| Target pipe (`create_card`) | `900000301` |

#### Metadata examples

```json
// update_card — output field fill_with_ai; input fields referenced in instruction
{ "pipeId": "987654321", "destinationPhaseId": "", "fieldsAttributes": [{ "fieldId": "900000101", "inputMode": "fill_with_ai", "value": "" }] }
// companion instruction (aiBehaviorParams.instruction), not metadata:
// "Read %{field:900000102} (title) and %{field:900000103} (description), then fill the category."

// move_card (no pipeId: leave out what an action does not use)
{ "destinationPhaseId": "900000201", "fieldsAttributes": [] }

// create_card
{ "pipeId": "900000301", "fieldsAttributes": [{ "fieldId": "title", "inputMode": "fill_with_ai", "value": "" }] }

// create_table_record (fieldsAttributes are TABLE field IDs; no pipeId)
{ "tableId": "<table_id>", "fieldsAttributes": [{ "fieldId": "<table_field_id>", "inputMode": "fill_with_ai", "value": "" }] }

// send_email_template
{ "emailTemplateId": "<template_id>", "allowTemplateModifications": false }

// human_validation
{ "emails": ["reviewer@example.com"], "title": "Review this card" }

// mcp_tool (mcpServerId is an MCP server registered on the pipe)
{ "mcpServerId": "<mcp_server_id>", "toolName": "<tool_name>", "toolInputs": [{ "name": "query", "source": "fixed_value", "value": "acme" }, { "name": "email", "source": "card_field", "fieldId": "customer_email" }] }
```

### 5b — Optional: capabilities and LLM provider

Inside `actionParams.aiBehaviorParams` a behavior may also carry:

- **`capabilitiesAttributes`** — advanced tools the behavior can use. Each entry is exactly `{ "capabilityType": "<type>", "enabled": true|false }` (both keys required, no extra keys — bare strings or `{ "type": ... }` are rejected).

  | Product name | `capabilityType` |
  |---|---|
  | IDP / Intelligent Document Processing | `advanced_ocr` |
  | Calculations & Analysis | `math_operations` |
  | Web Search | `web_search` |
  | Web Scraping | `web_scraping` |
  | Max effort | `max_effort` |

  `capabilityType` is not checked against a fixed set — any value passes through and the API validates the enum on write, so new capabilities work without a toolkit update. Validation checks **shape only, not entitlement** — a capability may still require organization-level enablement to have any effect, so a green pre-flight does not guarantee the capability is active for the org.
- **`providerId`** / **`systemProviderId`** — pick the behavior's LLM provider. Set **at most one** (a behavior resolves to a single active provider). Discover valid IDs with `get_llm_providers`: each provider carries `type` — use `providerId` for a custom (`byom`) provider and `systemProviderId` for a Pipefy-managed (`system`) one. `get_default_llm_provider` shows what a behavior falls back to when neither is set. IDs are also visible in the organization's AI settings in the Pipefy UI.

  **Bring your own model (custom provider).** First probe `validate_llm_provider_access`: read access does not prove the stronger `manage_ai_providers` permission or eligible plan required for writes. Create a provider with `configuration_file_path` (a local JSON file) and use its `id` as `providerId`. For `update_llm_provider`, send the full configuration: retain `__REDACTED__` placeholders to preserve existing secrets or supply new values to rotate them. Check `get_llm_provider_dependencies` before `delete_llm_provider`; use `set_llm_provider_active_status` for activation. `set_default_llm_provider` takes exactly one of `provider_id` / `system_provider_id`; `reset_default_llm_provider` clears the default.
- **`dataSourceIds`** — knowledge base sources the behavior can draw on. Each ID is a knowledge base item ID from `get_ai_knowledge_bases`. Agents also carry an agent-level `data_source_ids`; the two are unioned. See [Knowledge bases](#knowledge-bases-data-sources) below for the create → attach flow.

```json
{
  "instruction": "Extract totals from the attached invoice.",
  "capabilitiesAttributes": [{ "capabilityType": "advanced_ocr", "enabled": true }],
  "actionsAttributes": [ /* ... */ ]
}
```

### 6 — Validate before every create and update

A rejected update is not rolled back (see [Failure modes](#failure-modes)), so run this before every `create_ai_agent` and `update_ai_agent`, however small the change, and fix every problem it reports first.

`validate_ai_agent_behaviors(pipe_id, behaviors)` checks:
- Output field IDs (`fieldsAttributes[].fieldId`) exist in the pipe
- Phase IDs exist
- Pipe relations exist for `create_connected_card`
- Action types are valid (`KNOWN_AI_ACTION_TYPES`; `create_table_record` `fieldsAttributes` are **table** field IDs, so they are not checked against the pipe and surface a warning to verify with `get_table`; `send_email_template` metadata runs no pipe field-ID checks)
- Behavior structure passes Pydantic validation (including canonical `capabilitiesAttributes` shape and at most one of `providerId` / `systemProviderId`)
- `fieldsAttributes[].fieldId` values (outputs) are checked against start-form and phase fields, accepting both slug `id` and numeric `internal_id`. Instruction `%{field:...}` tokens (inputs) are **not** existence-checked: a missing id/slug still yields `valid: true`. Slug → numeric rewrite happens only on create/update, not here.
- Set `data_source_ids` (agent-level) to also check knowledge base membership: it is unioned with each behavior's `dataSourceIds` and checked against the pipe's knowledge bases. Unknown IDs are **warnings only** (`valid` stays true); if the knowledge base list cannot be read, a single warning is added and the check is skipped.

**`strict_unknown_action_types`** (default `true`): an `actionType` outside `KNOWN_AI_ACTION_TYPES` is reported in `problems` (blocking). Set `false` to demote unknown action types to `warnings` only, so `valid` stays true.

### 7 — Create the agent

`create_ai_agent` with `name`, `repo_uuid`, `instruction`, and `behaviors`. One-call creation is preferred — avoids partial agent shells. Agents are **active by default**; set `disabled_at` to the current time, as an ISO-8601 UTC timestamp, to start disabled (see [Active lifecycle](#active-lifecycle)).

On create/update, slug `fieldId` values are resolved to numeric `internal_id`, `%{field:<slug>}` is rewritten to `%{field:<internal_id>}`, and `referencedFieldIds` is auto-populated when applicable. The SDK injects action `referenceId` values and `%{action:<uuid>}` placeholders for every surface; do not generate them yourself.

### 8 — Handle responses

- **Success with `agent_uuid`** → check `disabled_at` and `active` on the write response to verify agent enablement.
- **Partial failure (behaviors rejected)** → the SDK raises `AiAgentConfigureError`; use its `.agent_uuid` to recover the existing shell. The MCP response carries `agent_uuid`. Call `update_ai_agent` with the **full required payload**: `uuid`, `repo_uuid` (same pipe UUID used on create), `name`, `instruction`, and complete `behaviors` (full-replace, not patch). Do NOT create a second agent. The create shell is often disabled; update preserves that state — call `toggle_ai_agent_status` after a successful recovery update if you need the agent active.
- **Failure without UUID** → validation or API error. Trust the hint text in the enriched error.

### 9 — Verify

`get_ai_agent(uuid)` to confirm behaviors and enablement (`disabledAt` null means active). Do not treat `behaviors[].active` as agent enablement; never assume inactive without confirmation.

Before removing acceptance cards, call `get_ai_agent_logs(repo_uuid=<pipe_uuid>)` without a `status` filter. Read `aiAgentLogsByRepo.nodes` from the returned data. Match `cardId`, `agentUuid`, and `createdAt` to the test execution. If `pageInfo.hasNextPage` is true, pass `pageInfo.endCursor` as `after` and continue.

Wait until the matching execution has terminal `status`: `success` or `failed`. Keep acceptance cards while execution is `processing`. Then call `get_card` with `include_fields=true`. Compare the stored output fields and phase with each expected outcome. An absent or empty required output does not pass acceptance. Missing or `processing` executions remain pending. A `failed` execution or an incorrect result does not pass acceptance.

---

## Knowledge bases (data sources)

Knowledge bases are pipe-scoped data sources an agent draws on. Attach one by putting its ID in a behavior's `dataSourceIds` (or the agent-level `data_source_ids`). All knowledge base operations are scoped by the pipe **UUID** (`pipe_uuid`), not the numeric pipe ID — `get_pipe` returns the `uuid`.

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_ai_knowledge_bases` | Yes | List every item on a pipe (plain texts, documents, data lookups); each has an `id` for `dataSourceIds` and a `type` (`knowledge_base_plain_texts`, `knowledge_base_documents`, or `data_lookups`). |
| `get_ai_knowledge_base_plain_text` | Yes | Fetch one plain text with its content. |
| `create_ai_knowledge_base_plain_text` | No | Create a plain text (`name` 1-80, `content` 1-3500, `description` 1-300, all required). |
| `update_ai_knowledge_base_plain_text` | No | Partial update; send at least one of name/content/description. |
| `delete_ai_knowledge_base_plain_text` | No | **Destructive; review and approve first.** |
| `get_ai_knowledge_base_document` | Yes | Fetch one document's metadata (`content` is the stored URL, not text). |
| `create_ai_knowledge_base_document` | No | Upload a PDF (`name` 1-80, `description` 1-300, `file_path`). `.pdf` + 20 MiB cap; indexing is asynchronous. |
| `update_ai_knowledge_base_document` | No | Metadata-only update (name/description); no file replacement. |
| `delete_ai_knowledge_base_document` | No | **Destructive; review and approve first.** |
| `get_ai_knowledge_base_data_lookup` | Yes | Fetch one data lookup; the payload never includes `conditions` — keep the definition client-side. |
| `create_ai_knowledge_base_data_lookup` | No | Create a data lookup (`name` 1-80, `description` 1-300, `source_repo_id` numeric pipe ID, `output_fields` 1-30, `conditions`, all required). |
| `update_ai_knowledge_base_data_lookup` | No | Full replacement: resend `source_repo_id`/`output_fields`/`conditions` every call; omitted `search_query` clears it; only name/description are partial. |
| `delete_ai_knowledge_base_data_lookup` | No | **Destructive; review and approve first.** |
| `validate_knowledge_base_access` | Yes | Probe read access before writes. |

### Flow: validate-access → create plain text → attach

1. **Probe access** — `validate_knowledge_base_access(pipe_uuid)`. A green result proves read access only (`read_ai_agents`), never the `manage_ai_agents` entitlement writes need.
2. **Create the source** — `create_ai_knowledge_base_plain_text(pipe_uuid, name, content, description)`. Limits fail fast client-side: `name` 1-80 chars, `content` 1-3500 chars, `description` 1-300 chars (all required). Keep the returned `id`.
3. **Attach** — add that `id` to a behavior's `dataSourceIds` (or the agent-level `data_source_ids`) when calling `create_ai_agent` / `update_ai_agent`. Validate first with `validate_ai_agent_behaviors(pipe_id, behaviors, data_source_ids=[...])` — unknown IDs surface as warnings.

For a **PDF document**, use `create_ai_knowledge_base_document` with `pipe_uuid`, `name`, `description`, and `file_path` at step 2. Only `.pdf` is accepted, with a 20 MiB cap. Indexing is asynchronous, so the document may not be searchable immediately. Keep the returned `id` and attach it.

### Data lookups: create with an AI-filled condition → attach → update (full replacement)

A **data lookup** lets the agent search cards in a source pipe by conditions and return selected field values. Same flow as above at step 2, with three rules of its own:

1. **Create** — `create_ai_knowledge_base_data_lookup(pipe_uuid, name, description, source_repo_id, output_fields, conditions)`. `source_repo_id` is the **numeric** ID of the source pipe (a UUID is accepted by the API but the lookup then breaks when the agent runs it). `output_fields` takes 1-30 field IDs (field slugs plus static fields like `id`, `title`, `created_at`). Each condition needs `field` + `operator` (opaque backend string, e.g. `"eq"`, `"contains"`) and is either **static** (string `value` required) or **AI-filled** — the AI asks the user for the value at runtime:

   ```json
   [{"field": "customer_email", "operator": "eq", "usingFillWithAi": true,
     "inputName": "Customer email", "inputType": "text",
     "inputDescription": "The customer's email address"}]
   ```

2. **Attach** — keep the returned `id` and add it to `dataSourceIds`, exactly as for the other kinds. **Also keep the definition you sent**: reads never return `conditions`, so your copy is the only complete record of the lookup.
3. **Update replaces everything** — `update_ai_knowledge_base_data_lookup` requires `source_repo_id`, `output_fields`, and `conditions` on every call (the complete condition set, not a delta), and omitting `search_query` clears it. Only `name`/`description` keep their stored values when omitted.

---

## Token normalization & slug resolution

Instructions accept five token aliases — all normalize to canonical `%{field:<internal_id>}`:

| Form | Behavior |
|------|----------|
| `%{<internal_id>}` | Canonical short form. |
| `{<internal_id>}` | Bare; auto-prefixed with `%`. |
| `{field:<internal_id>}` | Bare-with-prefix; auto-`%`. |
| `{field:<slug>}` | Bare slug; resolved to numeric when behavior action carries `pipeId`. |
| `%{field:<internal_id>}` | Canonical full form. |

`%{field:<slug>}` is rewritten to `%{field:<internal_id>}` when an action in the behavior supplies `pipeId`. If the Pipefy UI shows plain text instead of chips in token slots, the payload probably still has non-canonical tokens.

---

## Template params / placeholders

Per behavior you can give `template_params` (or `placeholders`) with `str → str` values and use `{{name}}` in any string (instruction, metadata IDs, etc.). Optionally set `instruction_template` instead of `aiBehaviorParams.instruction` — the final instruction is interpolated and written before the API call (by the MCP tools, the CLI, and the SDK's `CreateAiAgentInput` / `UpdateAiAgentInput`). These keys are stripped during validation.

```json
{
  "name": "Classify card",
  "event_id": "card_created",
  "instruction_template": "Read {{field_ref}} and classify the card.",
  "template_params": { "field_ref": "%{field:900000101}" },
  "actionParams": {
    "aiBehaviorParams": {
      "actionsAttributes": [
        {
          "name": "Fill classification",
          "actionType": "update_card",
          "metadata": { "pipeId": "{{pipe}}", "fieldsAttributes": [{ "fieldId": "{{class_field}}", "inputMode": "fill_with_ai", "value": "" }] }
        }
      ]
    }
  },
  "placeholders": { "pipe": "987654321", "class_field": "900000101" }
}
```

`template_params` and `placeholders` merge (placeholders wins on conflict).

---

## Naming differences (UI vs API)

| Pipefy UI | API / Tool field |
|-----------|------------------|
| Description (agent creation step 1) | `instruction` (agent-level) |
| Instruction / Prompt (per behavior) | `actionParams.aiBehaviorParams.instruction` |
| Pipe UUID | `repo_uuid` (from `get_pipe().uuid`, NOT the numeric `id`) |

---

## Success criteria

- Agent enablement matches the intended state: `get_ai_agent.disabledAt` is null when active; `behaviors[].active` does not establish agent enablement.
- `validate_ai_agent_behaviors` reports no errors before each create and update.
- Agent appears in the Pipefy UI under the pipe's AI settings.

## Failure modes

- **`update_ai_agent` is full-replace, not patch.** Read the agent with `get_ai_agent`, change what you need, and send the complete behaviors list back. A behavior you leave out is deleted. You can send the read behaviors back as they are; the ids and `%{action:…}` lines they carry are replaced on save. Update never reactivates a disabled agent; use `toggle_ai_agent_status` for that.
- **A rejected update is not rolled back.** Pipefy applies the name and instruction and removes the current behaviors before it saves the new list. When it then rejects the list (`RECORD_NOT_SAVED`), the agent is left with no behaviors, or only part of the new list, and stays enabled. Before `update_ai_agent`, keep the `get_ai_agent` result and run `validate_ai_agent_behaviors`, which checks each `event_id` against `get_automation_events` — warning you when those events cannot be loaded, so an unverified `event_id` never reads as a clean result — and validates the `human_validation`/`mcp_tool` action metadata. After a failure, call `get_ai_agent` to see what is left, fix the payload, and send the full list again. The same holds when the update fails with "references a pipe or table you do not have access to": the behaviors are already saved when that error returns.
- **`RECORD_NOT_SAVED` does not name the cause.** `validate_ai_agent_behaviors` now names several of them — an unknown `event_id` (when the pipe's automation events load), and a `human_validation` or `mcp_tool` action with missing metadata — so run it first. The same message still covers payload errors the pre-flight cannot see, so rule those named causes out before you conclude the pipe does not support AI agent behaviors.
- **Partial-failure recovery.** If `create_ai_agent` returns a UUID but reports failure, call `update_ai_agent(uuid, repo_uuid, name, instruction, behaviors)` — all five are required. Reuse the create `repo_uuid`; send the full behaviors list. Do NOT create a second agent. Update preserves disabled state; use `toggle_ai_agent_status` to change enablement.
- **Cross-pipe `PERMISSION_DENIED`.** Behaviors with `create_connected_card` or cross-pipe `create_card` require the service account to be a member of **both** source and destination pipes. When it is not, the API returns a bare `PERMISSION_DENIED`. Recovery: `get_pipe_members` + `invite_members` on the destination pipe.
- **Phase transition rule on `move_card`.** Destination must be reachable from the source phase (`cards_can_be_moved_to_phases`). Both `validate_ai_agent_behaviors` and `create_ai_agent` / `update_ai_agent` enrich this error with `valid_destinations` and a hint on how phases get connected and where to change the connections.
- **Maximum 5 behaviors per agent.** Adding a 6th rejects the whole save.
- **Ghost agents.** An agent listed by `get_ai_agents` may return "Agent not found" on `get_ai_agent` — a Pipefy backend artifact, persists across sessions, do not retry.
- **GraphQL error hints.** When a dedicated read tool returns permission-denied or not-found, the `error.message` may cite concrete tools (e.g. `"Use 'get_ai_agents' to list agents..."`). Trust the hint; don't improvise alternative flows.
- **Validation rejections.** Common issues: invalid `trigger_event`, prompt too long, missing required action config. Read the `errors` field per behavior.

## See also

- `pipefy-automations` — traditional automations and AI automations (different from AI agents).
- `pipefy-observability` — agent execution logs and credit usage.
- [docs/mcp/tools/identifiers.md#ai-agents-and-knowledge-bases](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/identifiers.md#ai-agents-and-knowledge-bases) — canonical map of which tool/argument expects slug vs `internal_id` vs uuid vs numeric id (AI agents scope by `repo_uuid` = pipe UUID).
