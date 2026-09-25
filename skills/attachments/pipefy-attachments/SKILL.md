---
name: pipefy-attachments
description: >
  Use this skill when the user wants to upload a file to a Pipefy card or
  table-record attachment field. Covers local and downloaded file sources,
  plus a presigned-URL handshake for uploading files directly.
tags: [pipefy, attachments, upload, card, table-record]
---

# Attachments

MCP clients: read [references/mcp.md](references/mcp.md). CLI users: read [references/cli.md](references/cli.md). Examples below describe shared operation arguments.

Upload one file at a time to a card or table-record attachment field. The
upload goes through Pipefy's presigned URL flow (request URL, S3 PUT, then
field update). **3 operations.**

---

## When to use

- The user says "attach this file to card X" or "upload to the documents field
  on record Y".
- Pick the source by where the bytes actually are. Use the source rules for your chosen surface.

Do not use this skill for:

- Reading or listing existing attachments. There is no list/download tool in
  this skill scope. Cards and table records expose their attachments through
  the regular card/record fetch tools.
- Bulk uploads. One file per call; iterate at the agent layer.

## Prerequisites

- A Pipefy `organization_id`. Find it via `get_organization` or `get_pipe`.
- A target `card_id` or `table_record_id`.
- The attachment field's slug (the human-readable id like `document_upload`,
  not the field's uuid). Find it on the card or table record fetch tools.
- Exactly one file source accessible to the chosen upload surface.

## Tools needed

| Operation | Read-only |
| ------------ | ----------- |
| `upload_attachment_to_card` | No |
| `upload_attachment_to_table_record` | No |
| `create_attachment_presigned_url` | No |

## Steps

### Upload a local file to a card

`file_name` is inferred from the source basename when omitted, so callers
usually only pass the four IDs and the source.

Operation arguments:

```text
upload_attachment_to_card(organization_id=42, card_id=1234, field_id=document_upload, file_path=~/report.pdf)
```

### Upload from a URL

```text
upload_attachment_to_card(organization_id=42, card_id=1234, field_id=document_upload, file_url=https://example.com/report.pdf)
```

When the URL has no filename in its path (e.g. `.../download?id=1`), pass
`file_name` explicitly so Pipefy stores it under a real name.

### Upload a local file to a table record

Operation arguments:

```text
upload_attachment_to_table_record(organization_id=42, table_record_id=tr-555, field_id=document_upload, file_path=/tmp/export.csv)
```

## Overriding the file name

To store the attachment under a different name than the source basename, pass
`file_name` explicitly. It wins over the inferred basename.

```text
upload_attachment_to_card(..., file_url=https://example.com/abc123.pdf, file_name=Invoice-2026.pdf)
```

## Use the presigned handshake

When the one-shot upload cannot reach the bytes or exceeds its 100 MiB cap, use
`create_attachment_presigned_url` and upload from an environment that can read the file:

1. Call `create_attachment_presigned_url` with `organization_id` + `file_name`
   (optional `content_type` / `content_length`). It returns `upload_url` (the S3
   PUT url), `storage_path` (the object key), and `expires_in_seconds`.
2. From an environment that can reach the upload host, HTTP `PUT` the file bytes
   to `upload_url` within `expires_in_seconds` (send `Content-Type` /
   `Content-Length` matching what you passed, if any).
3. Set the attachment field to `[storage_path]` via `update_card_field` /
   `set_table_record_field_value`. Store `storage_path`, never a URL — the signed
   download URL is minted on read.

Because the bytes are handled by the client (step 2), not passed through the
tool call, this keeps the model's context clean.

## Success criteria

**`upload_attachment_to_card` / `upload_attachment_to_table_record`** (one-shot):
the upload result has a `download_url` (the signed URL Pipefy
returns), the inferred or explicit `content_type`, and the `file_size` in
bytes, and the attachment field on the card or record now lists the file. One
call is the whole job.

**`create_attachment_presigned_url`** (handshake) is **not done at mint**:
a successful result here only means a target was minted — no field was touched and
nothing is attached yet. Done means you completed all three steps: after the
client PUTs the bytes to `upload_url` and you set the field to `[storage_path]`,
the attachment field lists the file. Do not treat the mint response (or its
premature signed URL) as a finished upload.

## Failure modes

Check source accessibility, the 100 MiB one-shot limit, upload expiry and signed
headers, and write access to the attachment field. The presigned handshake
requires checking the client PUT and field update separately from minting.

## See also

- `pipefy-pipes-and-cards`: finding card ids and attachment field slugs.
- `pipefy-database-tables`: finding table record ids and field slugs.
