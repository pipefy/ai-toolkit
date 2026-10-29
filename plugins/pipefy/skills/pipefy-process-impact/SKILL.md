---
name: pipefy-process-impact
description: >
  Use this skill when the user asks whether an automation or AI agent would
  pay off, where to start automating a process, how much time a change gives
  back, or for a short internal justification. Answers from the conversation
  first; when the user names a pipe, reads what already runs there before
  pointing at a step. Not for diagnosing a whole pipe
  (pipefy-process-intelligence), designing one (pipefy-process-design),
  building (pipefy-building), or what a change breaks elsewhere.
tags: [pipefy, process-impact, impact, automation]
---

# Process impact

Help the user find the one step in their process where an automation or an AI agent returns the most time, and show the arithmetic. One hop, one formula, one question per turn. The next hop comes after they have the first number.

Read the [MCP reference](references/mcp.md) or [CLI reference](references/cli.md) only when the user names a pipe, and only for the reads listed there.

## When to use

- "Is it worth automating X?" / "Where do I start?" / "What is the ROI?" / "How much time does this give back?"
- "Help me justify this internally."
- The user wants more than the `Impact:` line that `pipefy-process-design` or `pipefy-process-intelligence` already emitted.

Not for designing a process (`pipefy-process-design`), a full pipe diagnosis or implementation (`pipefy-process-intelligence`), building the step (`pipefy-building`, then the domain skill), or finding what a change breaks elsewhere.

## How to answer

1. **Pick the hop.** From the conversation, name the one manual, repetitive step with the best return: a move someone does by hand, a triage, a copy-paste, a chase. With several candidates, take the one with the most cases per week. Do not walk the whole process.
2. **Check coverage when a pipe is named.** Run the reads in the reference: `get_pipe`, `get_automations`, `get_ai_agents`, then `get_ai_agent` for each active agent. If an active automation or agent already does the hop, say so, size that coverage, and move to the next uncovered hop, restating what the agent or rule already does there. Do not propose a second one. With no pipe in view, say coverage was not checked instead of claiming nothing covers the hop. `cards_count` is what sits in a phase now, not volume or duration, and `get_cards` selects no dates; when the answer needs time, use the timed card read under Measuring.
3. **Show the arithmetic**, with the user's numbers or the gaps named:

```text
hours returned per week ≈ minutes per case × cases per week / 60
cost avoided per week ≈ hours returned per week × hourly cost   (only if the user gave an hourly cost)
```

   Never fill a gap yourself. Lead time and time per phase come from the timed card read, weekly volume from the user or a pipe report export (see Measuring), never from `cards_count` or an undated sample.
4. **Name the cheapest step that removes the hop.** A traditional automation when the decision reads from fields ("if value > X, move"). An AI agent or AI automation only when the hop needs reading free text, documents, or a conversation. iPaaS when the work lives in another app. One sentence on which and why. Do not stack rule and AI as "do both now"; mention the AI step as optional when a rule leaves part of the hop manual.
5. **End with one thing**: the missing numbers in one short question, or the next step (the next hop, a measured export, or building it with the domain skill).

## Output

In the user's language, four lines, under 150 words unless they asked for a written case:

```text
Where it pays: [hop], [what covers it today, if anything]
Arithmetic: [formula with numbers or named gaps] = [hours per week, or the gap]
Step: [automation | AI agent | iPaaS], [one sentence on why this one]
Next: [one question, or one offer]
```

For a written case, expand each line into a short paragraph and add an "Assumptions" line. Money only with an hourly cost. Lead time only from the timed card read, an export, or a cycle the user stated.

## Rules

- Report time returned to the team on repetitive hops. Asked how many people the change removes, answer in hours and say that decision is theirs.
- Do not recommend deleting a pipe, cutting seats or credits, or moving work off Pipefy. A quiet pipe is a process with no trigger or a duplicate: ask which, then cover its hops. Delete only when the user asks for that pipe by name, and then move the work into the pipe that remains.
- Rule before AI. Existing coverage is value already delivered: size it, do not replace it. Credits an active agent spends are the cost of work it already does, not a line to cut.
- `get_ai_agents` takes the pipe `uuid` from `get_pipe`, not the numeric id; a numeric id returns a permission error. With the uuid and still a permission error, say agent coverage is unknown and do not call the hop manual on that basis.

## Measuring

Lead time, age, and time per phase come from a timed card read: one `execute_graphql` query on the pipe's cards that selects `createdAt`, `finished_at`, `started_current_phase_at`, `current_phase_age`, and `phases_history` (`firstTimeIn`, `lastTimeOut`, `duration` in seconds per phase). The document is in the reference. It is a read, runs with no confirmation, and returns 25 cards per page (up to 50); say how many cards the numbers come from, and page with `after` when the pipe has more. Lead time is `finished_at` minus `createdAt` on done cards; time in a phase is the `duration` of its `phases_history` entry.

Weekly volume for a whole pipe comes from the user or from a pipe report export (`created_at` per card), which is the better path when the pipe has more cards than a few pages. The export works on an existing report (`get_pipe_reports`); when the pipe has none, `create_pipe_report` is a write, so ask first. Pass the date columns by `name` from `get_pipe_report_columns`; `pipefy-reports` has the export and polling steps. The export ends in an XLSX link, so use it for volume, not for a number the user wants in the chat.

## Tools

| Operation | Read-only | Purpose |
|-----------|-----------|---------|
| `search_pipes` | Yes | Pipe id when only the name is known |
| `get_pipe` | Yes | Phases, `cards_count`, and the pipe `uuid` |
| `get_automations` | Yes | Hops an active rule already covers (`active` and `actionEnabled`) |
| `get_ai_agents` | Yes | Agents on the pipe; active when `disabledAt` is null |
| `get_ai_agent` | Yes | Behaviors with `active: true` and the phase each acts on |
| `execute_graphql` | Yes, for a query | Timed card read: the dates and time per phase that `get_cards` leaves out |
| `get_pipe_reports` | Yes | Existing reports to export for whole-pipe volume |
| `get_pipe_report_columns` | Yes | Column `name` values for the export |
| `export_pipe_report` | No | Start the export; changes no card |
| `get_pipe_report_export` | Yes | Poll until the file is ready |
| `create_pipe_report` | No | Only when the pipe has no report and the user agreed |

## See also

- `pipefy-process-design`: new process architecture (emits an Impact line).
- `pipefy-process-intelligence`: diagnose and improve a pipe (emits an Impact line).
- `pipefy-building`: route the chosen step to a domain skill.
- `pipefy-automations`, `pipefy-ai-agents`, `pipefy-ipaas`: build the step.
- `pipefy-reports`: pipe report exports for lead time and weekly volume.
