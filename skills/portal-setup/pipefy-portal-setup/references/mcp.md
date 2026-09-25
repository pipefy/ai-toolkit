# MCP controls and examples

- **Cursor MCP:** after changing `PIPEFY_*` in `.env`, restart the MCP server so tools pick up the new credentials.

`delete_portal_page`: use the two-step preview (`confirmation_token` from the preview, then `confirm=true`).

If the raw response exposes nested `success: false`, treat the operation as failed even when the MCP envelope looks ambiguous.

## Two-step destructive deletes

MCP deletes (`delete_portal`, `delete_portal_page`, `delete_portal_element`, `delete_sub_portal`, `delete_sub_portal_element`) return a preview with `confirmation_token`. Echo that token with `confirm=true` on the second call. `unpublish_sub_portal` is not gated.

---

**Detach** element wiring (destructive: MCP two-step with `confirmation_token`):

MCP:
```
delete_sub_portal_element portal_uuid="<MAIN_PORTAL_UUID>" element_id="<FORMS_ELEMENT_ID>" confirm=false
```
Then after approval, echo the preview's `confirmation_token`:

```
delete_sub_portal_element portal_uuid="<MAIN_PORTAL_UUID>" element_id="<FORMS_ELEMENT_ID>" confirm=true confirmation_token="<token from preview>"
```

**Delete sub-portal interface** (irreversible):

MCP two-step `delete_sub_portal` (echo `confirmation_token`).

## MCP response shape

- Read tools return `{ success: true, data: { ... } }` when `PIPEFY_MCP_UNIFIED_ENVELOPE` is enabled (default). Parse **`data`** for `portals`, `pages`, `subPortals`, etc.
- GraphQL/transport failures → `{ success: false, error: { message: "..." } }` — do not treat transport errors as success.
- **`PERMISSION_DENIED`** on portal tools usually names **`create_portal`** or **`manage_portals`**. Re-check org id, token, and SA **`joinAsAdmin`** (see the skill’s “Confirm access before writes” section).
- Only **`PERMISSION_DENIED`** is rewritten to the portal permission hint; other GraphQL codes surface as generic errors with the API message.
- Destructive deletes: default **`confirm=false`** returns a preview (`requires_confirmation: true`, `confirmation_token`); call again with **`confirm=true`** and that token only after explicit human approval.

---

```text
list_portals organization_uuid="123456789"
```

```text
create_portal organization_uuid="123456789"
```

```text
get_portal portal_uuid="<MAIN_PORTAL_UUID>"
```

```text
create_portal_element page_id="<PAGE_ID>" type="forms" metadata={"name": "Request access", "gridMap": {"height": 66, "columns": 4, "minColumns": 4}}
```

```text
create_sub_portal main_portal_uuid="<MAIN_PORTAL_UUID>" name="Partner hub"
```

```text
publish_sub_portal portal_uuid="<MAIN_PORTAL_UUID>" element_id="<FORMS_ELEMENT_ID>" sub_portal_uuid="<SUB_PORTAL_UUID>"
```

```text
get_portal portal_uuid="<MAIN_PORTAL_UUID>"
```

```text
update_portal portal_uuid="<MAIN_PORTAL_UUID>" visibility="public"
```

```text
unpublish_sub_portal portal_uuid="<MAIN_PORTAL_UUID>" element_id="<FORMS_ELEMENT_ID>"
```

This workflow exposes 20 MCP tools.

The GraphQL `id` is exposed as `uuid` (same value).
