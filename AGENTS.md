# Repository Guidelines

## Where things are

[`docs/README.md`](docs/README.md) indexes every doc. Each workspace package sits under `packages/` with its own `pyproject.toml`, and `Package decomposition` in [`architecture.md`](docs/contributing/architecture.md#package-decomposition) says what each one owns. A scoped `AGENTS.md` in `packages/mcp/` and `skills/` adds the rules for that tree.

## SDK import name

- Import the SDK as `pipefy_sdk`. The distribution is named `pipefy`, but no `pipefy` import module exists yet, so `import pipefy` fails.
- Do not start the rename to `pipefy` inside another change. [`docs/contributing/architecture.md`](docs/contributing/architecture.md#risks-and-technical-debt) carries the gap and its target.

## Rules for a code change

[`docs/contributing/development.md`](docs/contributing/development.md) holds the commands and the procedures behind each rule below.

- Write the test before the code, for each layer.
- Start every Python module with `from __future__ import annotations`, and use built-in generics and `X | None`.
- Before you commit, run `uvx pre-commit run --all-files` and `uv run pytest -m "not integration"`.
- Follow the [code conventions](docs/contributing/conventions.md), and cite a rule by its ID, such as `PARSE-3`, rather than quoting it.
- Keep imports in the direction that [`docs/contributing/architecture.md`](docs/contributing/architecture.md#dependency-rule) states. Import-linter holds it inside `packages/mcp`, and ruff `TID251` holds it between packages.
- Add a capability as an SDK method, an MCP tool, and a CLI command in one change, through every step of [Add a capability](docs/contributing/development.md#add-a-capability).
- When you rename a tool or a command, update every skill that names it in the same pull request.
- Write each commit as a Conventional Commit, keep it to one change, and sign it off (`git commit -s`).
- Never commit a credential.
