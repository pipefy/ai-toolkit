# CLI reference — pipefy-automations

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

| Operation | CLI |
|---|---|
| `get_automations` | `pipefy automation list` |
| `get_automation` | `pipefy automation get` |
| `create_automation` | `pipefy automation create` |
| `update_automation` | `pipefy automation update` |
| `delete_automation` | `pipefy automation delete` |
| `simulate_automation` | `pipefy automation simulate` |
| `get_automation_events` | `pipefy automation events list` |
| `get_automation_event_attributes` | `pipefy automation event-attributes` |
| `get_automation_actions` | `pipefy automation actions list` |
| `create_send_task_automation` | `pipefy automation send-task create` |

| Operation | CLI |
|---|---|
| `get_ai_automations` | `pipefy ai-automation list` |
| `get_ai_automation` | `pipefy ai-automation get` |
| `create_ai_automation` | `pipefy ai-automation create` |
| `update_ai_automation` | `pipefy ai-automation update` |
| `delete_ai_automation` | `pipefy ai-automation delete` |
| `validate_ai_automation_prompt` | `pipefy ai-automation validate-prompt` |

Destructive deletes require `--yes`; there is no confirmation token.

Use `--condition` on `pipefy automation create` and `pipefy automation update` for the shared condition payload.
