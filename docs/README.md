# Documentation index

Guides for the **[pipefy/ai-toolkit](https://github.com/pipefy/ai-toolkit)** monorepo, which ships the MCP server `pipefy-mcp-server`, the CLI `pipefy-cli`, the SDK `pipefy`, and the agent skills. First-time install and per-client MCP wiring live in the root [`README.md#installation`](../README.md#installation).

## Using the toolkit

| Doc | Contents |
|-----|----------|
| [`mcp/`](mcp/README.md) | MCP tool reference by area, and the behavior every tool shares |
| [`cli/`](cli/README.md) | CLI usage patterns and discover-then-execute flows |
| [`cli/auth.md`](cli/auth.md) | CLI credential precedence, `pipefy auth login`, troubleshooting |
| [`sdk/`](sdk/README.md) | Using `pipefy` as a library |
| [`config.md`](config.md) | `PIPEFY_*` environment variables, `config.toml` schema and path, precedence chain |
| [`parity.md`](parity.md) | Which CLI command matches each MCP tool, and where the two differ |
| [`uninstall.md`](uninstall.md) | `uninstall.sh --scan` and teardown, and switching between the hosted, local, and plugin channels |
| [`DEPRECATION.md`](DEPRECATION.md) | Versioning and deprecation policy after v1.0 |
| [`../TERMS.md`](../TERMS.md) | Repository terms notice (license, platform terms, disclaimers) |
| [`../SECURITY.md`](../SECURITY.md) | Vulnerability disclosure |

## Contributing

| Doc | Contents |
|-----|----------|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Which guide fits a change, the sign-off, and the review for a regulated domain |
| [`contributing/development.md`](contributing/development.md) | Setup, checks, tests, the steps to add a capability, and commit and pull request rules |
| [`contributing/architecture.md`](contributing/architecture.md) | Map of the architecture: where a change goes, what it may import, and the known debt |
| [`contributing/conventions.md`](contributing/conventions.md) | Code rules with permanent IDs |
| [`contributing/adr/`](contributing/adr/README.md) | Architecture decision records |
| [`contributing/skills.md`](contributing/skills.md) | How to write, name, and maintain a skill |
| [`contributing/authoring.md`](contributing/authoring.md) | How the docs tree is organized and where a new doc goes |
| [`contributing/release.md`](contributing/release.md) | Versioning and the release procedure |
