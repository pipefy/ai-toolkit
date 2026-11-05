---
name: pipefy-building
description: >
  Routes a Pipefy build or configure request to the skill to read. Covers
  three kinds of request. One part, such as a field, a phase, an automation,
  an agent or a portal page, goes to its domain skill. A whole process goes to
  pipefy-process-design while a business decision is open. Otherwise it goes
  to a skill in the catalog that builds a whole process from a specification,
  or to the domain skills in dependency order. A build method that the user
  supplies decides how to build. Use it whenever the user wants to create,
  build, configure, connect or integrate something in Pipefy and the right
  skill is not open yet. Not a delivery playbook: it does not say how to build
  a part. Not for design advice (pipefy-process-design), pipe diagnosis
  (pipefy-process-intelligence) or the return of a change
  (pipefy-process-impact), except to send the request there.
tags: [pipefy, building, routing, orchestration]
---

# Route a Pipefy build request

This skill tells you which Pipefy skill to read for a build or configure request. The domain skill that you open says how to build the part.

Do not use this skill as a delivery playbook. When the user already has a building skill or a detailed build prompt, follow it for how to build. Use this skill only to know which Pipefy domain skill to read.

## Precedence

- A build method that the user supplies decides how to build. So does a skill in your catalog that builds a whole process from a specification.
- When a request to build a whole process has an open business decision, read `pipefy-process-design` first. Examples: who approves, which value routes a case, what happens on a rejection. A verb such as "create" does not remove the open decision.

## Find the kind of request

1. **One part.** The user asks for one part, such as a field, a phase, an automation, an agent, or a portal page. Read the domain skill for that part in the [routing table](#routing-table).
2. **A whole process.** The user asks for a process with many parts, with or without a specification.
   - When a business decision that changes the build is open, read `pipefy-process-design` first.
   - When a skill in your catalog builds a whole process from a specification, read that skill. Give it the specification.
   - Otherwise, use the order in the "Whole-process builds" section below.
3. **The user's own method.** The user supplies a build method or a detailed build prompt. Follow that method. Use this skill only to find the domain skill for each part.

Some requests use a build verb but ask for something else:

- The user wants advice and no change, such as "only tell me how you would do it". Read `pipefy-process-design`. Write nothing.
- The user wants to diagnose or improve a pipe that exists. Read `pipefy-process-intelligence`.
- The user asks if a change pays off, or wants a short justification. Read `pipefy-process-impact`.

## Routing table

| User intent (examples) | Read |
|------------------------|------|
| Design a process, "help me structure this flow", or check a specification | `pipefy-process-design` (advice, writes nothing) |
| Build a whole process with an open business decision | `pipefy-process-design` first, then this skill with the specification |
| Advice and no change | `pipefy-process-design` |
| Diagnose or improve a pipe that exists | `pipefy-process-intelligence` |
| Impact, ROI, "is this change worth it?", internal justification | `pipefy-process-impact` (advice, do not build from there) |
| Pipes, phases, fields, labels, cards, field conditions | `pipefy-pipes-and-cards` |
| Traditional or AI automations (if/then rules, prompt-driven rules) | `pipefy-automations` |
| Conversational AI agents, their behaviors and knowledge bases | `pipefy-ai-agents` |
| External integration with Slack, Gmail, Sheets, or another app | `pipefy-ipaas` |
| Main portal: its grid-layout pages, elements, sub-portals | `pipefy-portal-setup` |
| A standalone page or dashboard built as one HTML document (an HTML interface). When it is not clear if the user means this or a portal page, ask. | `pipefy-html-interfaces` |
| Members, email templates, inbox email, webhooks | `pipefy-members-email-webhooks` |
| Database tables, records, table fields | `pipefy-database-tables` |
| Pipe, table, or card relations | `pipefy-relations` |
| Upload a file to a card or a table record | `pipefy-attachments` |
| Reports and exports | `pipefy-reports` |
| An automation did not run, or its logs are empty. Do not call it an outage before the checks. | `pipefy-automations` (the "did not fire" checks), then `pipefy-observability` |
| Logs, usage, credits, job exports | `pipefy-observability` |
| First-time toolkit setup | `pipefy-toolkit-setup` |
| A dedicated operation fails or does not exist | `pipefy-introspection` (first fallback) |
| The introspection skill did not solve the problem | `pipefy-api-fallback` (last fallback) |

## Whole-process builds

Use this order when no catalog skill builds a whole process and the user supplied no build method. When a part needs another part's ID, create that other part first. Read each domain skill when you get to its part.

1. Pipe and phases.
2. Fields and field conditions.
3. Tables and relations.
4. Automations and integrations.
5. AI agents.
6. Portal pages.

- Activate the automations and AI agents of a new process, unless the user asks to keep them inactive (`build inactive`). Create a rule (an automation or an AI agent) inactive when its pipe already has cards that it can match. Do the same for a rule on a time limit or a schedule in a pipe with cards. Read that rule again, then activate it. Keep a rule inactive while it reads an unconfirmed assumption or needs a missing phase connection. Publish a sub-portal or an integration flow only when the user asks.
- After each write, read the part again and compare it with the request.
- When a part that matches the request exists, ask the user before you use it again.
- Create an AI automation or an AI agent only after the user says yes to AI. A confirmed AI line in the process specification is that yes, so do not ask again.
- End with each part and its state, the manual steps, the inactive parts, and one "Next step".

## Product limits live in domain skills

The domain skills hold the hard stops and quirks. Examples: phase connections, email templates that only the UI can create, and automation events and actions that do not work together. Others: no automation action can apply a label, and the AI consent rule. Follow those rules after you route.

## See also

- `pipefy-process-design` for design advice before a build.
- `pipefy-process-impact` for impact, ROI, or a justification.
- `pipefy-process-intelligence` for the diagnosis of a pipe that exists.
- [plugins/pipefy/README.md](https://github.com/pipefy/ai-toolkit/blob/main/plugins/pipefy/README.md) for the full catalog.
