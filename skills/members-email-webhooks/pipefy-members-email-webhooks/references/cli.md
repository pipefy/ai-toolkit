# CLI commands and flags

`add_service_account_to_pipe`: The **CLI** does not verify — it prints the raw invite result, so check `inviteMembers.errors` (or run `pipefy member list --pipe <id>`) to confirm the account was actually added.

## Member commands

| Operation | CLI |
| ------------ | ----- |
| `invite_members` | `pipefy member invite` |
| `add_service_account_to_pipe` | `pipefy member add-service-account` |
| `remove_member_from_pipe` | `pipefy member remove` |
| `set_role` | `pipefy member set-role` |

## Email commands

| Operation | CLI |
| ------------ | ----- |
| `get_card_inbox_emails` | `pipefy email inbox list --card <id>` |
| `send_inbox_email` | `pipefy email inbox send` |
| `get_email_templates` | `pipefy email template list --repo <id>` |
| `send_email_with_template` | `pipefy email template send` |

## Webhook commands

| Operation | CLI |
| ------------ | ----- |
| `get_webhooks` | `pipefy webhook list --pipe <id>` |
| `create_webhook` | `pipefy webhook create` |
| `update_webhook` | `pipefy webhook update <id>` |
| `delete_webhook` | `pipefy webhook delete <id>` |

```bash
pipefy member list --pipe 67890
```

```bash
pipefy member invite --pipe 67890 --email alice@example.com --role member
```

```bash
pipefy member add-service-account --pipe 67890 --email svc-automations@your-org.pipefy-service.com
```

```bash
pipefy email inbox send --card 12345 --to customer@example.com --subject "Your request is in progress" --body "Hi, we are processing your request." --from-email you@example.com
```

```bash
pipefy webhook list --pipe 67890
```

```bash
pipefy webhook create --pipe 67890 --url https://your-server.com/pipefy --events card.create,card.done
```

Destructive operations use `--yes` after reviewing the affected data and obtaining approval.
