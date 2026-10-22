# MCP reference — pipefy-ai-agents

## Preflight and generated fields

`create_ai_agent` / `update_ai_agent` do not auto-preflight. Call `validate_ai_agent_behaviors` before writing. Knowledge-base create/update tools do not auto-probe: call `validate_knowledge_base_access` first.

On a behavior save failure, the MCP tool auto-validates the payload. When pre-flight finds no field, phase, relation, or actionType problems, `RECORD_NOT_SAVED` does not name the cause. The same message covers an unknown `event_id`, a `human_validation` action without `emails` and `title`, and other payload errors. Rule those out before you conclude the pipe does not support AI agent behaviors. A rejected update is not rolled back. Call `get_ai_agent` to see what is left, fix the payload, and send the full list again.

## Hosted and local profiles

Agent reads (`get_ai_agents`, `get_ai_agent`, `validate_ai_agent_behaviors`) and writes (create/update/delete/toggle) are remote-safe under `profile=remote`.

`create_ai_knowledge_base_document`, `create_llm_provider`, and `update_llm_provider` require local files and are withheld on the hosted server.

- Provider create/update require `configuration_file_path`: a local JSON file, never inline credentials. Its `provider` key selects the vendor; secrets are never logged or returned. Hosted callers can attach an existing provider from `get_llm_providers` via `providerId` / `systemProviderId`, or create the provider through the CLI / Quick-install path.
- PDF creation uses `create_ai_knowledge_base_document(pipe_uuid, name, description, file_path)`. `file_path` belongs to the MCP server's machine. There is no hosted-safe file source: use a plain-text knowledge base on hosted, or create the PDF source through the CLI / Quick-install path. Local uploads enforce `.pdf` and 20 MiB before uploading; indexing is asynchronous.

## Enablement responses

Create/update responses use `disabled_at` / `active`; prefer these when present. A successful response with `agent_uuid` still requires checking enablement: null `disabled_at` means active. A partial-failure shell is often disabled; its envelope carries `disabled_at`.

On a partial create failure, the MCP envelope carries `agent_uuid`. Use it to
recover the existing shell through the full `update_ai_agent` payload in the skill.

`get_ai_agent` instead exposes agent `disabledAt`, not write-envelope `disabled_at` / `active`. Null means active. Re-read when the write response is unclear; `behaviors[].active` is never agent enablement. An agent with no active behavior is disabled by the API regardless of enablement flags.

## Destructive deletes

The first call to `delete_ai_agent` or a knowledge-base delete returns a preview. Show it to the user and obtain approval, then repeat with `confirm=true` and the preview's `confirmation_token`. Never skip the preview.
