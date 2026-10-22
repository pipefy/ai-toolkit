---
name: pipefy-process-intelligence
description: >
  Use this skill when the user wants to analyze an existing pipe for
  improvement opportunities — automation gaps, manual bottlenecks,
  missing AI agents, field conditions, or adjacent processes. Acts as
  a process analyst: investigates, diagnoses, and improves the pipe
  in progressive rounds — each round delivers visible results.
tags: [pipefy, process-intelligence, optimization, automation, analysis]
---

# Process Intelligence

Read the [MCP reference](references/mcp.md) or [CLI reference](references/cli.md) for the surface you are using. Load only the relevant reference.

Analyze existing pipes for improvement opportunities and implement them progressively. **Investigate immediately. Diagnose with data. Improve progressively.**

---

## When to use

The user asks to analyze or improve an existing process:
- "Analyze my pipe"
- "How can I improve this process?"
- "Is this pipe optimized?"
- "Where are the bottlenecks?"

**Not for:** designing a new process from scratch → use `pipefy-process-design`. Justifying a change with numbers, without implementing it → use `pipefy-process-impact`.

---

## Prerequisites

- Pipe ID or name is known (or searchable via `search_pipes`).
- Read access to the pipe's cards and phase data.

---

## Steps — investigation (Round 1)

1. **Get pipe structure:**

   Operation: `get_pipe pipe_id=<id>`

   Capture: phases, field count per phase, automation count.

2. **Sample recent cards** (last 30–50):

   Operation: `get_cards pipe_id=<id> first=50 include_fields=true`

   Look for: cards piling up in early phases, phases with 0 cards, fields left empty. `get_cards` selects no creation, update, or phase timestamps; the timed card read under the diagnosis framework does.

3. **Check automations:**

   Operation: `get_automations pipe_id=<id>`

   Look for: phases with no automations (manual handoffs), repeated manual steps.

4. **Check AI configuration:**

   Operation: `get_ai_agents repo_uuid=<PIPE_UUID>`

   For each active agent (`disabledAt` is null), read its behaviors to see which phases it already acts on:

   Operation: `get_ai_agent uuid=<AGENT_UUID>`

   Look for: no AI agents despite manual categorization or triage patterns, and hops an active behavior already covers (do not report those as manual).

---

## Diagnosis framework

Time-based signals need dates that `get_pipe` and `get_cards` do not return. Per-card signals (stuck in a phase for more than 7 days, no update in weeks) come from a timed card read: one `execute_graphql` query on the pipe's cards selecting `updated_at`, `current_phase_age`, and `phases_history` (`firstTimeIn`, `lastTimeOut`, `duration` in seconds per phase); the document is in the reference. It is a read with no confirmation, 25 cards per page (up to 50), so say how many cards the numbers come from.

Whole-pipe signals (a phase with no card in 90 days, cards leaving a phase per week) need every card, because the `cards` query has no date filter and no documented order, so one page proves nothing about the cards it left out. Page the timed read until `hasNextPage` is false, or use a pipe report export (`pipefy-reports`) with `start_at_phase_<n>` and `end_at_phase_<n>` (`<n>` is a report index, not the phase id); the export needs an existing report (`get_pipe_reports`), and creating one with `create_pipe_report` is a write, so ask first. Without full coverage, say the signal was not checked; do not call a phase dead from a sample, and do not infer time from `cards_count`.

| Signal | Opportunity |
|--------|-------------|
| Cards stuck in a phase for >7 days | Add due date field + overdue automation |
| Phase transitions always done by same person | Automate the transition condition |
| Fields never filled in certain phases | Remove or make optional |
| Same comment posted repeatedly | AI agent to auto-post based on trigger |
| No automation between intake and first action | Add "notify assignee" automation on card creation |
| Large field count on start form | Move optional fields to later phases |
| Phases with 0 cards over 90 days (whole pipe, not a sample) | Merge into a neighboring phase, or replace the hop with an automation or AI agent. Do not treat an empty phase as a reason to delete the pipe. |

---

## Steps — improvement (Round 2+)

Each round focuses on 1–2 improvements; report results before proceeding.

**Example: automate a repeated manual step**

1. Identify the manual step and its trigger.
2. Call `get_automation_events` and `get_automation_actions` for the pipe; select a supported event and action.
3. Create the automation:

   Operation: `create_automation pipe_id=<id> name="Automate manual step" trigger_id=<EVENT_ID> action_id=<ACTION_ID> active=false`

4. Verify the rule before activating it, then report the actual event and action used. If the desired event or action is unavailable, report the limitation instead of guessing an ID.

**Example: add a field condition**

1. Identify a field that should only show when another field has a specific value.
2. Read the field-condition input schema, then create the condition with its required `name`, `condition` dict, and `actions` list:

   Operation: `create_field_condition phase_id=<PHASE_ID> name="Show follow-up" condition=<CONDITION_DICT> actions=<ACTION_DICTS>`

---

## Output format per round

```
## Analysis — [Pipe Name]

### Findings
- [Finding 1]: [evidence from tool calls]
- [Finding 2]: ...

### Implemented this round
- [Change 1]: [tool called + result]

### Impact
[One line: minimum step done or proposed, time it returns to the team (formula with the missing numbers named), and the extra lift of the next step, or "next step does not close". Lead time only if this round already has dates.]

### Next round (if approved)
- [Opportunity]: [proposed action]
```

Keep Impact to one line. Do not invent volume, hourly cost, or lead time; name every missing number and ask for all of them in one question. For a fuller justification, read `pipefy-process-impact`. Do not recommend deleting a pipe.

---

## Success criteria

- Each round produces a concrete visible change (new automation, field condition, phase cleanup).
- The affected phase moves more cards: compare cards leaving it per week (`lastTimeOut` in the timed card read, or `end_at_phase_<n>` in a pipe report export) before and after the change, or ask the user.
- No improvement causes a regression (verify with `get_pipe` and `get_cards` after each round).

## Failure modes

- **`get_cards` returns empty:** the pipe may have no cards yet. Analyze structure only, and recommend standing up intake (start form, portal, or an automation that creates cards) rather than removing the pipe.
- **`create_automation` fails with unknown event:** use `get_automation_events` to list valid triggers.
- **User pushes back on automation:** explain what the automation does in plain language before creating.

## See also

- `pipefy-automations` — detailed automation creation guide.
- `pipefy-ai-agents` — add conversational agents for user-facing automation.
- `pipefy-observability` — check credit and execution data to quantify improvement impact.
- `pipefy-process-impact` for a fuller justification; this skill only emits the Impact line per round.
