# What the toolkit connects to and installs

This page lists the hosts the toolkit calls and the files an install or `pipefy auth login` writes.

Calls to Pipefy go to the hosts below and to storage URLs that Pipefy issues. Installation also contacts the hosts under [What an install adds to your machine](#what-an-install-adds-to-your-machine). When you pass a URL to download, the request goes to that URL.

## Hosts

- **`app.pipefy.com`**
  - You can set another host with `PIPEFY_BASE_URL`.
  - `api.pipefy.com` answers the same way.
  - This host serves Pipefy's GraphQL API.
  - Calls use the permissions of the signed-in user, the service account, or `PIPEFY_TOKEN`.
  - The `pipefy-api-fallback` skill calls this API with `curl`.
  - The skill runs only after the MCP tools and introspection fail.
  - Before the call, the agent tells you which `PIPEFY_*` variable it will read.
  - GraphQL requests carry `User-Agent: pipefy-sdk/<version> (<surface>)`.
  - They also carry `X-Client-Name` and `X-Client-Version`.
  - The MCP server also reports where it runs, as `(mcp; local)` or `(mcp; hosted)`.
  - It also sends `X-Client-Deployment`.
- **`mcp.pipefy.com`**
  - This host is Pipefy's hosted MCP server.
  - The Hosted MCP path and both plugins use it.
  - Sign-in is browser OAuth.
  - The public client id is `pipefy-mcp`.
- **`signin.pipefy.com`**
  - You can set another issuer with `PIPEFY_AUTH_URL`.
  - `pipefy auth login` opens your browser.
  - The redirect returns to `127.0.0.1`.
  - The CLI and the local MCP server refresh the session here.
  - `pipefy auth logout` revokes the session here.
  - These requests carry `User-Agent: pipefy-auth/<version>`.
  - They also carry `X-Client-Name: auth` and `X-Client-Version`.
- **`ipaas.pipefy.com`**
  - You can set another host with `PIPEFY_IPAAS_URL`.
  - This host serves the iPaaS (Advanced Automations) tools.

The toolkit sends no other telemetry.

## File transfers

- Attachment uploads go to presigned storage URLs that Pipefy issues.
- Knowledge-base uploads go to those same URLs.
- The tool downloads a `file_url` you pass.
- On the hosted path, Pipefy's server downloads that URL.
- Report exports and job exports download from signed Pipefy links.

## What an install adds to your machine

- **Quick-install script** (macOS and Linux)
  - The script asks before it installs [`uv`](https://docs.astral.sh/uv/) from `astral.sh` when uv is missing.
  - The uv installer may add `~/.local/bin` to your shell profile.
  - The script reads the newest non-alpha release from the GitHub API.
  - With `--version`, it reads that tag instead.
  - It runs `uv tool install` for `pipefy-cli` and `pipefy-mcp-server`.
  - It uses that release's wheels, including `pipefy`, `pipefy-auth`, and `pipefy-infra`.
  - Third-party dependencies come from PyPI.
  - uv may download a Python 3.11+ interpreter when it finds none.
  - With `--client cursor`, `claude-desktop`, or `codex`, it writes a `pipefy` entry into that client's config.
  - It skips the write when a `pipefy` entry already exists.
  - It records the run in `~/.local/state/pipefy/install-receipt` for `uninstall.sh`.
  - It asks before it runs `npx skills add`.
  - `--no-skills` skips that step.
- **`/pipefy:install`** (Claude Code plugin)
  - The command asks before it runs `uv tool install --force pipefy-cli` from PyPI.
- **Scan command** ([`pipefy-toolkit-setup`](../plugins/pipefy/skills/pipefy-toolkit-setup/SKILL.md) and [`uninstall.md`](uninstall.md))
  - It downloads `uninstall.sh` from this repository on GitHub.
  - It runs that script with `--scan`.
  - `--scan` reads every source listed under [Scope](uninstall.md#scope).
  - The OS keychain is one of those sources.
  - It prints what it found.
  - It changes nothing.
- **`npx skills add`**
  - It downloads the third-party `skills` tool from npm.
  - It downloads this repository from GitHub.
  - It installs the skills for your agent.
  - The `skills` tool sends usage telemetry to `skills.sh`.
  - It skips that telemetry when the environment contains `DISABLE_TELEMETRY` or `DO_NOT_TRACK`.
- **`pipefy auth login`**
  - It stores the session through Python `keyring`, normally in the OS keychain.
  - With `PIPEFY_KEYCHAIN_BACKEND=file`, the session is a plaintext file.
  - That file is `keyring.cfg` in the Pipefy config folder.
  - When `keyring` finds no OS keychain, it can store the session in its own plaintext file.
  - That file is `python_keyring/keyring_pass.cfg` in the user data folder.
  - On Linux, that folder is `~/.local/share`.
  - Login and token refresh also keep a lock file, `refresh.lock`.
  - The lock file is in the Pipefy config folder: `~/.config/pipefy`, or `%APPDATA%\pipefy` on Windows.

## Related

- Install steps: [`install.md`](install.md)
- Removal and switching paths: [`uninstall.md`](uninstall.md)
- Environment variables: [`config.md`](config.md)
- CLI sign-in: [`cli/auth.md`](cli/auth.md)
