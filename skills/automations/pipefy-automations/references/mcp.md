# MCP reference — pipefy-automations

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

Destructive deletes are two-step: show the preview to the user and obtain approval, then echo its `confirmation_token` with `confirm=true`. Never skip the preview.

An invalid `create_automation` phase transition returns `success: false` with a **text** error message listing allowed destination phases by name and id, plus a hint that transition rules are configured in the Pipefy UI only (not editable via API). There is no structured `valid_destinations` field on this envelope.

Invalid `field_map` field IDs fail before GraphQL with `success: false` and the offending ID.
