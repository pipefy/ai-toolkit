# pipefy-cli

Command-line interface for [Pipefy](https://www.pipefy.com/). The `pipefy` command reads and changes pipes, cards, tables, automations, and more, for people in a terminal and for scripts. It offers the same operations as the Pipefy MCP server, and it calls Pipefy through the [`pipefy`](https://pypi.org/project/pipefy/) SDK.

## Install

```sh
uv tool install pipefy-cli
pipefy auth login
```

## Example

```bash
pipefy pipe list --name Hiring --json
pipefy card list --pipe 67890
```

Every command prints a Rich table by default. Add `--json` for machine-readable output, and run `pipefy <command> --help` for its arguments.

## Documentation

- [Install guide](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md#4-cli-only): every install option, including shell completion.
- [CLI guides](https://github.com/pipefy/ai-toolkit/blob/main/docs/cli/README.md): sign-in and credentials, and the introspect-then-execute flow.
- [MCP and CLI parity](https://github.com/pipefy/ai-toolkit/blob/main/docs/parity.md): which command matches each MCP tool.
- [Configuration](https://github.com/pipefy/ai-toolkit/blob/main/docs/config.md): every `PIPEFY_*` variable and `config.toml`.
- [Troubleshooting](https://github.com/pipefy/ai-toolkit/blob/main/docs/troubleshooting.md): common failures by symptom.

The source, the issue tracker, and the full documentation index live in the [`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit) repository.
