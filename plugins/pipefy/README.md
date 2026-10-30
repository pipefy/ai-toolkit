# Pipefy plugin

The Pipefy plugin connects Claude Code and Cursor to [Pipefy](https://www.pipefy.com). It adds three parts:

- **The hosted Pipefy MCP server** at `https://mcp.pipefy.com/mcp`. The agent manages pipes, cards, tables, reports, automations and AI agents through it. You sign in through the browser the first time a tool needs your Pipefy account, and nothing runs on your machine.
- **Skills.** Each skill is a Markdown playbook for one Pipefy workflow: prerequisites, tools, steps and success criteria. The table below lists them.
- **Two Claude Code commands.** `/pipefy:install` installs the Pipefy CLI with `uv`, and `/pipefy:pipefy-login` signs the CLI in to Pipefy.

Every install path, including the skills alone through `npx skills add`, is in the [install guide](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md).

## Skills

Each skill folder holds a `SKILL.md` with the shared domain guidance. MCP clients also load its `references/mcp.md`, and CLI users load `references/cli.md`, when the file exists. Skills refer to each other by name.

| Domain | Skill | Description |
|--------|-------|-------------|
| **Pipes & Cards** | [pipefy-pipes-and-cards](skills/pipefy-pipes-and-cards/SKILL.md) | Pipes, phases, cards, labels; phase inventory/moves; `create_card(phase_id=…)`. Prefer over `execute_graphql` for seeding. |
| **Database Tables** | [pipefy-database-tables](skills/pipefy-database-tables/SKILL.md) | Tables, records, schema, attachments. |
| **Relations** | [pipefy-relations](skills/pipefy-relations/SKILL.md) | Pipe and card relations. |
| **Reports** | [pipefy-reports](skills/pipefy-reports/SKILL.md) | Pipe and organization reports, async exports. |
| **Automations** | [pipefy-automations](skills/pipefy-automations/SKILL.md) | Traditional and AI automations, simulation. |
| **iPaaS (Advanced Automations)** | [pipefy-ipaas](skills/pipefy-ipaas/SKILL.md) | Build, test, publish, and manage integration flows through MCP meta-tools; MCP-only. |
| **AI Agents** | [pipefy-ai-agents](skills/pipefy-ai-agents/SKILL.md) | Conversational AI agents and behaviors. |
| **Observability** | [pipefy-observability](skills/pipefy-observability/SKILL.md) | Logs, usage, credits, execution metrics, job exports. |
| **Members, Email & Webhooks** | [pipefy-members-email-webhooks](skills/pipefy-members-email-webhooks/SKILL.md) | Membership, email, webhooks. |
| **Portal setup** | [pipefy-portal-setup](skills/pipefy-portal-setup/SKILL.md) | Main portal, pages, elements, sub-portals (publish/unpublish). |
| **HTML interfaces** | [pipefy-html-interfaces](skills/pipefy-html-interfaces/SKILL.md) | Pages written as one HTML document, with data sources from pipes and tables and button actions on their records. |
| **Introspection** | [pipefy-introspection](skills/pipefy-introspection/SKILL.md) | Schema discovery and GraphQL fallback. |
| **Attachments** | [pipefy-attachments](skills/pipefy-attachments/SKILL.md) | Upload files to card or table-record attachment fields. |
| **Building** | [pipefy-building](skills/pipefy-building/SKILL.md) | Thin router: map build/configure intent → domain skill. Not a delivery playbook. |
| **Process Design** | [pipefy-process-design](skills/pipefy-process-design/SKILL.md) | Process architecture (consulting; not execution). |
| **Process Impact** | [pipefy-process-impact](skills/pipefy-process-impact/SKILL.md) | Where an automation or AI agent returns the most time: one hop, the arithmetic, the cheapest step (consulting; not execution). |
| **Process Intelligence** | [pipefy-process-intelligence](skills/pipefy-process-intelligence/SKILL.md) | Analyze pipes for improvement opportunities. |
| **API Fallback** | [pipefy-api-fallback](skills/pipefy-api-fallback/SKILL.md) | Raw GraphQL fallback when higher-level tools are insufficient. |
| **Onboarding** | [pipefy-toolkit-setup](skills/pipefy-toolkit-setup/SKILL.md) | First-time install: Cursor Marketplace plugin, hosted MCP, `install.sh`, or Claude Code plugin. |

## Contributing

Read [`CONTRIBUTING.md`](https://github.com/pipefy/ai-toolkit/blob/main/CONTRIBUTING.md) and the authoring guide in [`plugins/AGENTS.md`](https://github.com/pipefy/ai-toolkit/blob/main/plugins/AGENTS.md) before you add or change a skill.

## License

The plugin is licensed under the [Apache License 2.0](https://github.com/pipefy/ai-toolkit/blob/main/LICENSE). The "Pipefy" name, logo and brand assets are trademarks of Pipefy, Inc. and are not licensed under the Apache License 2.0; see [`NOTICE`](https://github.com/pipefy/ai-toolkit/blob/main/NOTICE). Your use of the Pipefy platform is governed by the [Pipefy Solutions Terms and Conditions](https://www.pipefy.com/terms-and-conditions/).
