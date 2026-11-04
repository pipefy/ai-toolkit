# MCP reference

## Invocation examples

```text
search_pipes pipe_name=""
```

An empty search returns all visible pipes.

```text
get_organization organization_id=<id>
```

For a pipe that the design can reuse:

```text
get_pipe pipe_id=<id>
```

```text
get_automations pipe_id=<id>
```

Pass `after=<pagination.end_cursor>` while `pagination.has_more` is true.

```text
get_ai_agents repo_uuid=<pipe.uuid>
```
