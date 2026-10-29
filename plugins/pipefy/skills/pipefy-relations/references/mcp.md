# MCP controls and examples

- **`delete_pipe_relation` first call returns preview:** expected. Show the preview to the user and get their approval, then call with `confirm=true` and the preview's `confirmation_token`.

```text
get_pipe_relations pipe_id=67890
```

```text
create_card_relation parent_id=<PARENT_CARD_ID> child_id=<CHILD_CARD_ID> source_id=<PIPE_RELATION_ID>
```

```text
get_card_relations card_id=<CHILD_CARD_ID>
```

```text
create_pipe_relation parent_id=111 child_id=222 name="Support Escalation"
```

Destructive operations use two steps: show the preview and obtain approval, then echo `confirmation_token` from the preview with `confirm=true`.
