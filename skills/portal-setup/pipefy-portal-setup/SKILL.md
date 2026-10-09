---
name: pipefy-portal-setup
description: >
  Use this skill when the user wants to list, create, or configure Pipefy
  portals (main hub, pages, page elements, sub-portals, publish/unpublish).
  Uses Interfaces and internal_api. Not for pipes/cards.
tags: [pipefy, portal, interfaces, sub-portal, pages, elements]
---

# Portal setup

MCP clients: read [references/mcp.md](references/mcp.md). CLI users: read [references/cli.md](references/cli.md). Examples below describe shared operation arguments.

Configure an organization's Pipefy portal: bootstrap the main hub, add pages and widgets, wire and publish sub-portals (Interfaces GraphQL + internal_api for sub-portal wiring).

Deep reference: [`docs/mcp/tools/portal.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/portal.md). Parity matrix: [`docs/parity.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/parity.md). Env vars: [`docs/config.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/config.md).

---

## When to use

- "Create our company portal", "list portals for org X", "publish a sub-portal".
- Add or change portal pages, layout, or page elements (`forms`, `link`, etc.).
- Attach, publish, unpublish, or delete sub-portals on the main portal.

Do **not** use for:

- Pipes, phases, cards, or automations — see `pipefy-pipes-and-cards`, `pipefy-automations`.
- Raw GraphQL when a portal tool exists — prefer the tools below.
- Bootstrapping a portal via undocumented `createInterface` GraphQL — always use **`create_portal`**.

---

## Prerequisites

- **Organization id:** UUID or **numeric org id** from the organization lookup or the Pipefy URL (examples below use fictional `123456789` per [`fixture_ids.py`](https://github.com/pipefy/ai-toolkit/blob/main/packages/sdk/tests/_shared/fixture_ids.py)). SDK resolves numeric ids before Interfaces calls. The org you pass to **`list_portals`** / **`create_portal`** must be the same org your token can write on.
- **Portal writes:** token needs **`create_portal`** and/or **`manage_portals`** on that org. Many service accounts only have pipe/card scope on their default org → `PERMISSION_DENIED` on portal mutations even when reads succeed elsewhere.
- **One main portal per org** — `create_portal` is idempotent (second call returns the same portal UUID).

### Confirm access before writes

Reads on the wrong org can succeed while Interfaces writes fail. Before page/element/sub-portal mutations:

1. Call **`list_portals`** with the intended `organization_uuid`.
2. Ensure the token is meant for that org (service account email vs human user on a different org is a common mismatch).
3. Prefer an org where the account has **`manage_portals`** and portal admin in Pipefy (not only `canManagePortals` on a read query from another org).

If **`update_portal`** or **`delete_portal`** returns `PERMISSION_DENIED` but the user insists the org role is correct: Pipefy may require **`joinAsAdmin`** on that portal interface for service accounts (Interfaces mutation, not shipped as MCP/CLI). The user must join as portal admin once in the UI (or via GraphQL) per portal UUID before SA writes succeed.

---

## How portals are organized

| Concept | What to expect |
|--------|----------------|
| **Main portal** | At most **one** per org (`subType: portal`). Created with **`create_portal`** (`findOrCreateInterfaceByTemplate`). |
| **`list_portals`** | Usually **one row** — the main portal only (filter `portal`). Sub-portals do **not** appear here. |
| **Sub-portals** | Separate entities (`create_sub_portal`). Listed under **`get_portal` → `subPortals[]`**. |
| **UI on the main hub** | Creating sub-portals does **not** add tiles to the main page. You must **publish** (or attach) on a **`forms`** element via **`publish_sub_portal`** / **`update_sub_portal_element`**. |
| **End-user visibility** | Sub-portals with **`published: false`** exist in the API but are **invisible to portal visitors** until published. |
| **Public main hub** | Main portal **`published`** is always `true` on `get_portal`. **Public** access = **`update_portal(visibility="public")`**, not the `published` flag. |

### Main portal lifecycle

- **Prefer `update_portal`** on an existing main portal over **delete + `create_portal`** on orgs you reuse for testing.
- **`delete_portal`** on the main removes one interface UUID; **orphan sub-portals** can remain unless deleted first.
- After deleting the main, **`create_portal`** may fail with **`Menu already created`** (org menu state persists while `mainPortal` is null). Recovery: delete orphan sub-portals, use Pipefy admin/support, or bootstrap content on the surviving UUID — do **not** switch to raw **`createInterface`**, which leaves a skeleton main page (`"Page"`, **0 elements**) and a broken builder; idempotent **`create_portal`** will keep returning that UUID.

### Empty main page

If the first page has no forms element, use `create_portal_element` with `type: forms` on that page. Attach, publish, and unpublish accept elements only from `get_portal` → `pages[0].elements`. A new page after the first page cannot supply a publish slot. If the portal has no pages, create its first page with `create_portal_page`.

---

## Schema notes

| Topic | Rule |
|-------|------|
| **`published` on list** | **`list_portals` does not return `published`** — call **`get_portal`**. |
| **Sub-portal in layout** | Tiles may appear under **`pages[].elements[]`** with `type: subPortal` even when top-level `subPortals[]` is empty. |
| **Publish wire** | Use `publish_sub_portal` / `update_sub_portal_element` on a `forms` element from `pages[0].elements`. Elements on later pages are not supported. `create_portal_element` with `type: subPortal` is not a substitute for publish. |
| **Element metadata** | **`update_portal_element`** is **replace-all** — send the full `metadata` JSON every time. |
| **Metadata keys** | `forms` → `name` (not `formId`); `link` → `linkName` / `linkUrl` (not `url` / `label`). |
| **Layout JSON** | **`update_portal_page_layout`** expects an **array** of row objects. Each row needs a non-empty `id`, `type: "row"`, and `children` as non-empty strings. Copy the target **`pages[].layout`** from **`get_portal`**. `metadata.gridMap` gives element dimensions, not placement. The API stores any JSON here verbatim, so a wrapper or an incomplete row replaces the grid. The toolkit rejects a non-array and any incomplete row locally, and still accepts `[]` as an empty page; never bypass it with raw GraphQL. |
| **Page grid vs elements** | **`create_portal_element`** leaves the layout grid untouched unless you pass `element_id` + `layout` (existing rows plus a row listing the new id); **`duplicate_portal_element`** appends layout rows; **`delete_portal_element`** leaves layout refs unless you pass `layout` (existing rows with the element removed); orphan refs can break the portal viewer (HTTP 500). |

---

## Tools needed

| Operation | Read-only |
| ------------ | ----------- |
| `list_portals` | Yes |
| `get_portal` | Yes |
| `create_portal` | No |
| `update_portal` | No |
| `delete_portal` | No |
| `create_portal_page` | No |
| `update_portal_page` | No |
| `delete_portal_page` | No |
| `sort_portal_pages` | No |
| `update_portal_page_layout` | No |
| `create_portal_element` | No |
| `update_portal_element` | No |
| `delete_portal_element` | No |
| `duplicate_portal_element` | No |
| `create_sub_portal` | No |
| `update_sub_portal_element` | No |
| `publish_sub_portal` | No |
| `unpublish_sub_portal` | No |
| `delete_sub_portal_element` | No |
| `delete_sub_portal` | No |

Element `type` values (15): `text`, `table`, `field`, `embedLink`, `embedVideo`, `embedImage`, `button`, `divider`, `link`, `forms`, `pages`, `subPortal`, `automationButton`, `contentBlock`, `document`.

---

## Steps — happy path (main portal + sub-portal publish)

1. **List or bootstrap the main portal**

   Operation arguments:

   ```text
   list_portals(organization_uuid="123456789")
   ```

   Expect **at most one** main portal row. If none:

   Operation arguments:

   ```text
   create_portal(organization_uuid="123456789")
   ```

   Capture `uuid` where `subType` is the main portal.

2. **Inspect structure**

   Operation arguments:

   ```text
   get_portal(portal_uuid="<MAIN_PORTAL_UUID>")
   ```

   Read the first page, `pages[0]`, and its forms element IDs. If it has no forms element, add one on that page.

3. **Optional — add a `forms` element** (if no templated `forms` slot exists)

   Use `pages[0].uuid` as `<PAGE_ID>`. Include the element in the page layout when visitors need a visible tile.

   Operation arguments:

   ```text
   create_portal_element(page_id="<PAGE_ID>", type="forms", metadata={"name": "Request access", "gridMap": {"height": 66, "columns": 4, "minColumns": 4}})
   ```

   If **`create_portal_element`** returns an opaque or `INTERNAL_SERVER_ERROR` from Interfaces, **`duplicate_portal_element`** from an existing link on the **same** `portal_uuid` and `page_id` instead of retrying create blindly.

4. **Create a sub-portal**

   Operation arguments:

   ```text
   create_sub_portal(main_portal_uuid="<MAIN_PORTAL_UUID>", name="Partner hub")
   ```

   Capture the sub-portal `uuid`. **`get_portal` will list it under `subPortals[]` with `published: false`** — the main hub UI is unchanged until step 5.

5. **Publish on a `forms` element**

   Operation arguments:

   ```text
   publish_sub_portal(portal_uuid="<MAIN_PORTAL_UUID>", element_id="<FORMS_ELEMENT_ID>", sub_portal_uuid="<SUB_PORTAL_UUID>")
   ```

6. **Verify publish state**

   Operation arguments:

   ```text
   get_portal(portal_uuid="<MAIN_PORTAL_UUID>")
   ```

   Make sure that the target `subPortals[].published` is `true`. Also make sure that the forms element metadata links to the intended sub-portal. Visitor access depends on the element layout and hub visibility rules.

7. **Optional — make the main hub public**

   Update `<MAIN_PORTAL_UUID>` with `visibility="public"` through `update_portal` (SDK argument: `interface_uuid`; MCP argument: `portal_uuid`).

---

## Steps — pages, layout, and safe edits

Use a **disposable page** for element/layout experiments on a shared org main portal:

1. **`create_portal_page`** with a unique title (e.g. `Agent smoke 2026-06-01`).
2. Run **`create_portal_element`**, **`update_portal_element`**, **`duplicate_portal_element`**, **`update_portal_page_layout`** on that page only.
3. Review and approve deletion of the disposable page, then use `delete_portal_page`.

**`duplicate_portal_element`:** `element_id`, `portal_uuid`, and `page_id` must refer to the **same page** that already contains the source element (duplicate on the same page, not cross-page).

**`update_portal_page_layout`:** read the target `pages[].layout` from **`get_portal`** and preserve its row IDs, child element UUIDs, and unaffected rows. Send the complete array with only the intended order/grouping changes; then re-read and compare. `elements[].metadata.gridMap` (`height`, `columns`, `minColumns`) describes dimensions, so it cannot reconstruct row order or grouping. Preserve the full metadata when resizing an element. If the layout is unavailable, stop the positional edit instead of guessing. Never wrap the array in `{ "rows": [ ... ] }`.

MCP:
```
get_portal portal_uuid="<portal_uuid>"
update_portal_page_layout page_id="<page_uuid>" layout=[<complete edited rows from that page>]
get_portal portal_uuid="<portal_uuid>"
```

CLI:
```bash
pipefy portal get <portal_uuid> --json
pipefy portal page layout update --page-id <page_uuid> --layout '[<complete edited rows from that page>]' --json
pipefy portal get <portal_uuid> --json
```

**`create_portal_element` with placement:** read `pages[].layout`, generate a UUID for `element_id`, append or insert a row `{ "id": "<new row uuid>", "type": "row", "children": ["<element_id>"] }`, and pass both `element_id` and the complete `layout`. Without `layout` the element is created but stays off the grid. Re-read and compare.

MCP:
```
create_portal_element page_id="<page_uuid>" type="link" metadata={...} element_id="<element_id>" layout=[<existing rows>, {"id": "<row uuid>", "type": "row", "children": ["<element_id>"]}]
```

CLI:
```bash
pipefy portal element create --page-id <page_uuid> --type link --metadata '{...}' --element-id <element_id> --layout '[<existing rows>, {"id": "<row uuid>", "type": "row", "children": ["<element_id>"]}]' --json
```

**`delete_portal_element` with pruning:** read `pages[].layout`, remove `element_id` from every row's `children`, and pass the complete array as `layout`. The grid and the element change in one call, so no row is left pointing at a deleted element. A layout that still lists `element_id` is rejected. Re-read and compare. The MCP and CLI references show the delete call with `layout`.

**`sort_portal_pages`:** pass a non-empty `page_ids` list with no duplicates. If the response exposes nested `success: false`, treat the operation as failed.

**Link element metadata (create/update, full replace):**

```json
{
  "gridMap": { "height": 64, "columns": 4, "minColumns": 4 },
  "linkUrl": "https://example.com",
  "linkName": "Example link"
}
```

---

## Steps — unpublish or remove sub-portal

**Unpublish** (keeps sub-portal entity; visitors lose access):

Operation arguments:

```text
unpublish_sub_portal(portal_uuid="<MAIN_PORTAL_UUID>", element_id="<FORMS_ELEMENT_ID>")
```

**Detach** element wiring with `delete_sub_portal_element` after reviewing the impact and obtaining approval.

**Delete sub-portal interface** with `delete_sub_portal` (irreversible); review and approve before deletion.

---

## Success criteria

- `list_portals` returns the org main portal (typically one row); `create_portal` returns the same UUID on repeat.
- `get_portal` shows expected `pages` / `elements` after writes.
- After **`create_sub_portal`**, sub-portal exists in API but **`published: false`** until publish.
- After publish: **`subPortals[].published`** is `true` and the main page shows the wired **`forms`** slot.
- After unpublish: **`published`** is `false` without deleting the sub-portal entity (unless you called `delete_sub_portal`).
- After layout/element edits on a disposable page, main portal pages used in production still open in the builder (no HTTP 500).

---

## Failure modes

| Symptom | Likely cause | Recovery |
|---------|----------------|----------|
| `PERMISSION_DENIED` on writes | Wrong org, missing `manage_portals`, or SA not joined on interface | Same org as `list_portals`; user runs portal admin join; try human admin token |
| Reads OK, writes fail on `admin` org | Token is human on org A, numeric id is org B | Align `organization_uuid` with token membership |
| `Menu already created` on `create_portal` | Main deleted but org menu state remains | Delete orphan sub-portals; avoid raw `createInterface`; bootstrap with `create_portal_page` on existing UUID |
| Main page empty in builder | Portal created outside `create_portal` template path | `create_portal_page` (title only) for templated elements |
| `published` missing on list | Expected | `get_portal` |
| Many subs in `get_portal`, empty main UI | Sub-portals not published to `forms` slots | `publish_sub_portal` per sub + `forms` `element_id` |
| Publish or unpublish rejected | The selected element is outside the first portal page or the API rejected the request | Use a forms element from `get_portal` → `pages[0].elements`. Read the result and stored state. |
| `subPortals[]` empty but UI shows tile | Linked under `pages[].elements` | Inspect `type: subPortal` in `elements[]` |
| `create_portal_element` opaque / 500 | Interfaces instability on some orgs | `duplicate_portal_element` from existing widget on same page |
| Portal viewer HTTP 500 | Orphan `layout` children or wrong layout shape | Copy/fix layout from `get_portal`; delete disposable smoke page |
| Nested `success: false` | API rejected mutation | Read `error.message`; do not assume top-level success |
| Validation on element | Wrong metadata keys or partial update | Full metadata blob; `linkName` / `name` per type |

---

## See also

- [`docs/mcp/tools/portal.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/mcp/tools/portal.md) — endpoints, wire naming, maintainer introspection
- `pipefy-introspection` — verify Interfaces / internal_api mutations before changing tools
