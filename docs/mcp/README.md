# MCP server documentation

Material in this tree describes **`pipefy-mcp-server`**: the MCP process, tool behavior, and client wiring.

Each tool expresses one outcome for the user, not one API endpoint, so an agent reaches a result in one call where the API would need several. [ADR-0003](../contributing/adr/0003-mcp-tools-express-outcomes.md) records why.

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

## Choose a tool surface

Not every client wants every tool. Three independent controls decide what `tools/list` returns:

| Control | Set with | Effect |
|---|---|---|
| **Launch profile** | `--profile local` / `remote` | The security floor. `local` registers every tool. `remote` serves only the remote-safe tools and validates an inbound bearer on each request. |
| **Toolset selection** | `--toolsets` / `PIPEFY_MCP_TOOLSETS` | Narrows the catalog within that floor, by subject domain or by tool profile. Selection never widens past the floor. |
| **Power discovery** | `--toolsets power` | Replaces the curated tools with four catalog meta-tools plus the raw GraphQL tools, so the working set stays small however large the catalog grows. |

The hosted URL always serves the remote-safe floor, so toolset selection applies to a local server only. The subject domains group tools by the job they serve, which differs from the reference areas above: card relations belong to `workflow`, and table relations belong to `database`. An unrecognized name is a startup error that prints every valid name.

[Toolset names](../config.md#toolset-names) defines each domain and tool profile. [Tool surface](../contributing/architecture.md#tool-surface) explains why the tools split this way.

## Where tool behavior is documented

Each tool's description and `Args:` block come from its Python docstring, which is what an MCP client shows to the model. The read-only and destructive hints come from the tool annotations. The reference pages in this tree cover the concepts, edge cases, and shared behavior that the docstrings do not state. `PIPEFY_TOOL_NAMES` in [`registry.py`](../../packages/mcp/src/pipefy_mcp/tools/registry.py) holds the canonical tool names.

Start with [`tools/cross-cutting.md`](tools/cross-cutting.md) for pagination, IDs, `debug`, permissions, and error shape — then open the domain guide you need.

For install and per-client MCP wiring (hosted HTTP, Cursor, Claude Desktop, Claude Code, Codex), see [`docs/install.md`](../install.md). First-time agent checklist: [`skills/onboarding/pipefy-toolkit-setup/SKILL.md`](../../skills/onboarding/pipefy-toolkit-setup/SKILL.md). For environment variables and `config.toml`, see [`../config.md`](../config.md). Local stdio wiring with `claude mcp add`: [Wire a local server by hand](../install.md#wire-a-local-server-by-hand).

The MCP ↔ CLI coverage matrix lives at **[`../parity.md`](../parity.md)**.
