# Pipefy skills catalog

Markdown playbooks in **Anthropic Skills** format: each file describes a Pipefy workflow (prerequisites, tools, steps, success criteria). Any agent that reads project files can use them (Cursor, Claude Code, Codex, and others).

## Using the catalog

**Install via [`skills.sh`](https://github.com/vercel-labs/skills)** (55+ agent targets — Claude Code, Cursor, Codex, OpenCode, …):

```bash
npx skills add pipefy/ai-toolkit                           # all skills
npx skills add pipefy/ai-toolkit --skill pipefy-pipes-and-cards
npx skills add pipefy/ai-toolkit -g -a claude-code -y      # CI-friendly
```

`skills.sh` reads canonical `skills/**/SKILL.md` files directly from this repo; no install or wheel needed.

Each entrypoint contains shared domain guidance. MCP clients load its
`references/mcp.md`; CLI users load `references/cli.md`, when present. Copy the
whole skill directory so these references travel with it. Skills refer to each
other by name, so a flat `<skill-name>/SKILL.md` installation works too.

**Reference from source (no install):**

```bash
git clone https://github.com/pipefy/ai-toolkit.git
# Reference paths such as skills/pipes-and-cards/pipefy-pipes-and-cards/SKILL.md
# in your IDE rules or agent context.
```

---

## Catalog

| Domain | Skill | Description |
|--------|-------|-------------|
| **Pipes & Cards** | [pipefy-pipes-and-cards](pipes-and-cards/pipefy-pipes-and-cards/SKILL.md) | Pipes, phases, cards, labels; phase inventory/moves; `create_card(phase_id=…)`. Prefer over `execute_graphql` for seeding. |
| **Database Tables** | [pipefy-database-tables](database-tables/pipefy-database-tables/SKILL.md) | Tables, records, schema, attachments. |
| **Relations** | [pipefy-relations](relations/pipefy-relations/SKILL.md) | Pipe and card relations. |
| **Reports** | [pipefy-reports](reports/pipefy-reports/SKILL.md) | Pipe and organization reports, async exports. |
| **Automations** | [pipefy-automations](automations/pipefy-automations/SKILL.md) | Traditional and AI automations, simulation. |
| **iPaaS (Advanced Automations)** | [pipefy-ipaas](ipaas/pipefy-ipaas/SKILL.md) | Build, test, publish, and manage integration flows through MCP meta-tools; MCP-only. |
| **AI Agents** | [pipefy-ai-agents](ai-agents/pipefy-ai-agents/SKILL.md) | Conversational AI agents and behaviors. |
| **Observability** | [pipefy-observability](observability/pipefy-observability/SKILL.md) | Logs, usage, credits, execution metrics, job exports. |
| **Members, Email & Webhooks** | [pipefy-members-email-webhooks](members-email-webhooks/pipefy-members-email-webhooks/SKILL.md) | Membership, email, webhooks. |
| **Portal setup** | [pipefy-portal-setup](portal-setup/pipefy-portal-setup/SKILL.md) | Main portal, pages, elements, sub-portals (publish/unpublish). |
| **Introspection** | [pipefy-introspection](introspection/pipefy-introspection/SKILL.md) | Schema discovery and GraphQL fallback. |
| **Attachments** | [pipefy-attachments](attachments/pipefy-attachments/SKILL.md) | Upload files to card or table-record attachment fields. |
| **Building** | [pipefy-building](building/pipefy-building/SKILL.md) | Thin router: map build/configure intent → domain skill. Not a delivery playbook. |
| **Process Design** | [pipefy-process-design](process-design/pipefy-process-design/SKILL.md) | Process architecture (consulting; not execution). |
| **Process Impact** | [pipefy-process-impact](process-impact/pipefy-process-impact/SKILL.md) | Where an automation or AI agent returns the most time: one hop, the arithmetic, the cheapest step (consulting; not execution). |
| **Process Intelligence** | [pipefy-process-intelligence](process-intelligence/pipefy-process-intelligence/SKILL.md) | Analyze pipes for improvement opportunities. |
| **API Fallback** | [pipefy-api-fallback](api-troubleshoot/pipefy-api-fallback/SKILL.md) | Raw GraphQL fallback when higher-level tools are insufficient. |
| **Onboarding** | [pipefy-toolkit-setup](onboarding/pipefy-toolkit-setup/SKILL.md) | First-time install: Cursor Marketplace plugin, hosted MCP, `install.sh`, or Claude Code plugin. |

---

## Contributing

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — frontmatter, CI checks, style, review rubric.
- [`docs/contributing/skills.md`](../docs/contributing/skills.md): authoring guide.
- [`.github/skill-template/`](../.github/skill-template/) — copyable `SKILL.md` starter for new skills (local repos or PRs here).
