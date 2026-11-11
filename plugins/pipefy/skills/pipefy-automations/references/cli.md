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

## Create an AI automation inactive

Use the shared "Create an AI automation inactive" recipe before this command. Run the prompt check with the selected event:

```bash
pipefy ai-automation validate-prompt --pipe 67890 --prompt "Summarize %{900000102} into the summary field." --field-ids '["900000101"]' --event-id card_created --json
```

Replace the example pipe and field ids with ids from the pipe. Use the selected event and its parameters:

```bash
pipefy automation create --pipe 67890 --name "Summarize intake" --event-id card_created --action-id generate_with_ai --no-active --extra '{"action_params":{"aiParams":{"value":"Summarize %{900000102} into the summary field.","fieldIds":["900000101"],"skillsIds":[]}},"condition":{"expressions":[{"structure_id":0,"field_address":"","operation":"","value":""}],"expressions_structure":[[0]]}}' --json
```

The response holds the new id in `createAutomation.automation.id`. Read the rule with `pipefy ai-automation get <automation_id>`. Activate it only when the shared recipe permits activation:

```bash
pipefy ai-automation update <automation_id> --pipe 67890 --patch-active --json
```
