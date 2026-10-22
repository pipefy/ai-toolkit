# MCP reference

## Invocation examples

```text
get_pipe pipe_id=<id>
```

```text
get_cards pipe_id=<id> first=50 include_fields=true
```

```text
execute_graphql query=<document below> variables={"pipeId": "<id>"}
```

```graphql
query TimedCards($pipeId: ID!, $first: Int = 25, $after: String) {
  cards(pipe_id: $pipeId, first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id done createdAt finished_at started_current_phase_at current_phase_age updated_at
      current_phase { name }
      phases_history { phase { name } firstTimeIn lastTimeOut duration }
    } }
  }
}
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
