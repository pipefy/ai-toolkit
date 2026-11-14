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

`pipefy automation list` and `pipefy ai-automation list` expose `totalCount`
and `pageInfo.hasNextPage`; use the next cursor until no page remains.

Use `--condition` on `pipefy automation create` and `pipefy automation update` for the shared condition payload.

## Create an AI automation

`pipefy ai-automation create` runs the prompt check with the selected event before it creates the rule. Add `--no-active` for a rule that must start off. Replace the example pipe and field ids with ids from the pipe:

```bash
pipefy ai-automation create --pipe 67890 --name "Summarize intake" --event-id card_created --prompt "Summarize %{900000102} into the summary field." --field-ids '["900000101"]' --no-active --json
```

The response holds the new id in `automation_id`. Read the rule with `pipefy ai-automation get <automation_id>`. Activate it only when the shared workflow permits activation:

```bash
pipefy ai-automation update <automation_id> --pipe 67890 --patch-active --json
```
