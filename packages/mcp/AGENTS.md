# MCP package rules

Scoped to `packages/mcp/`. Repo-wide rules are in [`../../AGENTS.md`](../../AGENTS.md), and the code rules are in [`conventions.md`](../../docs/contributing/conventions.md). [`architecture.md`](../../docs/contributing/architecture.md) explains this package: its blocks under `MCP server`, the profiles under `Identity lifetime`, the tool listing under `Tool surface`, and the log under `What reaches a log`. [`docs/config.md`](../../docs/config.md) is the reference for every startup flag and variable.

Run `uv run lint-imports` after you change an import. Import-linter holds this package's layer order.

## Distribution model

Under the `local` profile, the server runs in the user's environment as a
subprocess of the agent runtime (Claude Code, Claude Desktop, etc.), with the
filesystem and network access that the user already has. For that profile, the
trust boundary is the user. Under the `remote` profile, the server runs as a
multi-user HTTP service, and the trust boundary is each caller's bearer.

Implications for tool design:

- Local filesystem inputs (`file_path`) are first-class under the `local`
  profile. There is no path-traversal threat surface beyond what the user can
  already access, and a local `file_path` needs no SSRF guard, redirect cap, or
  download size limit. The `remote` profile rejects a `file_path` input (see
  "Exposure vs input restriction").
- A **server-side URL fetch is different**: when the server (not the user) makes
  the request, those defenses apply under every profile. The `file_url`
  attachment source carries them in the SDK (`HttpxUrlDownloader`: HTTPS +
  public-IP gate, 80/443 ports, connect-time re-validation, redirect cap, size
  cap), and any future URL ingestion should do the same.

Tool exposure under the `remote` profile is **default-deny**: only tools
explicitly marked remote-safe are registered, and everything else is withheld.
The marker is described below.

## Adding a tool

- Give the tool function a `ctx: Context` parameter, and start its body with `client = get_pipefy_client(ctx)`. Do not pass a client through `register`. A client captured at registration acts as one caller for every request, and under the `remote` profile each request acts as its own caller.
- Register the tool at construction, through `_register_pipefy_tools` in `server.py`, never inside the lifespan.
- Add its name to `PIPEFY_TOOL_NAMES` in `tools/registry.py`, and to one domain in `DOMAINS` in `tools/toolsets.py`. `tests/tools/test_toolsets.py` fails the build for a tool with no domain.
- Declare the tool's effect in its annotations, and add no confirmation gate. `TOOL-2` in [`conventions.md`](../../docs/contributing/conventions.md) is the rule.

## Marking a tool remote-safe

Under the `remote` profile, the server lists only the tools whose registration carries `meta=REMOTE`, and it withholds every other tool. Under `local`, the marker has no effect.

```python
from pipefy_mcp.tools.remote_profile import REMOTE

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True), meta=REMOTE)
async def get_organization(...): ...
```

Mark a tool remote-safe only when all of these hold:

- It reaches the API with the request-scoped bearer, and the API's permissions govern it completely.
- It reads no local file.
- It reads no process-wide setting to decide something about the caller (see "Settings in tool code").

A write must also meet three more criteria:

- **Authorization is the API's, and only the API's.** A remote-safe write carries no client-side permission check; it relies entirely on the backend rejecting a caller who lacks the permission (org-admin to create or delete a service account, pipe-admin to add a member). Mark a write remote-safe only once its permission is enforced downstream for the request-scoped bearer — never infer authorization from the tool merely being reachable.
- **A returned secret must never reach a log.** A returned secret is safe only because no log line holds an argument value or a response body, as `What reaches a log` in [`architecture.md`](../../docs/contributing/architecture.md#what-reaches-a-log) states. A write that would need its secret logged, echoed in an error, or stored on the server is not remote-safe.
- **The confirmation gate is not an authorization boundary.** A new tool adds no gate. It declares its effect instead, which is `TOOL-2` in [`docs/contributing/conventions.md`](../../docs/contributing/conventions.md). Nearly every existing destructive tool still gates through `check_destructive_confirmation`: the first call returns a preview and a `confirmation_token`, and only a second call with `confirm=True` and that token mutates. The token binds one tool, one resource identity, and one caller. A hosted deployment verifies it statelessly with an HMAC derived from the bearer, so a token can be replayed within 300 seconds. A client that auto-approves tool calls can send both calls with no person involved, so the gate proves only that the preview reached the transcript. The gate is debt, and the `QR-25` entry in [Risks and technical debt](../../docs/contributing/architecture.md#risks-and-technical-debt) carries it. A destructive write is remote-safe when the API authorizes it and its effect is stated plainly to the caller.

Marking a tool shifts the `REMOTE_SEED` drift guard in `tests/tools/test_remote_profile.py`, so the change always gets a review.

Restrict an input inside a remote-safe tool at call time, with `is_remote_profile(ctx)` from `tools/tool_context.py`. Do not use the marker for it, and do not read the module-level settings singleton, because embedders and tests build a runtime from explicit settings that the singleton does not see. Restrict an input only where it resolves from the deployment's own environment or disk: `create_ipaas_connection` rejects a `{"$env": ...}` reference, and the attachment tools reject `file_path`. A write whose every input is a per-request value needs no restriction.

Do not add a destructive keyword for `call_ipaas_tool`. The set is closed: `delete`, `remove`, `destroy`, `drop`, `uninstall`, `revoke`.

`execute_graphql` is remote-safe, and its mutations use the same confirmation token as the dedicated deletes. Do not set `destructiveHint` on it. A token can be replayed while it lives, so a mutation that is not idempotent can run twice. Use a dedicated tool for that write.

Nothing limits what one caller costs another yet, which `Risks and technical debt` in [`architecture.md`](../../docs/contributing/architecture.md#risks-and-technical-debt) carries. Until it does, add a new kind of remote write only where the API's permissions bound what it can reach.

## Settings in tool code

- Never import `pipefy_mcp.settings` from code that a tool reaches, directly or through a helper. `uv run lint-imports` fails on that import. An exception needs a review that confirms the setting answers a question about the deployment, never about the caller. `Identity lifetime` in [`architecture.md`](../../docs/contributing/architecture.md#identity-lifetime) explains why.
- Take every per-caller value from the request.

## Tool-call middleware

`core/tool_middleware.py` explains the chain. When you write a middleware:

- Register a built-in middleware in `default_tool_middlewares` in `server.py`, and pass any other one to `build_pipefy_mcp_server` through `extra_tool_middlewares`. Do not reach into MCP SDK internals.
- To stop a call, return `short_circuit_error(ctx, ...)` without awaiting `call_next`. It marks the result `isError=True` and shapes it for the negotiated protocol revision, which a hand-built result skips.
- Read a result with `result_is_error(result)`, never `result.is_error`. A real call returns a wire dict, on which `is_error` reads `False` for every failure. A test fixture that stands in for a real call uses that dict shape.
- Rewrite arguments through `replace(ctx, params=...)`, never by mutating `ctx.arguments`, which the dispatcher shares.
- Never log a bearer or an argument value. Use `ctx.argument_keys`, which is bounded and holds no values.
- Write HTTP middleware as pure ASGI. Starlette's `BaseHTTPMiddleware` buffers the response body, which breaks Streamable HTTP streams.
- A host app that mounts the server's HTTP app enters `app.session_manager.run()` in its own lifespan, because Starlette does not run a mounted app's lifespan.
- `mcp[cli]` is pinned to `2.0.*` because of the provisional middleware list and the `Tool.run` patch in `tools/validation_envelope.py`. Before you widen the pin, re-test both.
