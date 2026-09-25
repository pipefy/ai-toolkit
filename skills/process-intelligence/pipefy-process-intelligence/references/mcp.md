# MCP reference

## Invocation examples

```text
get_pipe pipe_id=<id>
```

```text
get_cards pipe_id=<id> first=50 include_fields=true
```

```text
get_automations pipe_id=<id>
```

```text
get_ai_agents repo_uuid=<PIPE_UUID>
```

```text
create_automation pipe_id=<id> name="Overdue Alert" trigger_event="card_overdue" actions='[{"type":"send_email","to":"assignee"}]'
```

```text
create_field_condition pipe_id=<id> phase_id=<phase_id> action="show" when='{"field_id":"<f1>","value":"Yes"}' fields='["<f2>"]'
```
