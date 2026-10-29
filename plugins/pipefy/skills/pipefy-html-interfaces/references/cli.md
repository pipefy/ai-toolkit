# CLI commands and flags

All commands sit under `pipefy portal html-interface`, except deleting a duplicate, which uses `pipefy portal delete`.

`write` and `create` take the HTML document as `--content`/`--html`, or read it from a file with `--content-file`/`--html-file` (mutually exclusive, one required) — a real document is hard to quote in a shell. `create`'s `--color` defaults to `blue`. `--data-sources` on `create` and `set-sources` takes the JSON array inline, the same shape as the MCP `data_sources` argument.

## Command mapping

| Operation | CLI equivalent |
| --- | --- |
| `get_interface_html_guidelines` | `pipefy portal html-interface guidelines` |
| `list_interface_repos` | `pipefy portal html-interface repos` |
| `get_interface_repo_fields` | `pipefy portal html-interface repo-fields` |
| `list_interfaces` | `pipefy portal html-interface list` |
| `get_interface_html` | `pipefy portal html-interface get` |
| `create_html_interface` | `pipefy portal html-interface create` |
| `set_interface_sources` | `pipefy portal html-interface set-sources` |
| `write_interface_html` | `pipefy portal html-interface write` |
| `delete_portal` (duplicate cleanup) | `pipefy portal delete` |

```bash
pipefy portal html-interface guidelines
pipefy portal html-interface guidelines --include-design-system
```

```bash
pipefy portal html-interface repos --organization-id <org_id> --repo-name <name_fragment>
pipefy portal html-interface repo-fields --repo-uuid <repo_uuid>
```

```bash
pipefy portal html-interface list --organization-uuid <org_id> --search-term <name>
```

```bash
pipefy portal html-interface get <interface_uuid>
```

```bash
pipefy portal html-interface create --organization-uuid <org_id> --name "Open requests" \
  --html-file page.html \
  --data-sources '[{"id": "requests", "name": "Open requests", "repoId": "<repo_uuid>", "fieldKeys": ["title", "<field_uuid>"]}]'
```

```bash
pipefy portal html-interface set-sources --interface-uuid <interface_uuid> --page-id <page_id> --element-id <element_id> \
  --data-sources '[...]'
```

```bash
pipefy portal html-interface write --page-id <page_id> --element-id <element_id> --content-file page.html
```

```bash
pipefy portal delete <interface_uuid> --yes
```
