# MCP reference — pipefy-ai-agents

## Preflight and generated fields

`create_ai_agent` / `update_ai_agent` do not auto-preflight. Call `validate_ai_agent_behaviors` before writing. Knowledge-base create/update tools do not auto-probe: call `validate_knowledge_base_access` first.

The MCP tool auto-injects `referenceId` and `%{action:<uuid>}` placeholders; do not generate these yourself. On a behavior save failure, it auto-validates the payload. If structurally correct, `RECORD_NOT_SAVED` indicates a pipe-level restriction rather than a payload problem.

## Hosted and local profiles

Agent reads (`get_ai_agents`, `get_ai_agent`, `validate_ai_agent_behaviors`) and writes (create/update/delete/toggle) are remote-safe under `profile=remote`.

`create_ai_knowledge_base_document`, `create_llm_provider`, and `update_llm_provider` require local files and are withheld on the hosted server.

- Provider create/update require `configuration_file_path`: a local JSON file, never inline credentials. Its `provider` key selects the vendor; secrets are never logged or returned. Hosted callers can attach an existing provider from `get_llm_providers` via `providerId` / `systemProviderId`, or create the provider through the CLI / Quick-install path.
- PDF creation uses `create_ai_knowledge_base_document(pipe_uuid, name, description, file_path)`. `file_path` belongs to the MCP server's machine. There is no hosted-safe file source: use a plain-text knowledge base on hosted, or create the PDF source through the CLI / Quick-install path. Local uploads enforce `.pdf` and 20 MiB before uploading; indexing is asynchronous.

## Enablement responses

Create/update responses use `disabled_at` / `active`; prefer these when present. A successful response with `agent_uuid` still requires checking enablement: null `disabled_at` means active. A partial-failure shell is often disabled; its envelope carries `disabled_at`.

`get_ai_agent` instead exposes agent `disabledAt`, not write-envelope `disabled_at` / `active`. Null means active. Re-read when the write response is unclear; `behaviors[].active` is never agent enablement. An agent with no active behavior is disabled by the API regardless of enablement flags.

## Destructive deletes

The first call to `delete_ai_agent` or a knowledge-base delete returns a preview. Show it to the user and obtain approval, then repeat with `confirm=true` and the preview's `confirmation_token`. Never skip the preview.
