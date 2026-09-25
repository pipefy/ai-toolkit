# CLI commands and flags

Bootstrap portals with `pipefy portal create`, not undocumented `createInterface` GraphQL.

Find the organization id with `pipefy org get` or the Pipefy URL.

Delete the disposable test page with `pipefy portal page delete` and `--yes` only after approval.

Deletes (`pipefy portal delete`, page/element/sub-portal delete, and sub-portal detach) use `--yes` after approval. `unpublish_sub_portal` is not gated.

```bash
pipefy portal sub-portal detach <MAIN_PORTAL_UUID> <FORMS_ELEMENT_ID> --yes
```

```bash
pipefy portal sub-portal delete <SUB_PORTAL_UUID> --yes
```

CLI `--json` prints the raw SDK payload (no `success` wrapper).

## Command mapping

| Operation | CLI equivalent |
| ------------ | ---------------- |
| `list_portals` | `pipefy portal list` |
| `get_portal` | `pipefy portal get` |
| `create_portal` | `pipefy portal create` |
| `update_portal` | `pipefy portal update` |
| `delete_portal` | `pipefy portal delete` |
| `create_portal_page` | `pipefy portal page create` |
| `update_portal_page` | `pipefy portal page update` |
| `delete_portal_page` | `pipefy portal page delete` |
| `sort_portal_pages` | `pipefy portal page sort` |
| `update_portal_page_layout` | `pipefy portal page layout update` |
| `create_portal_element` | `pipefy portal element create` |
| `update_portal_element` | `pipefy portal element update` |
| `delete_portal_element` | `pipefy portal element delete` |
| `duplicate_portal_element` | `pipefy portal element duplicate` |
| `create_sub_portal` | `pipefy portal sub-portal create` |
| `update_sub_portal_element` | `pipefy portal sub-portal attach` |
| `publish_sub_portal` | `pipefy portal sub-portal publish` |
| `unpublish_sub_portal` | `pipefy portal sub-portal unpublish` |
| `delete_sub_portal_element` | `pipefy portal sub-portal detach` |
| `delete_sub_portal` | `pipefy portal sub-portal delete` |

```bash
pipefy portal list --organization-uuid 123456789
pipefy portal create --organization-uuid 123456789
```

```bash
pipefy portal get <MAIN_PORTAL_UUID>
```

```bash
pipefy portal element create --page-id <PAGE_ID> --type forms \
  --metadata '{"name":"Request access","gridMap":{"height":66,"columns":4,"minColumns":4}}'
```

```bash
pipefy portal sub-portal create --main-portal-uuid <MAIN_PORTAL_UUID> --name "Partner hub"
```

```bash
pipefy portal sub-portal publish <MAIN_PORTAL_UUID> <FORMS_ELEMENT_ID> <SUB_PORTAL_UUID>
```

```bash
pipefy portal update <MAIN_PORTAL_UUID> --visibility public
```

```bash
pipefy portal sub-portal unpublish <MAIN_PORTAL_UUID> <FORMS_ELEMENT_ID>
```

The GraphQL `id` is exposed as `uuid` (same value).
