# CLI commands and flags

The CLI always runs locally as the user, so it exposes `--file` (a local path) only.

The CLI equivalent is `pipefy attachment presign` (prints `upload_url` /
`storage_path` / `expires_in_seconds`); you run the `PUT` and the field update.

## Command mapping

| Operation | CLI equivalent |
| ------------ | ---------------- |
| `upload_attachment_to_card` | `pipefy attachment upload --card <id>` |
| `upload_attachment_to_table_record` | `pipefy attachment upload --record <id>` |
| `create_attachment_presigned_url` | `pipefy attachment presign` |

```bash
pipefy attachment upload --org 42 --card 1234 --field document_upload --file ~/report.pdf
```

```bash
pipefy attachment upload --org 42 --record tr-555 --field document_upload --file /tmp/export.csv
```

The CLI exposes 2 attachment commands.
