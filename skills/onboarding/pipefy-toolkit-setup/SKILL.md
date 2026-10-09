---
name: pipefy-toolkit-setup
description: >
  Guide a first-time user through Pipefy AI toolkit setup (Cursor Marketplace
  plugin, hosted MCP, local install.sh, or Claude Code plugin). Use when the
  user asks to install Pipefy MCP, connect Claude/Cursor to Pipefy, run
  /pipefy:install, or set up mcp.pipefy.com. Do not use for day-to-day Pipefy workflows
  after MCP is already working.
tags: [pipefy, onboarding, install, mcp, setup, claude, cursor]
metadata:
  surfaces: "mcp cli"
---

# Pipefy toolkit setup (first-time onboarding)

Choose a connection path below, then read the [MCP reference](references/mcp.md) or [CLI reference](references/cli.md) for that path. Load only the relevant reference.

**Canonical install snippets** live in [`docs/install.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md). The root README has a quick-start table with the first command for each install path. This skill is the agent **checklist**: print or run the install-guide blocks verbatim, and do not invent alternate commands.

Edge cases: [`packages/mcp/README.md`](https://github.com/pipefy/ai-toolkit/blob/main/packages/mcp/README.md). Auth: [`docs/cli/auth.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/cli/auth.md). Env: [`docs/config.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/config.md).

## When to use

- “Set up Pipefy”, “install the MCP”, or “connect Claude/Cursor to Pipefy”.
- The user mentions a client plugin, a hosted connection, or a fresh machine without toolkit access.

**Do not use** once tools already work — switch to a domain skill (pipes, tables, …).

## Prerequisites

- User has a Pipefy account (Admin access if they need a service account).

## Steps

1. **Choose one path** — ask the user; do not pick silently. Respect whether they want a hosted connection, a client plugin, a local toolkit, or CLI only.

   If they only say “Claude Code”, ask: Hosted MCP (zero local Python) or the Claude Code plugin (slash commands and local CLI)? If unsure, suggest Hosted.

   If they only say “Cursor”, ask: Cursor Marketplace plugin (hosted, no local Python) or Quick install (local CLI and tools that read local files)? If unsure, suggest the plugin.

   | Path | Install guide section | Outcome |
   |------|----------------|---------|
   | Cursor Marketplace plugin | [Cursor Marketplace plugin](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md#6-cursor-marketplace-plugin) | Hosted server, browser sign-in, no local Python |
   | Hosted MCP | [Hosted MCP](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md#1-hosted-mcp-claude-code) | HTTPS `mcp.pipefy.com` |
   | Local toolkit | [Quick install](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md#3-quick-install-script) | Local server and CLI, including local-file tools |
   | Claude Code plugin | [Claude Code plugin](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md#2-claude-code-plugin) | Marketplace and slash install/login |
   | CLI only | [CLI](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md#4-cli-only) | `pipefy` on PATH; no MCP |

2. **Execute the canonical install instructions** for that path. Keep client setup and local installation aligned with the user's choice.
3. **Authenticate** using the selected path's login flow.
4. **Verify** access with a permitted read-only organization operation (`list_organizations` needs no id and surfaces organization ids), or the local installation check. Check for conflicting registrations using the selected reference.

## Success criteria

- Exactly the selected connection is configured, with no conflicting registrations; CLI-only needs no server registration.
- Authentication completed.
- The permitted read-only operation or local installation check succeeds.

## See also

- [`docs/install.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md)
- [`docs/uninstall.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/uninstall.md) — `uninstall.sh --scan`, teardown, and switching between hosted, local, and plugin
- [`skills/README.md`](https://github.com/pipefy/ai-toolkit/blob/main/skills/README.md)
