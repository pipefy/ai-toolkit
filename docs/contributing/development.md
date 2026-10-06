# Development

This guide covers a change to the SDK, the CLI, or the MCP server. [`CONTRIBUTING.md`](../../CONTRIBUTING.md) covers a skill, the sign-off, and the review for a regulated domain. [`architecture.md`](architecture.md) says where a change goes and what it may import, and [`conventions.md`](conventions.md) holds the code rules.

## Set up a clone

1. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/).
2. From the repository root, run `uv sync`. It installs every workspace package.
3. If you want the checks to run before each commit, run `uvx pre-commit install` once per clone.

The pre-commit hook runs `ruff` lint and format on Python files. On `install.sh` and `uninstall.sh` it runs `shellcheck --shell=sh` from `shellcheck-py`, `sh -n`, and a check that every `rm` and `rmdir` in `uninstall.sh` goes through its `remove_path` guard. CI runs the same checks, plus `dash -n`. To run the hook on the whole tree, use `uvx pre-commit run --all-files`. To skip it for a work-in-progress commit, use `git commit --no-verify`.

The `ruff` revision in `.pre-commit-config.yaml` must move together with `uv.lock`, so that the hook and CI run the same `ruff`. CI also pins the same `shellcheck-py` release that the hook uses.

## Run the applications

- `uv run pipefy-mcp-server` starts the MCP server.
- `uv run pipefy --help` runs the CLI.

To smoke-test a tool change by hand, use Cursor's MCP integration. To debug the protocol itself, use MCP Inspector:

```bash
npx @modelcontextprotocol/inspector uv --directory . run pipefy-mcp-server
```

## Test

Write the tests first for each layer: red, then green, then refactor. Tests live beside their package, in `packages/<pkg>/tests/`, and use `pytest-asyncio`, `pytest-cov`, and `pytest-mock`.

| Command | What it runs |
|---|---|
| `uv run pytest` | The full suite |
| `uv run pytest -m "not integration"` | Every test that needs no network, as CI runs it |
| `uv run pytest packages/sdk/tests` | One package |
| `uv run pytest -m integration` | Tests marked `@pytest.mark.integration`, which need `PIPEFY_*` credentials |
| `uv run pytest --cov=packages/sdk/src/pipefy_sdk --cov-report=term-missing` | SDK coverage |

A unit test needs no marker.

## Code style

- Target Python 3.11 or later, and start every module with `from __future__ import annotations`.
- Use built-in generics such as `list[str]` and `dict[str, Any]`, and union syntax such as `str | None`.
- Run `uv run ruff check .` and `uv run ruff format .` before you commit. `ruff` enforces formatting and import order.

## Add a capability

A capability is an SDK method, an MCP tool, and a CLI command that do the same thing. Add all three in one change:

1. Add the GraphQL query in `packages/sdk/src/pipefy_sdk/queries/`.
2. Add the service method in `packages/sdk/src/pipefy_sdk/services/`.
3. Expose it through `PipefyClient` in `packages/sdk/src/pipefy_sdk/client.py`.
4. Register the MCP tool in `packages/mcp/src/pipefy_mcp/tools/`, add its name to `PIPEFY_TOOL_NAMES` in `tools/registry.py`, and give it a domain in `tools/toolsets.py`. The test in `tests/tools/test_toolsets.py` fails the build for a tool with no domain.
5. Add the CLI command in `packages/cli/src/pipefy_cli/commands/`, and register it in `main.py`.
6. Mark the capability as shipped in [`docs/parity.md`](../parity.md).
7. Update every skill in `skills/` that the capability affects, in the same pull request or in a paired one opened in the same review window.

## Rename a tool or a command

A rename that breaks a command or a tool updates every affected skill in the same pull request, or in a paired one opened in the same review window. CI enforces this rule: `skills-lint.yml` checks the frontmatter of each `SKILL.md`, the operation and MCP tool names with their `name=` arguments, and every `pipefy` invocation written as code, down to its subcommand path and `--` options, in `skills/**/SKILL.md` and its `references/`. A rename that leaves a skill behind fails the build.

## Commits and pull requests

- Write each commit message as a [Conventional Commit](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, or `chore:`, with an optional scope.
- Make each commit one functional change.
- Sign off every commit with `git commit -s`. CI checks the Developer Certificate of Origin, which [`CONTRIBUTING.md`](../../CONTRIBUTING.md#developer-certificate-of-origin-dco) describes, so an unsigned commit fails.
- Split a pull request that touches more than 10 files or changes more than 300 lines.
- In each pull request, include a summary, the tests you ran with their results, and the docs you updated where a tool's behavior or the configuration changed.

## Credentials

Read credentials from environment variables or from `.env`, and never commit one. [`docs/config.md`](../config.md) lists every variable.
