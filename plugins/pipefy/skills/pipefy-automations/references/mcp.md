# MCP reference — pipefy-automations

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

Destructive deletes are two-step: show the preview to the user and obtain approval, then echo its `confirmation_token` with `confirm=true`. Never skip the preview.

`get_automations` exposes `pagination.total_count` and `has_more`; follow `after`
until `has_more` is false. For `get_ai_automations`, pagination describes the
mixed automation page, not only the AI rules returned from that page.

An invalid `create_automation` phase transition returns `success: false` with a **text** error message listing allowed destination phases by name and id, plus a hint that transition rules are configured in the Pipefy UI only (not editable via API). There is no structured `valid_destinations` field on this envelope.

Invalid `field_map` field IDs fail before GraphQL with `success: false` and the offending ID.

For the validated AI automation in the shared workflow, call `create_ai_automation` with `name`, `event_id`, `pipe_id`, `prompt`, and `field_ids`:

```text
create_ai_automation name="Summarize intake" event_id="card_created" pipe_id=67890 prompt="Summarize %{900000102} into the summary field." field_ids=["900000101"]
```
