# Members, Email & Webhooks

Manage pipe membership, send emails from card inboxes, read inbox replies, and manage webhooks (list, create, update, delete).

## Email templates

Hard stop: creating, editing and deleting email templates is not part of the API or MCP surface. The GraphQL schema has no template CRUD mutation, so the only path is the Pipefy UI. A flow that needs a new or edited template carries a manual UI step, and that step belongs in the plan handed to the user before any build starts.

## Notes

- `add_service_account_to_pipe` sends the `inviteMembers` mutation, the same one that `invite_members` uses.
