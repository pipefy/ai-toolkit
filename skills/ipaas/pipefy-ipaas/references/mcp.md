# MCP controls and examples

- **iPaaS OAuth client configured on this MCP server.** If `PIPEFY_IPAAS_OAUTH_CLIENT_ID` is blank, every tool returns a "disabled on this server" message (server-config disable, distinct from the org-level one).

- Under `profile=remote`, `$env` secret references in arguments are rejected.

Destructive catalog **calls** need the MCP confirmation token when the call is judged destructive, in this order: catalog `annotations.destructiveHint` true, then `arguments.operation` needle-equality after strip and casefold against `delete` / `remove` / `destroy` / `drop` / `uninstall` / `revoke`, then annotation false stops (do not fall through to name needles), else the catalog name is matched as a substring against those needles. A catalog miss (the name was not on the page this server read) is unclassifiable and takes the two-step as well. Mixed manage with `operation=DELETE` is two-step; `ADD` / `UPDATE` stay one-shot unless a `confirmation_token` is supplied, which routes any call through the guard. Show the preview to the user and get their approval, then call again with `confirm=true`, the preview's `confirmation_token`, and the same `arguments` as step 1 (`operation` may differ in case or surrounding whitespace; any other change returns a fresh preview). Do not invent extra needles.

Every `call_ipaas_tool` has a ~120s network budget (most relevant here for long runs).

To keep the secret out of the conversation, set it in the server environment and reference it as `{"$env": "PIPEFY_IPAAS_CONNECTION_<NAME>"}` (local servers only; rejected under `profile=remote`).

- **Server-config iPaaS disabled.** When `PIPEFY_IPAAS_OAUTH_CLIENT_ID` is blank, tools return "disabled on this server" — restore the default or set a client id.

- **`$env` rejected under remote profile.** Secret references are local-only. Pass credentials through `create_ipaas_connection`, not inline `$env`.

- **Accidental destruction.** A destructive catalog call returns a preview with `confirmation_token`. Show the preview to the user and get their approval, then call again with `confirm=true` and the preview's `confirmation_token`. Judgement order: annotation `true`, then `arguments.operation` needle-equality, then annotation `false` stops (a false annotation does **not** fall through to name needles), else name substring needles. Mixed `operation=DELETE` is two-step; `ADD`/`UPDATE` are not. Prefer updating a step over deleting it.

```text
get_ipaas_tools pipe_id=<pipe_id>
get_ipaas_tools pipe_id=<pipe_id> tool_name=<flow-builder entry>
```

This workflow exposes 4 MCP tools.

The MCP server exposes it through **4 meta-tools**: the flow-builder verbs are catalog entries you discover per pipe and invoke through `call_ipaas_tool`, never a fixed tool list.
