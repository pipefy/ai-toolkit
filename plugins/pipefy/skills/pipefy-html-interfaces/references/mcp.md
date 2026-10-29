# MCP controls and examples

- **CLI users:** read [cli.md](cli.md) for the command equivalents.
- **Response shape.** Every tool here returns both `result` (a pretty-printed JSON string) and `data` (the parsed dict). Read `data`: `data.repos`, `data.fields`, `data.interfaces`, and for an interface `data.uuid` and `data.pages`.
- **Sources are checked before any network call.** `create_html_interface` and `set_interface_sources` reject a malformed `data_sources` list (duplicate `id` or `name`, an empty or over-long `fieldKeys`, more than 10 sources) with `INVALID_ARGUMENTS` and change nothing.
- **Create-then-write failure.** When `create_html_interface` creates the interface but the write fails, the error's `details` carries `uuid`, `page_id`, and `element_id`. Pass `page_id` and `element_id` to `write_interface_html`. When the create returns no page, `details` carries only `uuid`; pass it to `get_interface_html`.
- **Deleting a duplicate.** `delete_portal` is a two-step call: the first returns a preview with a `confirmation_token`. Show the preview to the user, and only after their approval call again with `confirm=true` and that token.

```text
get_interface_html_guidelines
list_interface_repos organization_id=<org_id> interface_uuid=<interface_uuid>
write_interface_html page_id=<page_id> element_id=<element_id> content=<document>
delete_portal portal_uuid=<interface_uuid>
```
