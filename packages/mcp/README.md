# pipefy-mcp-server

MCP server for [Pipefy](https://www.pipefy.com/). It lets an AI agent in Cursor, Claude Desktop, Claude Code, Codex, or any MCP client read and change pipes, cards, tables, automations, and more, with the permissions of the account that signs in. It calls Pipefy through the [`pipefy`](https://pypi.org/project/pipefy/) SDK.

## Install

```sh
uvx pipefy-mcp-server
```

An MCP client starts the server for you. Pipefy also hosts it, and the [install guide](https://github.com/pipefy/ai-toolkit/blob/main/docs/install.md) shows how to connect each client to the hosted server or to a local one.

## Documentation

- [Quickstart](https://github.com/pipefy/ai-toolkit/blob/main/docs/quickstart.md): connect Claude Code and ask a first question.
- [MCP tool reference](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/README.md): what each tool does, and the behavior every tool shares.
- [Configuration](https://github.com/pipefy/ai-toolkit/blob/main/docs/config.md): every `PIPEFY_*` variable and `config.toml`.
- [Troubleshooting](https://github.com/pipefy/ai-toolkit/blob/main/docs/troubleshooting.md): common failures by symptom.

The source, the issue tracker, and the full documentation index live in the [`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit) repository.
