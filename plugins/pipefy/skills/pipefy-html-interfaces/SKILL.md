---
name: pipefy-html-interfaces
description: >
  Use when the user wants to create, read, or rewrite a Pipefy HTML interface:
  a standalone page whose content is one HTML document, optionally showing live
  data from pipes and tables. Covers choosing data sources, creating the page,
  and rewriting it. Needs HTML interfaces enabled on the organization. For the
  main portal, its grid-layout pages, and sub-portals, use `pipefy-portal-setup`.
tags: [pipefy, interfaces, html, pages, data-sources]
metadata:
  surfaces: "mcp cli"
---

# HTML interfaces

MCP clients: read [references/mcp.md](references/mcp.md). CLI users: read [references/cli.md](references/cli.md).

An HTML interface is a page whose single element is a `customCode` element holding one HTML document. The element can declare data sources (pipes or tables) that the HTML reads by source id. Writing the HTML publishes it: there is no draft.

## When to use

- "Build a page that shows our open requests", "make a dashboard page from this pipe."
- "Change the layout / copy / colors of my HTML interface."
- "Add the table X as a data source to my page."
- "List my HTML interfaces", "show me the HTML of page Y."

If the user asks for a "page" and it is unclear whether they mean a standalone HTML page or a page inside their main portal, ask before doing anything.

**When not to use:** the main portal, its grid-layout pages and elements, and sub-portals live in `pipefy-portal-setup` (`list_portals` and `get_portal` cover those, and `get_interface_html` refuses them). Pipes, fields, and cards themselves live in `pipefy-pipes-and-cards`. Never change an HTML interface with the portal page or element tools: they accept its `customCode` element, but they replace its metadata and sources without the checks the tools here make.

## Prerequisites

- **HTML interfaces enabled on the organization.** Pipefy enables them per organization; organization admins cannot turn them on. If a call fails because the feature is not enabled, stop and tell the user to ask Pipefy to enable HTML interfaces for their organization. No tool can enable them.
- **Organization id.** `list_interface_repos` accepts only the numeric organization id; `create_html_interface` and `list_interfaces` accept the numeric id or the uuid. Users usually give the uuid or the name, so look up the numeric id with `list_organizations` (its `id`) and use it everywhere.
- **Admin access to the pipes and tables** the page shows. `list_interface_repos` lists only published pipes and tables the caller administers.

## Operations

| Operation | Read-only | Purpose |
|-----------|-----------|---------|
| `get_interface_html_guidelines` | Yes | The rules the HTML must follow, the `data-pfy-*` vocabulary for binding data, and the filter format; with `include_design_system`, also a design-system catalog. |
| `list_interface_repos` | Yes | Pipes and tables that can be a data source. |
| `get_interface_repo_fields` | Yes | A pipe's or table's custom fields, to pick a source's `fieldKeys`. |
| `list_interfaces` | Yes | The organization's HTML interfaces, with their `visibility`. |
| `get_interface_html` | Yes | One interface's pages, elements, data sources, and live HTML. |
| `create_html_interface` | No | Create an interface and write its first page, with optional sources. |
| `set_interface_sources` | No | Replace an element's data sources. |
| `write_interface_html` | No | Replace and publish an element's HTML. |

## Rules that hold in every flow

- **Read the guidelines first.** Call `get_interface_html_guidelines` before writing any HTML, and follow it. This skill does not repeat the rules: the guidelines are their single source, and they change with the platform. By default it leaves out `designSystem`, a component catalog several times the size of the rules. Ask for it with `include_design_system` only when styling the page.
- **Bind data exactly as `dataPfyVocabulary` says.** It says what each `data-pfy-*` attribute does, for most which element it goes on, and the value it takes. The validator only checks that an attribute is allowed, so it accepts a binding in the wrong place.
- **Every write is live.** `create_html_interface`, `write_interface_html`, and `set_interface_sources` change what visitors see at once. A specific request from the user ("rename the heading to X") is approval for that change. Before anything beyond it, such as rewriting markup they did not mention or removing a source they still use, show the user the change and get their approval.
- **Keep the live page reading only declared sources.** HTML that reads a source id the element does not declare renders blank, with no error. Add a source before writing the HTML that reads it. Remove or rename a source only after the live HTML no longer reads it.
- **Fix every violation before writing again.** A rejected write stores nothing and lists every violation. Fix all of them in one pass, then write again. If the HTML came from the user, show them the violations and a version that follows the rules, and publish only once they agree.

## Steps — create a page

1. **Read the rules**, and the design-system catalog if you will style the page:

   ```text
   get_interface_html_guidelines
   get_interface_html_guidelines include_design_system=true
   ```

2. **Check the name is free.** If an interface with that name exists, ask the user whether to change it (see the next section) or create another.

   ```text
   list_interfaces organization_uuid=<org_id> search_term=<name>
   ```

3. **Pick the data** (skip for a page without live data). List candidate repos, then the fields of each one you use:

   ```text
   list_interface_repos organization_id=<org_id> repo_name=<name_fragment>
   get_interface_repo_fields repo_uuid=<repo_uuid>
   ```

   A source is `{"id", "name", "repoId", "fieldKeys", "filters"}`. `repoId` is the repo's `uuid`. `fieldKeys` holds 1 to 30 keys: a custom field's `uuid` (not its `id`), or a built-in key such as `title` (the guidelines list built-in keys under `filters.fixedColumnNames`). `filters` is optional and follows the guidelines' filter format. `id` and `name` are unique within the element; the HTML reads the source by `id`. An element holds at most 10 sources.

4. **Write the HTML** against the guidelines, binding each source by its `id` with the `dataPfyVocabulary` attributes.

5. **Create the interface** with its sources and HTML in one call:

   ```text
   create_html_interface organization_uuid=<org_id> name="Open requests" html=<document> data_sources=[{"id": "requests", "name": "Open requests", "repoId": <repo_uuid>, "fieldKeys": ["title", <field_uuid>]}]
   ```

   The result carries the new interface's `uuid` and its page and element ids. Tell the user the interface's name and `uuid`.

## Steps — change an existing page

1. **Find it and read it:**

   ```text
   list_interfaces organization_uuid=<org_id> search_term=<name_fragment>
   get_interface_html interface_uuid=<interface_uuid>
   ```

   Use the element whose `type` is `customCode` on the page the user means. If the interface has more than one page or `customCode` element, list them and ask which one. Take `page_id` from `pages[].uuid`, `element_id` from `pages[].elements[].uuid`, the current sources from the element's `dataSources`, and note its `htmlDocument.contentHash`.

2. **Add sources** if the new HTML needs more data. For a field the page does not read yet, find its uuid with `get_interface_repo_fields` on the source's `repoId`. Send the complete list, the current sources plus the new ones: it replaces the element's sources, and `[]` removes them all. Sources read with `get_interface_html` can be sent back as read. Keep the `id` of every source you keep.

   ```text
   set_interface_sources interface_uuid=<interface_uuid> page_id=<page_id> element_id=<element_id> data_sources=[...]
   ```

3. **Write the new HTML**, starting from the document you read. Right before writing, read the interface again: if `contentHash` changed, someone else edited the page, so start again from the new document and show the user the change.

   ```text
   write_interface_html page_id=<page_id> element_id=<element_id> content=<document>
   ```

4. **Remove or rename sources** the new HTML no longer reads, if the user wants them gone, with one more `set_interface_sources` call that sends the complete list.

## Success criteria

- The create or write returns success, with no violations.
- `get_interface_html` shows the new document and the expected `dataSources` on the element.
- Every source id the HTML reads is in the element's `dataSources`.

## Failure modes

- **The create succeeded but the write failed.** The interface exists with a blank page, and the error gives its `uuid`, `page_id`, and `element_id`. Resolve the error (fix the HTML for a rejection), then call `write_interface_html` with those ids. Do not call `create_html_interface` again: it would create a second, orphaned interface.
- **The create returned no page to write into.** The interface may exist anyway, and the error gives its `uuid`. Check it with `get_interface_html` before doing anything else, and never retry the create blindly.
- **The create failed and the error has no `uuid`.** The interface may exist anyway. Search for it with `list_interfaces` by name before any retry, and create again only if no new interface with that name appears.
- **The HTML was rejected on a write.** Nothing was stored. Fix every listed violation against the guidelines and write again.
- **A write failed without listing violations.** Read the page with `get_interface_html` to see what is stored, then write again once. If it fails again, stop and tell the user.
- **The page renders blank sections.** The HTML reads a source id that the element does not declare, or one that was renamed or removed. Compare the HTML with `dataSources` from `get_interface_html`, then fix the sources or the HTML.
- **A duplicate interface exists.** Show the user both, with names and uuids. With their approval, delete the extra one with `delete_portal`, which takes the interface's uuid as `portal_uuid` and asks for confirmation.
- **A repo is missing from `list_interface_repos`.** It is unpublished, or the caller is not its admin. An empty list can also mean the organization id is wrong: the listing does not report an unknown organization or interface.
- **`get_interface_html` refuses the interface.** It is a grid-layout portal or sub-portal; use `pipefy-portal-setup`.
- **Unsure what a source update stored.** `set_interface_sources` returns the sources as sent, not as stored. Read them back with `get_interface_html`.

## See also

- `pipefy-portal-setup`: the main portal, its grid-layout pages and elements, and sub-portals.
- `pipefy-pipes-and-cards`: create the pipes and fields a page reads.
