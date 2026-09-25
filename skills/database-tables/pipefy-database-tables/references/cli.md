# CLI commands and flags

Destructive operations use `--yes` (no token), only after showing affected data and obtaining explicit approval. Never delete in a single unreviewed step.

## Table commands

| Operation | CLI |
| ------------ | ----- |
| `get_tables` | `pipefy table list` |
| `search_tables` | `pipefy table list --search` |
| `get_table` | `pipefy table get <id>` |
| `create_table` | `pipefy table create` |
| `update_table` | `pipefy table update <id>` |
| `delete_table` | `pipefy table delete <id>` |

## Table field commands

| Operation | CLI |
| ------------ | ----- |
| `create_table_field` | `pipefy table field create <table_id> --label <name> --type <type>` |
| `update_table_field` | `pipefy table field update <field_id> --table <table_id> --label <name>` |
| `delete_table_field` | `pipefy table field delete <field_id> --table <table_id>` |

## Record commands

| Operation | CLI |
| ------------ | ----- |
| `get_table_records` | `pipefy record find --table <id>` |
| `find_records` | `pipefy record find --filter` |
| `get_table_record` | `pipefy record get <id>` |
| `create_table_record` | `pipefy record create` |
| `update_table_record` | `pipefy record update <id> --fields ...` |
| `set_table_record_field_value` | `pipefy record update <id> --field-id <slug> --value <json>` |
| `delete_table_record` | `pipefy record delete <id>` |

## Attachment commands

| Operation | CLI |
| ------------ | ----- |
| `upload_attachment_to_table_record` | `pipefy attachment upload --record <id> --field <slug> --file <path> --organization <id>` |

```bash
pipefy table list
```

```bash
pipefy record find --table 456 --filter '{"column_id":"email","search_value":"user@example.com"}'
```

```bash
pipefy record update 789 --field-id status --value '"Active"'
```

```bash
pipefy record update 789 --fields '{"status":"Active"}'
```

Attachment uploads accept `--file` only. See `pipefy-attachments`.

Table field updates also accept `--description`, `--required`, and `--options`.
