---
name: pipefy-building
description: >
  Thin router for Pipefy build and configure asks: map user intent to the
  correct domain skill (pipes, automations, AI agents, iPaaS, portals, etc.).
  Use when the user wants to create, build, configure, or integrate something
  in Pipefy and you need to know which skill to open. Do not use this skill
  as a delivery playbook — if the user already has a building skill or a
  detailed build prompt, follow that for how to build; use this skill only
  for which Pipefy domain skill to read.
tags: [pipefy, building, routing, orchestration]
---

# Pipefy Building (router)

Maps **what the user wants** to **which domain skill to read**. It does not teach create/update workflows — open the linked skill for that.

If the user already has a building skill or a detailed build prompt/spec, use that for *how to build*; use this skill for *which Pipefy skill to load*.

---

## When the user wants X → read skill Y

| User intent (examples) | Read |
|------------------------|------|
| Design / architecture / "help me structure this process" | `pipefy-process-design` (consulting only) |
| Pipes, phases, fields, labels, cards, field conditions | `pipefy-pipes-and-cards` |
| Traditional or AI automations (if/then, prompt-driven rules) | `pipefy-automations` |
| Conversational AI agents and behaviors | `pipefy-ai-agents` |
| External integration / integrate with Slack, Gmail, Sheets, or another app | `pipefy-ipaas` |
| Portals, pages, elements, sub-portals | `pipefy-portal-setup` |
| Members, email templates, inbox email, webhooks | `pipefy-members-email-webhooks` |
| Database tables and records | `pipefy-database-tables` |
| Pipe/card relations | `pipefy-relations` |
| Reports and exports | `pipefy-reports` |
| Logs, usage, credits, job exports | `pipefy-observability` |
| First-time toolkit setup | `pipefy-toolkit-setup` |

**Do not re-teach domain workflows here — open the linked skill.**

---

## Product limits live in domain skills

Hard stops and quirks (phase connections UI-only, email template create/edit UI-only, incompatible automation event×action pairs, no automation action applies a label, verify-after-write, AI consent) are documented in the domain skills above; follow those contracts after routing.

## See also

- `pipefy-process-design` — consulting when the ask is design, not build.
- [skills/README.md](https://github.com/pipefy/ai-toolkit/blob/main/skills/README.md) — full catalog.
