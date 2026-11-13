# Repository guidelines

## Workspace layout

The `uv` workspace packages depend strictly downward (`cli` and `mcp` -> `sdk` and `auth` -> `infra`), enforced per package by ruff `TID251`. `pipefy-mcp-server` and `pipefy-cli` never import each other, and neither imports `pipefy_sdk.services` or `pipefy_sdk.queries` directly.

| Path | Distribution | Import module | Role |
|---|---|---|---|
| `packages/sdk/` | `pipefy` | `pipefy_sdk` | GraphQL client, `PipefyEngine` / `PipefyClient`, queries, models, and domain helpers. Keep `import pipefy_sdk` until `src/pipefy/` exists. |
| `packages/mcp/` | `pipefy-mcp-server` | `pipefy_mcp` | MCP server (`MCPServer`), tool registrations, toolset profiles, and hosted auth/observability. |
| `packages/cli/` | `pipefy-cli` | `pipefy_cli` | `pipefy` Typer CLI over `pipefy_sdk` and `pipefy_auth`. |
| `packages/auth/` | `pipefy-auth` | `pipefy_auth` | OAuth login, keychain session storage, service-account credentials, and inbound JWT validation. |
| `packages/infra/` | `pipefy-infra` | `pipefy_infra` | Leaf utilities: TOML config loader, SSRF URL guards, path discovery, and client telemetry headers. |
| `plugins/pipefy/` | (plugin) | (Markdown) | Claude Code and Cursor plugin: `.mcp.json`, slash commands, and agent skills (`plugins/pipefy/skills/`). |
| `tests/` | (root tests) | (none) | Repo-wide suites: skill linters, plugin packaging, version lockstep, and `install.sh` / `uninstall.sh` parity. |

## Guides by task

Open the matching guide before editing that area:

- **Touching `packages/mcp/`** (tools, profiles, `meta=REMOTE`, middleware, runtime, or hosted mode): [`packages/mcp/AGENTS.md`](packages/mcp/AGENTS.md).
- **Touching `plugins/pipefy/` or skills**: [`plugins/AGENTS.md`](plugins/AGENTS.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Designing layers, ports, settings, or the `pipefy_sdk` rename**: [`docs/architecture.md`](docs/architecture.md).
- **Typing GraphQL responses** (`TypedDict` vs validating Pydantic model): [`docs/response-typing.md`](docs/response-typing.md).
- **Adding or renaming MCP tools or CLI commands**: [`docs/parity.md`](docs/parity.md) and [`docs/mcp/tools/`](docs/mcp/tools/) (`identifiers.md` maps slug vs `internal_id` vs UUID vs numeric ID).
- **Changing `PIPEFY_*` env vars, `config.toml`, or auth precedence**: [`docs/config.md`](docs/config.md) and [`docs/cli/auth.md`](docs/cli/auth.md).
- **Changing `install.sh`, `uninstall.sh`, or outbound hosts/headers**: [`docs/install.md`](docs/install.md), [`docs/uninstall.md`](docs/uninstall.md), and [`docs/trust.md`](docs/trust.md).
- **Changing runtime dependencies**: [`docs/dependencies.md`](docs/dependencies.md).

## Build, test, and development

Run unit tests with `PIPEFY_*` environment variables unset so local credentials or keychain overrides do not leak into test cases.

- **Install workspace**: `uv sync --all-extras --dev`
- **Unit tests (CI gate, no network)**: `uv run pytest -m "not integration"`
- **Single package or root suite**: `uv run pytest packages/sdk/tests` (or `packages/mcp/tests`, `packages/cli/tests`, `packages/auth/tests`, `packages/infra/tests`, `tests`)
- **Integration tests (live API)**: copy `.env.example` to `.env`, set `PIPEFY_SERVICE_ACCOUNT_*`, and run `uv run pytest -m integration -v`
- **Lint and format**: `uv run ruff check .` and `uv run ruff format .`
- **Banned upward imports** (run per package so each `pyproject.toml` applies): `(cd packages/sdk && uv run ruff check src) && (cd packages/auth && uv run ruff check src) && (cd packages/infra && uv run ruff check src)`
- **MCP intra-package layers**: `(cd packages/mcp && uv run lint-imports)`
- **Plugin and skills gates**: `python3 .github/workflows/scripts/lint_plugin_packaging.py` (reads `git ls-files`, so stage new files first), `uv run python .github/workflows/scripts/lint_skill_frontmatter.py`, and `uv run python .github/workflows/scripts/lint_skill_refs.py`
- **Shell scripts** (`install.sh`, `uninstall.sh`): run `uvx --from shellcheck-py==0.11.0.1 shellcheck --shell=sh install.sh uninstall.sh` and `sh -n install.sh uninstall.sh`. You can also run `uvx pre-commit install` once per clone, keeping the ruff `rev` in `.pre-commit-config.yaml` aligned with `uv.lock`.
- **GraphQL input models**: `uv run python scripts/generate_graphql_inputs.py check` compares `_generated.py` against `packages/sdk/schema/input_types.json`. Use `generate` to rewrite `_generated.py` and `snapshot` to refresh from the live API.
- **Version lockstep**: `uv run python scripts/bump_version.py verify` (change versions only through `scripts/bump_version.py`).
- **Manual E2E**: test MCP tool changes through Cursor's MCP client first. Use MCP Inspector (`npx @modelcontextprotocol/inspector uv --directory . run pipefy-mcp-server`) for protocol debugging.

## Coding style and boundaries

- **Python 3.11+.** Start every module with `from __future__ import annotations`. Use built-in generics (`list[str]`, `dict[str, Any]`) and `X | Y` unions.
- **Validate at boundaries, trust types inside.** `MCPServer` tool signatures, Typer CLI signatures, and `pydantic-settings` models coerce and reject untyped input at the edge. Internal functions trust parameter annotations and do not add runtime `isinstance` guards. Nested unschema'd dicts (`filter: dict[str, Any] | None`) still earn a dedicated boundary parser such as `prepare_report_cards_filter` or `validate_record_filter`.
- **Parse, don't validate.** Boundary parsers return a self-guaranteeing type whose constructor enforces its invariants (Pydantic model, leaf value type, or closed sum type like `ResolvedAuth`). Avoid bare `raise` guards that pass loose input on. Fail cross-field settings rules at construction.
- **Compose once per app.** Keep parsed types free of I/O, framework types, and SDK clients. Wire effects (keychain, HTTP, `PipefyEngine`, token verifiers) in the app's composition root (`McpRuntime.for_profile` in `pipefy_mcp`, CLI command bootstrap in `pipefy_cli`). Full layer rules live in [`docs/architecture.md`](docs/architecture.md).
- **Respect Pipefy API and CLI quirks.** GraphQL input field casing mixes `camelCase` and `snake_case` (`cardId` vs `card_id` are distinct). Use explicit per-field Pydantic aliases with `populate_by_name=True`, never a blanket case converter. In CLI tests, Rich splits `--option-name` with ANSI codes in CI (`FORCE_COLOR=1`), so assert on option-free text fragments.

## Adding a new capability

A capability ships across SDK, MCP, CLI, parity docs, and skills. Follow TDD at each layer (failing test -> implementation -> green):

1. Add the static `gql()` query or mutation in `packages/sdk/src/pipefy_sdk/queries/`.
2. Add the adapter method in `packages/sdk/src/pipefy_sdk/services/` (extract pure branching into a helper) and expose it on `PipefyClient` in `packages/sdk/src/pipefy_sdk/client.py`.
3. Register the MCP tool in `packages/mcp/src/pipefy_mcp/tools/`, add it to `PIPEFY_TOOL_NAMES` (`registry.py`), and assign a domain in `tools/toolsets.py`. Add `meta=REMOTE` only when it meets the criteria in [`packages/mcp/AGENTS.md`](packages/mcp/AGENTS.md). Destructive tools must resolve `get_pipefy_client(ctx)` before `check_destructive_confirmation`.
4. Add the CLI command in `packages/cli/src/pipefy_cli/commands/` and register it in `main.py` (or record an explicit deferral in `docs/parity.md`).
5. Update `docs/parity.md` and `docs/mcp/tools/<domain>.md`, keeping shared UX wording identical across docstrings, CLI help, and parity rows.
6. Update affected skills in `plugins/pipefy/skills/` in the same PR. Renaming a tool or CLI command/flag without updating skill references fails `skills-lint.yml`.

## Commit and PR guidelines

- Use Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`) with one atomic change per commit. Split PRs that exceed 10 files or 300 changed lines.
- Sign off every commit with `git commit -s` (CI enforces DCO). Never commit secrets or `.env` files.
- Include a summary, exact test commands and results, and doc updates in every PR description.
