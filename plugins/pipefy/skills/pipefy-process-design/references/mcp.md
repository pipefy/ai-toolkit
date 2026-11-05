# MCP reference

## Invocation examples

```text
search_pipes pipe_name=""
```

An empty search lists pipes that the caller belongs to, with a cap per organization. Read `search_limits.max_pipes_per_org` before treating the result as complete.

With a name filter, `pipes_truncated: true` means that matching results exceeded the cap. Without a name filter, the flag can also reflect membership scope. The flag alone does not prove that the cap removed results.

Report unresolved access or truncation limits in the reuse assessment. Do not conclude that no reusable pipe exists outside the returned scope. Read [pipe listing limits](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/organization.md#why-counts-disagree) for the discovery rules.

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
