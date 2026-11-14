# MCP reference — pipefy-automations

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

Destructive deletes are two-step: show the preview to the user and obtain approval, then echo its `confirmation_token` with `confirm=true`. Never skip the preview.

`get_automations` exposes `pagination.total_count` and `has_more`; follow `after`
until `has_more` is false. For `get_ai_automations`, pagination describes the
mixed automation page, not only the AI rules returned from that page.

An invalid `create_automation` phase transition returns `success: false` with a **text** error message listing allowed destination phases by name and id, plus a hint on how phases get connected and where to change the connections. There is no structured `valid_destinations` field on this envelope.

Invalid `field_map` field IDs fail before GraphQL with `success: false` and the offending ID.

For a validated AI automation, call `create_ai_automation` with `name`, `event_id`, `pipe_id`, `prompt`, `field_ids`, and `active`. Use `active=false` for a rule that must start off:

```text
create_ai_automation name="Summarize intake" event_id="card_created" pipe_id=67890 prompt="Summarize %{900000102} into the summary field." field_ids=["900000101"] active=false
```

In the default response, the new id is in `data.automation_id`. A server with the legacy envelope returns it as `automation_id` at the top level. Pass that id to `get_ai_automation` to read the saved rule:

```text
get_ai_automation automation_id=<automation_id>
```

Activate the rule only when the shared workflow permits activation:

```text
update_ai_automation automation_id=<automation_id> active=true
```
