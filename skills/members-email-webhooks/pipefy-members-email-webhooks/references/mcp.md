# MCP controls and examples

`add_service_account_to_pipe`: The **MCP tool** verifies membership afterwards: it returns an error if the account is not a member of the pipe once the invite is processed, so an incomplete setup is not reported as success.

Delete a throwaway service account with two-step `delete_service_account` (echo `confirmation_token`) when done.

- **`delete_webhook` first call returns preview:** expected. Show the preview to the user and get their approval, then call with `confirm=true` and the preview's `confirmation_token`.

```text
get_pipe_members pipe_id=67890
```

```text
invite_members pipe_id=67890 members='[{"email":"alice@example.com","role_name":"member"},{"email":"bob@example.com","role_name":"admin"}]'
```

```text
add_service_account_to_pipe pipe_id=67890 email=svc-automations@your-org.pipefy-service.com
```

```text
get_card_inbox_emails card_id=12345
```

```text
send_inbox_email card_id=12345 to="customer@example.com" subject="Your request is in progress" body="Hi, we are processing your request."
```

```text
get_webhooks pipe_id=67890
```

```text
create_webhook pipe_id=67890 url="https://your-server.com/pipefy" actions='["card.create","card.done"]'
```

Destructive operations use two steps: show the preview and obtain approval, then echo `confirmation_token` from the preview with `confirm=true`.

`remove_member_from_pipe` verifies afterwards and warns if the member is still present (org-level permissions can override pipe removal).

This workflow exposes 12 MCP tools.
