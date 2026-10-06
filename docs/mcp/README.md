# MCP server documentation

Material in this tree describes **`pipefy-mcp-server`**: the MCP process, tool behavior, and client wiring.

## Tool design

An MCP tool expresses one user outcome, not one API endpoint. It orchestrates the underlying steps in code, so the model does not chain calls in its context.

`TOOL-1` and `TOOL-2` in [`conventions.md`](../contributing/conventions.md) are the rules a tool follows, and the reasoning is in the decision record [ADR-0003](../contributing/adr/0003-mcp-tools-express-outcomes.md).

## Contents

| Path | Description |
|------|-------------|
| [`tools/cross-cutting.md`](tools/cross-cutting.md) | Behavior every tool shares |
| [`tools/identifiers.md`](tools/identifiers.md) | Which id form each tool and argument expects |
| [`tools/pipes-and-cards.md`](tools/pipes-and-cards.md) | Pipes, phases, fields, labels, and cards |
| [`tools/reports.md`](tools/reports.md) | Reports and exports |
| [`tools/automations-and-ai.md`](tools/automations-and-ai.md) | Automations, AI automations, and AI agents |
| [`tools/llm-providers.md`](tools/llm-providers.md) | LLM providers |
| [`tools/knowledge-bases.md`](tools/knowledge-bases.md) | Knowledge bases |
| [`tools/observability.md`](tools/observability.md) | Logs, usage, and metrics |
| [`tools/service-accounts.md`](tools/service-accounts.md) | Service accounts |
| [`tools/organization.md`](tools/organization.md) | Organizations |
| [`tools/portal.md`](tools/portal.md) | Portals |
| [`tools/ipaas.md`](tools/ipaas.md) | iPaaS (Advanced Automations) |
| [`tools/introspection.md`](tools/introspection.md) | Schema discovery and raw GraphQL |

Start with [`tools/cross-cutting.md`](tools/cross-cutting.md) for pagination, IDs, `debug`, permissions, and error shape — then open the domain guide you need.

For install and per-client MCP wiring (hosted HTTP, Cursor, Claude Desktop, Claude Code, Codex), see the root [`README.md#installation`](../../README.md#installation). First-time agent checklist: [`skills/onboarding/pipefy-toolkit-setup/SKILL.md`](../../skills/onboarding/pipefy-toolkit-setup/SKILL.md). For environment variables and `config.toml`, see [`../config.md`](../config.md). Local stdio wiring with `claude mcp add`: [`packages/mcp/README.md`](../../packages/mcp/README.md).

The MCP ↔ CLI coverage matrix lives at **[`../parity.md`](../parity.md)**.
