# Quickstart

In this tutorial, you connect Claude Code to Pipefy and ask your first questions about your own pipes. You install nothing besides Claude Code: the MCP server runs on Pipefy's infrastructure, and you sign in through your browser. The whole run takes about five minutes.

This tutorial follows one path, the hosted MCP server in Claude Code, because it is the recommended client and needs no local Python. [`install.md`](install.md) covers every other path.

## Before you start

You need:

- Claude Code, installed and signed in.
- A Pipefy account with access to at least one pipe. The agent sees what your account sees, and nothing more.

If another Pipefy MCP server is already registered on this machine, remove it first, because a second registration shadows this one. [Before you install](install.md#before-you-install) shows how to check.

## Step 1. Register the hosted server

Run this command in a terminal:

```bash
claude mcp add --transport http --scope user --client-id pipefy-mcp pipefy https://mcp.pipefy.com/mcp
```

Claude Code now knows a server named `pipefy`, for every project on this machine.

## Step 2. Sign in

1. Start Claude Code with `claude`.
2. Type `/mcp`, select `pipefy`, and follow the browser sign-in.
3. Sign in to Pipefy in the browser, and return to Claude Code.

If `/mcp` shows `pipefy` as *Needs authentication*, run `claude mcp login pipefy` and sign in again.

## Step 3. Ask about your pipes

Type this prompt in Claude Code:

```text
List the Pipefy pipes I can see.
```

The agent calls the `search_pipes` tool and answers with the pipes in each organization your account belongs to. Claude Code asks for permission before the first call to each tool. Allow it.

## Step 4. Look inside one pipe

Pick a pipe name from the answer, and ask about its cards:

```text
Show the cards in the "<pipe name>" pipe, grouped by phase.
```

The agent reads the pipe and its cards with tools such as `get_pipe` and `get_cards`, and it groups them for you. You can now ask follow-up questions in plain words, such as which cards are late or who owns each one.

The tools can also change data, for example by creating or moving a card. A tool that deletes something asks you to confirm first, and [Destructive operations](mcp/tools/cross-cutting.md#destructive-operations) explains how.

## Where to go next

- Add the workflow playbooks, so the agent follows tested procedures for common jobs: `npx skills add pipefy/ai-toolkit`. [`skills/README.md`](../skills/README.md) lists them.
- Add the CLI and the `/pipefy:*` slash commands with the [Claude Code plugin](install.md#2-claude-code-plugin).
- Browse what the tools do in the [MCP tool reference](mcp/README.md).
