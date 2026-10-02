# MCP reference — pipefy-pipes-and-cards

## Creation and error controls

Most write tools support `debug=true` on errors, returning GraphQL codes and `correlation_id`.

Interactive clients may elicit start-form fields on `create_card`. For agent seeding, use `skip_elicitation=true`:

```
create_card pipe_id="306996634" phase_id="340012345" skip_elicitation=true title="Seeded"
```

`get_pipe` returns phase metadata inside the pipe's phases. On a required empty field, `move_card_to_phase` may return `success: false` naming the field and optionally a hide hint. Always discover allowed targets first.

## Attachments

`upload_attachment_to_card` takes exactly one source: `file_path` on the MCP server's filesystem (local profile only), or `file_url` (SSRF-guarded download, any profile and required on hosted). The attachment `field_id` is a slug. See `pipefy-attachments`.

## Field-condition controls

`create_field_condition` verifies the rule on the requested phase. `verified: true` indicates verification succeeded; missing/wrong phase returns `success: false` with `error.details.condition_id`. Use that ID (or the ID in the message) to delete the condition through the destructive preview flow before recreating. Do not blind-retry create. If verification reads are inconclusive, the tool may return success with a warning that verification was unavailable.

Do not hide a required field. MCP rejects `hide` / `hidden` on `required=true`; clear `required` first. `update_field_condition` enforces this when top-level `actions` is set. Passing `actions` through `extra_input` returns `INVALID_ARGUMENTS`. See [parity](https://github.com/pipefy/ai-toolkit/blob/main/docs/parity.md).

## Destructive deletes

Deletes return a preview first, including `confirmation_token`. This is expected, not a failed deletion. Show the preview to the user and obtain approval, then repeat with `confirm=true` and that token.
