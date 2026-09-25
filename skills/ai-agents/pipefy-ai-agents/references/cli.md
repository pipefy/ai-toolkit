# CLI reference — pipefy-ai-agents

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

| Operation | CLI |
|---|---|
| `get_ai_agents` | `pipefy agent list` |
| `get_ai_agent` | `pipefy agent get` |
| `create_ai_agent` | `pipefy agent create` |
| `update_ai_agent` | `pipefy agent update` |
| `delete_ai_agent` | `pipefy agent delete` |
| `toggle_ai_agent_status` | `pipefy agent toggle` |
| `validate_ai_agent_behaviors` | `pipefy agent validate-behaviors` |

| Operation | CLI |
|---|---|
| `get_ai_knowledge_bases` | `pipefy kb list` |
| `get_ai_knowledge_base_plain_text` | `pipefy kb plain-text get` |
| `create_ai_knowledge_base_plain_text` | `pipefy kb plain-text create` |
| `update_ai_knowledge_base_plain_text` | `pipefy kb plain-text update` |
| `delete_ai_knowledge_base_plain_text` | `pipefy kb plain-text delete` |
| `get_ai_knowledge_base_document` | `pipefy kb document get` |
| `create_ai_knowledge_base_document` | `pipefy kb document create` |
| `update_ai_knowledge_base_document` | `pipefy kb document update` |
| `delete_ai_knowledge_base_document` | `pipefy kb document delete` |
| `get_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup get` |
| `create_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup create` |
| `update_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup update` |
| `delete_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup delete` |
| `validate_knowledge_base_access` | `pipefy kb validate-access` |

## Write controls and flags

Destructive deletes require `--yes`; there is no confirmation token.

`pipefy agent create` and `pipefy agent update` require `--pipe` (numeric pipe ID). They automatically run behavior preflight: `problems` block the write and `warnings` appear under `preflight`.

- Common options: `--repo-uuid`, `--name`, `--instruction`, `--behaviors` (JSON array), and `--data-sources` (JSON array).
- Create: `--active` / `--inactive`. Update has no status flags; use `pipefy agent toggle --active` / `--inactive`.
- Update: `pipefy agent update --disabled-at` can carry the `disabledAt` timestamp read with `pipefy agent get`, avoiding a preserve re-read.
- `agent validate-behaviors` takes repeatable `--data-source-id` instead of `--data-sources`.
- `--strict` (default) / `--no-strict` on `agent validate-behaviors`, `agent create`, and `agent update` control unknown action types.

## Providers and knowledge bases

`pipefy ai-provider list`, `pipefy ai-provider create`, `update`, `delete`, `set-active-status`, `default set`, and `default reset` manage providers. Create/update use a local JSON configuration file, never inline credentials. Its `provider` key selects the vendor; secrets are never logged or returned.

Knowledge-base create/update commands automatically gate on `pipefy kb validate-access`; this proves read access only, not write entitlement. Use `pipefy kb list` to obtain IDs for attachment.

Create a PDF with `pipefy kb document create --file …`; `.pdf` and 20 MiB are enforced client-side. Data lookup example:

```bash
pipefy kb data-lookup create --source-repo-id … --output-fields '[…]' --conditions '[…]'
```
