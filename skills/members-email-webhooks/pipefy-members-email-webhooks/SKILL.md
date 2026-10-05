---
name: pipefy-members-email-webhooks
description: >
  Use this skill when the user wants to manage pipe membership, send or read
  card inbox emails, use email templates, or manage webhooks.
tags: [pipefy, members, email, webhooks, inbox]
---

# Members, Email & Webhooks

MCP clients: read [references/mcp.md](references/mcp.md). CLI users: read [references/cli.md](references/cli.md). Examples below describe shared operation arguments.

Manage pipe membership, send emails from card inboxes, read inbox replies, and manage webhooks.

---

## Member management

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `invite_members` | No | Invite one or more users by email + role. |
| `add_service_account_to_pipe` | No | Attach an existing org **service account** to a pipe by email + role (iPaaS setup). Check membership afterwards. |
| `remove_member_from_pipe` | No | **Destructive; review and approve first.** Check afterwards: org-level permissions can override pipe removal. |
| `set_role` | No | Change a member's pipe role (`member_id` = user id). |

List existing members with `get_pipe_members` from `pipefy-pipes-and-cards`. Id forms: [`docs/mcp/tools/identifiers.md#members-email-webhooks`](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/identifiers.md#members-email-webhooks).

### Steps — invite members

1. **Check existing members:**

   Operation: `get_pipe_members(pipe_id=67890)`

2. **Invite new members:**

   Operation: `invite_members(pipe_id=67890, members='[{"email":"alice@example.com","role_name":"member"},{"email":"bob@example.com","role_name":"admin"}]')`

   > Before inviting **external emails** (domain different from the org's known domains), warn the user that this is an external invitation and confirm before proceeding.

   > Before granting **admin role**, confirm with the user — admin is the highest pipe-level role.

### Steps — add a service account to a pipe (iPaaS setup)

When setting up an iPaaS (Advanced Automations) flow that runs under a **service account**, the account must be a member of the target pipe, or pipe-scoped calls under its identity fail with a permission error even though the flow looks configured.

1. **Get the service account's email.** Either create one with `create_service_account(organization_uuid, name, role)` — which returns the account's email plus its OAuth2 client secret and token endpoint **once** (store them immediately) — or take the email from your organization's service-account settings. A freshly created account has no pipe access until this step. The pipe role defaults to `admin` (a service account running automations usually needs full pipe access); pass a narrower role only when you deliberately want to limit it.

   > One-step alternative: `create_service_account(organization_uuid, name, role, pipe_ids=[...])` provisions the account **and** adds it to the given pipes in one call, returning a `pipe_memberships` summary. Use it when you already know the target pipes.

2. **Attach it** (when not using the `pipe_ids` shortcut above):

   Operation: `add_service_account_to_pipe(pipe_id=67890, email=svc-automations@your-org.pipefy-service.com)` (role defaults to `admin`)

   This attaches an existing service account — create one first with `create_service_account` if needed. Delete a throwaway account after approval when done. See [docs/mcp/tools/service-accounts.md](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/service-accounts.md).

---

## Email (card inbox)

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_card_inbox_emails` | Yes | Read emails in a card's inbox. |
| `send_inbox_email` | No | Send an email from a card inbox. |
| `get_email_templates` | Yes | List templates for a pipe or table (`repo_id` numeric). |
| `send_email_with_template` | No | Send using a template (`email_template_id` from that list). |

> **Confirm every send.** Both send operations deliver mail outside Pipefy, often to external addresses, and a sent email cannot be recalled. Before each `send_inbox_email`, show the user the recipients (`to`, plus `cc` / `bcc` when set), the subject and the body. Before each `send_email_with_template`, show the template name and the recipients it will use: the `to` you pass, or with no `to`, the template's `toEmail` (from `get_email_templates`; a `{{...}}` placeholder there resolves from the card's fields). The template's `ccEmail` / `bccEmail` are not sent: to copy someone, pass `cc` / `bcc` in the send call and show them too. Send only after the user confirms. One confirmation covers one send: a request covering several cards still needs a confirmation per email, never one approval for a loop.

> **Templates are UI-only.** Creating, editing and deleting an email template has no API, MCP or CLI path: the GraphQL schema has no template CRUD mutation. The template must already exist before a flow can send with it. When the process needs a new or changed template, put the manual Pipefy UI step in the plan you give the user instead of promising an end-to-end email flow.

### Steps — send a card inbox email

1. **Get the card's inbox emails** (see what has been received):

   Operation: `get_card_inbox_emails(card_id=12345)`

2. **Confirm the draft:** show the user the recipients, the subject and the body, and wait for their approval.

3. **Send the reply** (only after approval):

   Operation: `send_inbox_email(card_id=12345, to=["customer@example.com"], from_="you@example.com", subject="Your request is in progress", body="Hi, we are processing your request.")`

   `to` is a list of addresses, and `from_` (the sender address) is required.

---

## Webhooks

| Operation | Read-only | Purpose |
| ------------ | ----------- | --------- |
| `get_webhooks` | Yes | List all webhooks for a pipe. |
| `create_webhook` | No | Register a new webhook endpoint. |
| `update_webhook` | No | Change URL, headers, or events. |
| `delete_webhook` | No | **Destructive; review and approve first.** |

> **Header values are secrets.** `get_webhooks` returns each webhook's `headers` unmasked, and they usually hold authorization tokens or API keys. In a reply, name only the header keys (for example `Authorization`, `X-Api-Key`), never their values, even when the user asks for them. A lost token comes back from the system that issued it; to replace it, set a new value with `update_webhook`. `update_webhook` replaces the whole `headers` object, so send every header from `get_webhooks` and change only the lost one, or the others are deleted. An update that leaves `headers` out deletes them all, so a change to only the URL, name or events must resend the headers too.

### Steps — create a webhook

1. **List existing webhooks:**

   Operation: `get_webhooks(pipe_id=67890)`

2. **Create the webhook:**

   Operation: `create_webhook(pipe_id=67890, url="https://your-server.com/pipefy", actions='["card.create","card.done"]')`

---

## Success criteria

- Invited members appear in `get_pipe_members`.
- Sent emails show in the card's inbox thread.
- Created webhooks receive test payloads from Pipefy on the configured events.

## Failure modes

- **`invite_members` fails with "user not found":** verify the email address is correct.
- **`send_inbox_email` fails:** the card must have an inbox enabled in the pipe settings.
- **Webhook never fires:** verify the pipe events match the configured `actions` list; check that the endpoint URL is publicly reachable (not localhost).
- **Deletion:** review the affected webhook or member and obtain approval before removal.

## See also

- `pipefy-pipes-and-cards` — create the pipe and cards before managing membership.
- `pipefy-observability` — monitor email and webhook delivery logs.
- `pipefy-ipaas` — when a flow's service account needs pipe membership.
