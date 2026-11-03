# MCP reference

## Invocation examples

```text
get_pipe pipe_id=<id>
```

```text
get_records pipe_id=<id> first=50 include_fields=true order_by=[{"attribute": "CREATED_AT", "direction": "DESC"}]
```

```text
execute_graphql query=<the TimedCards document in the skill> variables={"pipeId": "<id>"}
```

```text
get_automations pipe_id=<id>
```

```text
get_ai_agents repo_uuid=<PIPE_UUID>
```

```text
get_ai_agent uuid=<AGENT_UUID>
```

```text
create_automation pipe_id=<id> name="Automate manual step" trigger_id=<EVENT_ID> action_id=<ACTION_ID> active=false
```

```text
create_field_condition phase_id=<PHASE_ID> name="Show follow-up" condition=<CONDITION_DICT> actions=<ACTION_DICTS>
```
