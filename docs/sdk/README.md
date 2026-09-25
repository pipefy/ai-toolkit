# SDK documentation

This tree summarizes how to work with **`pipefy`**: the vendor GraphQL client, services, models, and queries shared by the MCP server and CLI.

## Using the library

- Import **`PipefyClient`** from `pipefy_sdk` and call facade methods; domain logic lives under `packages/sdk/src/pipefy_sdk/services/`.
- GraphQL operations are static `gql()` constants under `packages/sdk/src/pipefy_sdk/queries/` — do not build query strings dynamically.
- Pydantic input models live in `packages/sdk/src/pipefy_sdk/models/`.

For a short in-repo overview and dev commands, see **[`../../packages/sdk/README.md`](../../packages/sdk/README.md)**.

## Errors

`PipefyError` is the root of the API error types. Catch it to handle a failure
the Pipefy API reported:

```python
from pipefy_sdk import PipefyError, PipefyGraphQLError

try:
    await client.get_pipe(pipe_id)
except PipefyGraphQLError as exc:
    # exc.errors is the raw per-node error dict list, each with its own
    # message and extensions; read codes off that rather than the message text.
    codes = [(e.get("extensions") or {}).get("code") for e in exc.errors]
except PipefyError:
    # any other failure the API reported; see the carve-outs below
    ...
```

The hierarchy:

- **`PipefyError`** — root of the API error types below.
- **`PipefyAPIError`** — the API returned an error payload.
- **`PipefyGraphQLError`** — a GraphQL response carried `errors`. Subclasses `PipefyAPIError`, and carries the raw list on `.errors`. This is what most failures arrive as.
- **`AiAgentConfigureError`** — `create_ai_agent` created the agent, but the update that writes its instruction and behaviors failed. The agent exists, and it is disabled when `.disabled_at` (the create's `disabledAt`) is set. To recover, write its behaviors with `update_ai_agent(agent_uuid, ...)`, which keeps it disabled, then activate it with `toggle_ai_agent_status`. To discard it, call `delete_ai_agent`. The error message says the same. The update's own error is `__cause__`.

Catch the specific type before the root, since `except PipefyError` also catches
`PipefyGraphQLError` and would otherwise shadow it.

Other exported error types sit outside this root. Catch these by name:

- **`PortalPermissionError`** subclasses `ValueError`. That parentage is what
  maps a portal permission denial to CLI exit code 2 rather than 1.
- **`AttachmentUploadError`** and **`KnowledgeBaseDocumentUploadError`**
  subclass `Exception`.

Transport-level failures (connection refused, timeouts) surface as `gql`'s
`TransportError`, which the SDK does not wrap.

## AI agents

`create_ai_agent(CreateAiAgentInput(...))` creates the agent and then calls `update_ai_agent` to write its `instruction`, `behaviors`, and `data_source_ids`. The API disables a new agent until an update with an active behavior clears `disabledAt`, so the chained update omits `disabledAt` unless you set `disabled_at` to create the agent inactive. If that update fails, the method raises `AiAgentConfigureError` (see [Errors](#errors)).

`CreateAiAgentInput` and `UpdateAiAgentInput` prepare raw behavior dicts while they validate, the same way as the MCP tools:

- `template_params` (or `placeholders`) fill `{{name}}` in every string of the behavior, and `instruction_template` becomes `actionParams.aiBehaviorParams.instruction`. A `{{name}}` without a value is a `ValidationError`.
- Instruction token aliases (`{field:X}`, `{action:<uuid>}`, `%{<digits>}`, `{<digits>}`) become `%{field:…}` / `%{action:…}`, on the agent `instruction` and on each behavior's.

The prep applies to raw dicts only. A `BehaviorInput` instance passes through as it is, because `BehaviorInput` itself does no prep: pass raw dicts, or build each `BehaviorInput` from the output of `pipefy_sdk.behavior_placeholders.expand_behavior_placeholders`.

## Pre-write validation

Two read-only `PipefyClient` methods dry-run a write before you make it. They have the same names and parameters as the MCP tools, and they never persist anything:

- **`validate_ai_agent_behaviors(pipe_id, behaviors, *, strict_unknown_action_types=True, data_source_ids=None)`** checks a behavior list against the pipe's fields, phases, relations, phase transitions, and knowledge bases. Call it before `create_ai_agent` / `update_ai_agent`.
- **`validate_ai_automation_prompt(pipe_id, prompt, field_ids, event_id=None)`** checks the prompt's `%{internal_id}` references, the output `field_ids`, the optional trigger, and whether AI is enabled for the pipe and the organization. Call it before `create_ai_automation`.

Both return a dict. `valid` is true only when `problems` is empty, and `warnings` holds non-blocking notices. The agent result adds a `message`; the prompt result adds a `field_map` of the referenced field IDs to their labels. A failed pipe read sets `success` to false instead of raising: the agent result then gives the reason in `problems`, and the prompt result carries only `success`, `valid`, and `error`.

## Methods named after the MCP tools

Five `PipefyClient` methods share names and parameters with MCP tools so an agent that builds its tools from the client can call the same operations. MCP and CLI call these methods; MCP `fill_card_phase_fields` still owns elicitation when a form can be shown and the caller did not skip it.

- **`get_ai_automation(automation_id)`** delegates to `get_automation`. Returns the rule record, or `None` when the id is missing.
- **`get_ai_automations(pipe_id, organization_id=None, *, first=None, after=None)`** calls `get_automations`, then keeps only `generate_with_ai` rows in `nodes` (`pipefy_sdk.ai_preflight.filter_ai_automation_summaries`). `totalCount` and `pageInfo` still describe the mixed page.
- **`delete_ai_automation(automation_id)`** delegates to `delete_automation`. Same result as that method.
- **`remove_member_from_pipe(pipe_id, user_ids)`** runs the mutation, then reads members back. Returns `{"data": <mutation result>, "warning": <str or None>}`. `warning` is `None` when every requested user is gone, or when the members read fails. A non-numeric `pipe_id` raises `ValueError` before that read. Use the singular when the caller wants confirmation that the removal took effect. **`remove_members_from_pipe`** fetches the pipe before mutating and may fetch members when resolving numeric user ids; it skips post-mutation verification. The plural is not deprecated.
- **`fill_card_phase_fields(card_id, phase_id, fields, *, required_fields_only=False)`** reads `get_phase_fields` once, filters `fields` to editable ids, and does not write a field the phase does not expose. When nothing survives: `success`, `message`, `phase_id`, `phase_name`, `skipped_field_ids`. When a write runs: the `update_card` dict, plus `skipped_field_ids` only when a key was dropped.

Skills cite `get_pipe` (labels are on the pipe) and `get_pipe_reports` (the reports connection). There is no `PipefyClient.get_labels` or `PipefyClient.get_pipe_report`; MCP keeps those names as aliases, and projection stays in MCP and CLI.

## Configuration

OAuth and endpoint variables are documented in **[`../config.md`](../config.md)** and **[`../../.env.example`](../../.env.example)**. Integration tests use `@pytest.mark.integration` and the same `PIPEFY_*` keys from local **`.env`** (e.g. `PIPEFY_PORTAL_ORG_UUID` for portal live tests). Unit tests use fictional ids in **[`../../packages/sdk/tests/_shared/fixture_ids.py`](../../packages/sdk/tests/_shared/fixture_ids.py)** — not production org UUIDs.

## Relationship to MCP and CLI

The SDK has **no** MCP or Typer dependencies. `pipefy-mcp-server` and `pipefy-cli` both depend on `pipefy` only. Feature parity between MCP tools and CLI commands is tracked in **[`../parity.md`](../parity.md)**.
