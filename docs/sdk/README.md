# SDK documentation

`pipefy` is the Python SDK for Pipefy's GraphQL API. The MCP server and the CLI call Pipefy through it, and your own program can call it too. The distribution is named `pipefy`, and the import module is `pipefy_sdk`.

## Make a first call

1. Add the SDK and the auth helpers to your project:

   ```sh
   uv add pipefy pipefy-auth
   ```

2. Set `PIPEFY_TOKEN` to a Pipefy bearer token. [`../config.md`](../config.md) lists the other ways to sign in, such as a service account.
3. Build a client and call a method. Every method is a coroutine, and a read returns the GraphQL `data` object as a `dict`:

   ```python
   import asyncio
   import os

   from pipefy_auth import StaticBearerAuth
   from pipefy_sdk import PipefyClient, PipefySettings


   async def main() -> None:
       client = PipefyClient(
           PipefySettings(), auth=StaticBearerAuth(os.environ["PIPEFY_TOKEN"])
       )
       result = await client.get_pipe(pipe_id="<pipe id>")
       print(result["pipe"]["name"])


   asyncio.run(main())
   ```

`PipefySettings()` reads the `PIPEFY_*` variables and `config.toml`, so the same configuration serves the SDK, the CLI, and the MCP server.

## Handle errors

Catch the specific error type before its root, because `except PipefyError` also catches `PipefyGraphQLError`:

```python
from pipefy_sdk import PipefyError, PipefyGraphQLError

try:
    await client.get_pipe(pipe_id)
except PipefyGraphQLError as exc:
    # Read codes from extensions: the message text is not stable.
    codes = [(e.get("extensions") or {}).get("code") for e in exc.errors]
except PipefyError:
    ...
```

[Error types](reference.md#error-types) lists every type, including the ones outside the `PipefyError` root.

## Skills in the package

The `pipefy` wheel includes the versioned skill catalog. After installing the wheel, each skill is available at `<skill-name>/SKILL.md` under the directory returned by `pipefy_sdk.skills.directory()`. Its `references/` files use the same relative paths as the source catalog. Use `parse_skill_surfaces()` to select skills for your client; an omitted `metadata.surfaces` field means SDK, MCP, and CLI all apply.

```python
from pipefy_sdk import skills

for skill_file in skills.directory().glob("*/SKILL.md"):
    if "sdk" in skills.parse_skill_surfaces(skill_file.read_text(), skill_file.parent.name):
        print(skill_file)
```

## Where to go next

- [`reference.md`](reference.md): the error types, AI agent creation, pre-write validation, and the methods named after MCP tools.
- [`../parity.md`](../parity.md): which CLI command and MCP tool match each operation.
- [`../config.md`](../config.md): every `PIPEFY_*` variable and `config.toml`.
