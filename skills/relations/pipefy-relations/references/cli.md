# CLI commands and flags

## Command mapping

| Operation | CLI |
| ------------ | ----- |
| `get_pipe_relations` | `pipefy relation pipe list --pipe <id>` |
| `create_pipe_relation` | `pipefy relation pipe create` |
| `update_pipe_relation` | `pipefy relation pipe update <id>` |
| `delete_pipe_relation` | `pipefy relation pipe delete <id>` |
| `get_table_relations` | `pipefy relation table list --ids <id,...>` |
| `get_card_relations` | `pipefy relation card list --card <id>` |
| `create_card_relation` | `pipefy relation card create` |
| `delete_card_relation` | `pipefy relation card delete <id>` |

```bash
pipefy relation pipe list --pipe 67890
```

```bash
pipefy relation card create --source-relation <id> --source-card <id> --target-card <id>
```

```bash
pipefy relation pipe create --parent 111 --child 222 --name "Support Escalation"
```

Destructive operations use `--yes` after reviewing the affected data and obtaining approval.
