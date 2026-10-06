<div align="center">
  <img
    src="docs/images/pipefy-developers-banner.png"
    alt="Pipefy Developers — AI Toolkit (MCP Server, Pipefy CLI, GraphQL SDK, Agent Skills)"
    width="100%"
  />
</div>

<p align="center">
  <a href="https://github.com/pipefy/ai-toolkit/actions/workflows/ci.yml"><img src="https://github.com/pipefy/ai-toolkit/actions/workflows/ci.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+" /></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/uv-package%20manager-blueviolet" alt="uv package manager" /></a>
  <a href="https://modelcontextprotocol.io/introduction"><img src="https://img.shields.io/badge/MCP-Server-orange" alt="MCP Server" /></a>
  <a href="https://github.com/pipefy/ai-toolkit/releases/latest"><img src="https://img.shields.io/github/v/release/pipefy/ai-toolkit?include_prereleases&sort=semver" alt="Latest release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License" /></a>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#installation">Installation</a> •
  <a href="#repository-layout">Repository layout</a> •
  <a href="#mcp-server">MCP server</a> •
  <a href="#command-line-interface">CLI</a> •
  <a href="#agent-skills">Agent skills</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#legal">Legal</a>
</p>

---

## Overview

The Pipefy AI Toolkit lets an AI agent, a script, or a Python program work in Pipefy: read and change pipes, cards, tables, automations, AI agents, and reports, with the permissions of the account that signs in. It ships four components:

| Component | Package / path | Purpose |
|-----------|----------------|---------|
| **MCP server** | `pipefy-mcp-server` | Exposes the full local catalog to MCP clients (Cursor, Claude Desktop, Claude Code, and others). The hosted URL that the Cursor Marketplace plugin and Hosted MCP use serves the remote-safe floor instead; see [MCP server](#mcp-server). |
| **CLI** | `pipefy-cli` | Terminal commands aligned with MCP capabilities; see [`docs/parity.md`](docs/parity.md). |
| **SDK** | `pipefy` | Vendor GraphQL client, services, and models shared by MCP and CLI. |
| **Skills** | [`skills/`](skills/) | Markdown playbooks (Anthropic Skills format) for common Pipefy workflows. |

Feedback and issues: [GitHub Issues](https://github.com/pipefy/ai-toolkit/issues) · **dev@pipefy.com**

### What it looks like

In an MCP client, ask in plain words. The agent picks the tools, such as `search_pipes` and `get_cards`:

```text
Which cards in my "Hiring" pipe are still in the Interview phase?
```

In a terminal, the CLI runs the same operations:

```sh
pipefy pipe list --name Hiring --json
pipefy card list --pipe 67890
```

---

## Installation

[`docs/install.md`](docs/install.md) covers every path in full:

| You are in | You want | Path |
|---|---|---|
| Claude Code | The fastest start, no local Python | [Hosted MCP](docs/install.md#1-hosted-mcp-claude-code) |
| Claude Code | The hosted server plus slash commands, skills, and the CLI | [Claude Code plugin](docs/install.md#2-claude-code-plugin) |
| Cursor | The fastest start, no local Python | [Cursor Marketplace plugin](docs/install.md#6-cursor-marketplace-plugin) |
| Cursor, Claude Desktop, or Codex | The local-file tools, the CLI, or one command for everything | [Quick-install script](docs/install.md#3-quick-install-script) |
| A terminal, a script, or CI | No agent | [CLI only](docs/install.md#4-cli-only) |
| Any agent | Only the workflow playbooks | [Skills only](docs/install.md#5-skills-only) |

**Register exactly one Pipefy MCP server.** A second registration shadows the first, whatever its name. [Before you install](docs/install.md#before-you-install) shows how to check a machine, and [`docs/uninstall.md`](docs/uninstall.md) shows how to switch paths.

---

## Repository layout

`uv` workspace of Python packages, plus a skills catalog. **`pipefy`** is the vendor GraphQL layer. MCP and CLI depend on it and do not import each other.

| Path | Distribution | Role |
|------|--------------|------|
| [`packages/sdk/`](packages/sdk/) | `pipefy` | GraphQL transport, services, queries, Pydantic models. [Package README](packages/sdk/README.md) |
| [`packages/mcp/`](packages/mcp/) | `pipefy-mcp-server` | MCP tool registration and server lifecycle. [Package README](packages/mcp/README.md) |
| [`packages/cli/`](packages/cli/) | `pipefy-cli` | Typer CLI (`pipefy` command). [Package README](packages/cli/README.md) |
| [`packages/auth/`](packages/auth/) | `pipefy-auth` | Shared OAuth and keychain helpers for MCP and CLI. [Package README](packages/auth/README.md) |
| [`packages/infra/`](packages/infra/) | `pipefy-infra` | Shared config loading, path discovery, and URL safety. Leaf package. [Package README](packages/infra/README.md) |
| [`skills/`](skills/) | — | Agent skill playbooks. [Catalog](skills/README.md) |

---

## MCP server

The local server registers the full catalog. Canonical names: `PIPEFY_TOOL_NAMES` in [`packages/mcp/src/pipefy_mcp/tools/registry.py`](packages/mcp/src/pipefy_mcp/tools/registry.py). The hosted URL (Marketplace plugin and Hosted MCP) serves the remote-safe floor instead: it withholds the tools whose input is a file on your machine.

Tool descriptions and `Args:` blocks come from Python docstrings (what MCP clients show to models), and the read-only and destructive hints come from the tool annotations. Per-area reference docs cover the concepts, edge cases, and cross-cutting behavior that the docstrings do not state.

[`docs/mcp/README.md`](docs/mcp/README.md) lists the reference for each area. Start with [`cross-cutting.md`](docs/mcp/tools/cross-cutting.md) for pagination, IDs, permissions, and the error shape.

### Choosing a tool surface

Not every client wants every tool. Three independent controls decide what `tools/list` returns:

| Control | Set with | Effect |
|---|---|---|
| **Launch profile** | `--profile local` / `remote` | The security floor. `local` registers every tool; `remote` serves only the remote-safe surface and validates an inbound bearer per request. |
| **Toolset selection** | `--toolsets` / `PIPEFY_MCP_TOOLSETS` | Narrows within that floor — by **subject domain** (`workflow`, `database`, `interfaces`, `automation`, `intelligence`, `analytics`, `governance`, `integration`) or by **tool profile** (`requester`, `operator`, `manager`, `builder`, `admin`, `auditor`), unioned. Selection never widens past the floor. |
| **Power discovery** | `--toolsets power` | Replaces the curated tools with four catalog meta-tools (`get_tool_categories`, `search_tools`, `describe_tool`, `execute_tool`) plus the raw-GraphQL tools, so the working set stays small no matter how large the catalog grows. |

The toolset names are a **different grouping from the reference areas**: those follow the documentation, while subject domains partition tools by the job they serve — card relations land in `workflow`, table relations in `database`. Passing an unrecognized name is a startup error that prints the full list of valid ones. `--toolsets` / `PIPEFY_MCP_TOOLSETS` is a process-level switch: it applies to the local stdio server only, not to the hosted URL.

Per-name definitions and precedence: [`docs/config.md`](docs/config.md). Why the tools split into domains and tool profiles: [Tool surface](docs/contributing/architecture.md#tool-surface).

---

## Command-line interface

The **`pipefy`** CLI mirrors shipped MCP capabilities where parity is defined in **[`docs/parity.md`](docs/parity.md)**. Conventions: Rich output by default, **`--json`** for scripts, **`--yes`** on destructive commands.

```sh
pipefy pipe list --json
pipefy card get 123456789
pipefy introspect query --name getPipe
```

CLI-specific guides: **[`docs/cli/`](docs/cli/README.md)** (including [introspect-then-execute](docs/cli/self-healing.md)).

---

## Agent skills

The [`skills/`](skills/) directory holds workflow playbooks: prerequisites, tool tables (MCP + CLI), steps, and success criteria. Compatible with any agent that reads Markdown (Cursor, Claude Code, Codex, and others). Distribution is via [`skills.sh`](https://github.com/vercel-labs/skills) (55+ agent targets); install commands are under [Installation](#installation) above.

Full catalog: [`skills/README.md`](skills/README.md). Authoring: [`docs/contributing/skills.md`](docs/contributing/skills.md). Contributions: [`CONTRIBUTING.md`](CONTRIBUTING.md).

**Card & phase agent ergonomics:** use [`skills/pipes-and-cards/pipefy-pipes-and-cards/SKILL.md`](skills/pipes-and-cards/pipefy-pipes-and-cards/SKILL.md) (workflow *Seed pipe across phases*; prefer dedicated tools over `execute_graphql`).

---

## Documentation

[`docs/README.md`](docs/README.md) indexes every guide, for people who use the toolkit and for people who contribute to it.

---

## Contributing

Contributions are welcome via issues and pull requests. Commits must include a [DCO](https://developercertificate.org/) sign-off (`git commit -s`); see [`CONTRIBUTING.md`](CONTRIBUTING.md).

| Area | How to contribute |
|------|-------------------|
| **Skills** | Markdown only — see [`docs/contributing/skills.md`](docs/contributing/skills.md). |
| **MCP / CLI / SDK** | Follow [`docs/contributing/development.md`](docs/contributing/development.md) and [`docs/parity.md`](docs/parity.md). |
| **Field mapping gaps** | Open an issue with the field type and expected behavior. |

---

## Legal

This toolkit (MCP server, CLI, SDK, and skill/blueprint playbooks) is licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for trademark reservations.

Your access to and use of the Pipefy platform through this toolkit is governed by the [Pipefy Solutions Terms and Conditions](https://www.pipefy.com/terms-and-conditions/) ([versão em português](https://www.pipefy.com/pt-br/termos-e-condicoes/)) and, for AI features, by the Pipefy AI Additional Terms (to be published and incorporated by reference into those terms), including their acceptable use provisions. Using this toolkit requires a Pipefy account; nothing in the Apache 2.0 license grants rights to the Pipefy service.

**Templates, not advice.** Skills and blueprints are configurable templates provided for general informational purposes. They do not constitute legal, HR, financial, tax, or other professional advice, and must be reviewed, configured, and validated by qualified professionals before production use. Each published blueprint ships with a `COMPLIANCE.md` describing its intended purpose, out-of-scope uses, AI risk classification, and default human-oversight settings (see [`COMPLIANCE.template.md`](.github/skill-template/COMPLIANCE.template.md)).

**AI-generated output.** Outputs produced by AI features may contain errors or omissions and must be independently verified before being relied upon.

**Beta software.** Pre-1.0 releases are provided “AS IS”, without warranties of any kind, and may change or be discontinued at any time. See the full disclaimer in [TERMS.md](TERMS.md).

Security reports: see [SECURITY.md](SECURITY.md). Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md).
