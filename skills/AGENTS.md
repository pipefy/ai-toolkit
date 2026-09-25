# Skills — Authoring Guide

This document defines how to author, name, and maintain skills in the `ai-toolkit` monorepo.

---

## What is a skill?

A skill is a directory with a `SKILL.md` entrypoint describing a Pipefy workflow. Its body contains domain rules, payload shapes, steps, and failure modes shared by MCP, CLI, and SDK consumers. Surface-specific instructions live in sibling reference files, loaded only by clients using that surface.

---

## Directory structure

```
skills/
  <domain>/
    <skill-name>/
      SKILL.md          ← the skill file
      references/       ← when the workflow has surface-specific instructions
        mcp.md          ← MCP controls, profiles, response envelopes
        cli.md          ← shipped commands and flags
      COMPLIANCE.md     ← required for regulated-domain / blueprint skills
  AGENTS.md             ← this file
  README.md             ← catalog index
```

The copyable starter lives at [`.github/skill-template/pipefy-skill-template/`](../.github/skill-template/pipefy-skill-template/), outside this catalog.

**Domain folders** match the MCP tool surface:
`pipes-and-cards`, `database-tables`, `relations`, `reports`, `automations`, `ipaas`, `ai-agents`, `observability`, `members-email-webhooks`, `portal-setup`, `attachments`, `introspection`, `building`, `process-design`, `process-intelligence`, `api-troubleshoot`, `onboarding`

Regulated domains (`legal`, `human-resources`, `finance`, `compliance`, or any skill involving decisions about natural persons) require substantive Legal review and a filled `COMPLIANCE.md` (start from [`docs/compliance/COMPLIANCE.template.md`](../docs/compliance/COMPLIANCE.template.md)). See [`CONTRIBUTING.md`](../CONTRIBUTING.md).

To start a new skill, copy [`.github/skill-template/pipefy-skill-template/`](../.github/skill-template/pipefy-skill-template/) (see [`.github/skill-template/README.md`](../.github/skill-template/README.md)). The inline skeleton below matches that file.

---

## SKILL.md template

```markdown
---
name: pipefy-<domain>-<action>   # kebab-case, unique
description: >
  One-line summary used by agents to choose this skill.
  Be specific about when to use vs not use.
tags: [pipefy, <domain>, ...]
---

# Title

Short intro (1-2 sentences). State the tool count when relevant.

MCP clients: read [references/mcp.md](references/mcp.md).
CLI users: read [references/cli.md](references/cli.md).

---

## When to use

The user intent that triggers this skill (examples). State when NOT to use this skill.

## Prerequisites

What must be true before the agent can execute (IDs, access, config).

## Tools needed

| Operation | Read-only | Purpose |
|-----------|-----------|---------|
| `tool_name` | Yes/No | Domain outcome |

## Steps

1. **Step name** — description.

   Operation arguments (adapt to the active surface):
   ```
   tool_name arg1=value1 arg2=value2
   ```

2. **Next step** — ...

## Success criteria

How the agent / human knows the workflow completed correctly.

## Failure modes

Common errors and how to recover.
```

---

## Naming conventions

- **Skill names:** kebab-case, descriptive, start with `pipefy-` (`pipefy-pipes-and-cards`, `pipefy-process-design`).
- **Domain folders:** kebab-case, plural where natural (`pipes-and-cards`, `automations`).
- **Stable IDs:** once a skill is published, renames require a CHANGELOG note so agent prompts using old names still resolve.

---

## Frontmatter rules

All fields are **required** unless noted:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Must match the directory name exactly. |
| `description` | Yes | One-line summary; used by agents to select this skill. |
| `tags` | No | Optional list of relevant keywords. |

CI (`skills-lint.yml`) validates these on every PR.

---

## Body style

- **Action-first headlines.** "Create a pipe" not "Pipe creation."
- **Surface-neutral body.** Name operations by their shared tool names. Keep domain argument examples in the body; put MCP confirmation tokens, elicitation, profiles, MCP-only parameters and envelopes in `references/mcp.md`, and CLI commands/flags in `references/cli.md`. Link each existing reference from the body. Routers without surface-specific behavior need no reference files.
- **Code blocks for invocations.** Show concrete MCP and CLI variants in their respective references when both exist; state missing/deferred equivalents rather than inventing commands.
- **Prefer explicit IDs over names** in examples — Pipefy IDs are stable; names change.
- **Under 500 lines.** Keep skills focused; use "See also" links to related skills rather than duplicating content.
- **Progressive disclosure.** Put the common happy path first; edge cases and failure modes last.

---

## Linking to repository docs

When a skill needs stable URLs into this repo’s Markdown:

- **MCP tool semantics** — `docs/mcp/tools/<domain>.md` (cross-cutting rules: `docs/mcp/tools/cross-cutting.md`).
- **CLI-only flows** — `docs/cli/` (e.g. `docs/cli/self-healing.md`).
- **SDK usage** — `docs/sdk/README.md`.
- **Install** — always root `README.md#installation` (canonical snippets); first-time agent checklist — `skills/onboarding/pipefy-toolkit-setup/SKILL.md`; **`PIPEFY_*` env vars and `config.toml`** — `docs/config.md`; **MCP ↔ CLI matrix** — `docs/parity.md`.

---

## Intra-repo coupling

Skills and tools live in the same monorepo. When a CLI command or MCP tool is renamed:

1. Update the skill reference in the same PR (or a paired PR opened in the same review window).
2. The `skills-lint.yml` CI job validates frontmatter on every `skills/**/SKILL.md`
  and lints operation names + `pipefy` CLI references in each entrypoint and its `references/**/*.md` files. A rename that
   doesn't update the skill fails the build.

---

## Best practices

- **Keep skills short.** If a skill exceeds 500 lines, split it by sub-domain.
- **Refer by name.** Use `See also: the pipefy-automations skill`, optionally naming a section, rather than paths between skills. Consumers may flatten the catalog to `<skill-name>/SKILL.md`. Within a skill, relative links to `references/` remain portable; use repository URLs for external docs.
- **Test before shipping.** Run the skill end-to-end against a real Pipefy org before opening a PR.
