# Documentation index

Guides for the **[pipefy/ai-toolkit](https://github.com/pipefy/ai-toolkit)** monorepo, which ships the MCP server `pipefy-mcp-server`, the CLI `pipefy-cli`, the SDK `pipefy`, and the agent skills.

## Using the toolkit

The pages for users sort into four kinds, so you can pick by what you need right now. A tutorial teaches by doing, a how-to guide finishes one task, a reference states facts, and an explanation says why.

### Tutorials

| Doc | Contents |
|-----|----------|
| [`quickstart.md`](quickstart.md) | Start here: connect Claude Code to Pipefy and ask a first question |

### How-to guides

| Doc | Contents |
|-----|----------|
| [`install.md`](install.md) | Choose an install path, and wire each MCP client |
| [`cli/auth.md`](cli/auth.md) | Sign in with the CLI, and fix a failed sign-in |
| [`cli/self-healing.md`](cli/self-healing.md) | Discover a GraphQL operation with `pipefy introspect`, then run it |
| [`sdk/`](sdk/README.md) | Make a first call, handle SDK errors, and read the skill catalog from code |
| [`uninstall.md`](uninstall.md) | Scan and tear down an install, and switch between the hosted, local, and plugin channels |
| [`troubleshooting.md`](troubleshooting.md) | Fix a common failure, found by its symptom |

### Reference

| Doc | Contents |
|-----|----------|
| [`mcp/reference.md`](mcp/reference.md) | Every MCP tool with its flags and parameters, generated from the code |
| [`cli/reference.md`](cli/reference.md) | Every CLI command with its arguments and options, generated from the code |
| [`sdk/reference.md`](sdk/reference.md) | SDK error types, and the client methods whose behavior goes beyond their docstrings |
| [`cli/auth-reference.md`](cli/auth-reference.md) | CLI credential precedence, the `pipefy auth` commands, and session behavior |
| [`cli/`](cli/README.md) | CLI output, confirmation, and configuration conventions |
| [`config.md`](config.md) | `PIPEFY_*` environment variables, `config.toml` schema and path, precedence chain |
| [`parity.md`](parity.md) | Which CLI command matches each MCP tool, and where the two differ |
| [`DEPRECATION.md`](DEPRECATION.md) | What a version number promises: semantic versioning and the deprecation window |

### Explanation

| Doc | Contents |
|-----|----------|
| [`mcp/`](mcp/README.md) | How the MCP tools behave by area, what every tool shares, and how to choose a tool surface |
| [`contributing/architecture.md`](contributing/architecture.md) | How the toolkit is built, and why |

### Policies

| Doc | Contents |
|-----|----------|
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
| [`contributing/release.md`](contributing/release.md) | The release tracks and the procedure to cut a release |

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/README.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/README.md).
