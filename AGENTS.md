# Repository Guidelines

## Documentation map
- **`README.md`**. Project pitch, one-page install front door (`README.md#installation`: hosted MCP, Quick install, Claude Code plugin, CLI, skills), repo layout, MCP tools table, contributing.
- **`CONTRIBUTING.md`**. Skills contribution guide (frontmatter, CI, style). The entry point for GitHub contributors.
- **`docs/README.md`**. Index of docs by application (MCP, CLI, SDK) and shared guides.
- **`docs/config.md`**. `PIPEFY_*` environment variables, `config.toml` schema, precedence chain.
- **`docs/parity.md`**. MCP tool ↔ CLI command parity matrix. Source of truth for coverage and deferrals.
- **`docs/MIGRATION.md`**. What existing MCP users need to know about v0.1.
- **`docs/uninstall.md`**. `uninstall.sh --scan` and teardown, and switching between the hosted, local, and plugin channels. The two root scripts are colocated so `install.sh` and `uninstall.sh` stay reviewable side by side. A test asserts every file the installer writes is one the teardown accounts for.
- **`docs/contributing/architecture.md`**. The map of the architecture: where a change goes, what it may import, and where the code falls short of the map.
- **`docs/contributing/conventions.md`**. The code conventions, as rules with permanent IDs. A rule belongs there when a reviewer applies it by judgment to one unit of code.
- **`docs/contributing/development.md`**. Setup, test commands, the steps to add a capability, and the rules for commits and pull requests.
- **`docs/contributing/authoring.md`**. How the docs tree is organized, the audience and Diataxis cuts, where a new doc goes, and the form of a convention and of a section of `architecture.md`.
- **`docs/mcp/tools/`**. Per-area MCP tool reference (parameters, edge cases, cross-cutting behavior). Includes `identifiers.md`, the canonical map of which tool/argument expects slug vs `internal_id` vs uuid vs numeric id.
- **`docs/cli/`**. CLI-specific guides, for example introspect-then-execute.
- **`docs/sdk/README.md`**. Using `pipefy` as a library.
- **`docs/contributing/skills.md`**. Skill-authoring guide (frontmatter, naming, style). Read it before adding a skill, and follow the rules in `skills/AGENTS.md`.
- **`skills/onboarding/pipefy-toolkit-setup/`**. First-time setup checklist for agents. It links to README snippets and owns no commands.

## Project structure

```
packages/sdk/   → pipefy            (Vendor API SDK: GraphQL, models, services. Dist named `pipefy`, import module `pipefy_sdk`)
packages/mcp/   → pipefy-mcp-server (MCP tools, server lifecycle. Depends on pipefy)
packages/cli/   → pipefy-cli        (Typer CLI. Depends on pipefy)
packages/auth/  → pipefy-auth       (Shared OAuth and keychain helpers for CLI and MCP. Depends on pipefy-infra)
packages/infra/ → pipefy-infra      (Shared TOML config loader, path discovery, SSRF defenses, string helpers. Leaf package)
skills/         → agent skills catalog (Markdown, no Python package)
```

**Vendor API SDK** means the GraphQL-facing library (`pipefy`) used by both MCP and CLI, distinct from app glue or generic shared helpers.

## SDK import name

- Import the SDK as `pipefy_sdk`. The distribution is named `pipefy`, but no `pipefy` import module exists yet, so `import pipefy` fails.
- Do not start the rename to `pipefy` inside another change. [`docs/contributing/architecture.md`](docs/contributing/architecture.md#risks-and-technical-debt) carries the gap and its target.

## Rules for a code change

[`docs/contributing/development.md`](docs/contributing/development.md) holds the commands and the procedures behind each rule below.

- Write the test before the code, for each layer.
- Start every Python module with `from __future__ import annotations`, and use built-in generics and `X | None`.
- Before you commit, run `uv run ruff check .`, `uv run ruff format .`, and `uv run pytest -m "not integration"`.
- Follow the [code conventions](docs/contributing/conventions.md), and cite a rule by its ID, such as `PARSE-3`, rather than quoting it.
- Keep imports in the direction that [`docs/contributing/architecture.md`](docs/contributing/architecture.md#dependency-rule) states. Import-linter holds it inside `packages/mcp`, and ruff `TID251` holds it between packages.
- Add a capability as an SDK method, an MCP tool, and a CLI command in one change, through every step of [Add a capability](docs/contributing/development.md#add-a-capability).
- When you rename a tool or a command, update every skill that names it in the same pull request.
- Write each commit as a Conventional Commit, keep it to one change, and sign it off (`git commit -s`).
- Never commit a credential.
