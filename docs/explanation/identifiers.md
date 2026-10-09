---
title: Identifiers
description: The four forms of a Pipefy ID, and when a field takes its slug or its internal_id.
---

# Identifiers

Pipefy names objects in four forms. The MCP server, the CLI, and the SDK all take these forms. This page explains each form, and when a field takes its slug or its internal_id.

To learn which form an argument wants, read its description in the input schema of the tool or in the `--help` of the command. For example, `pipefy agent list --help` describes `--repo` as "Pipe UUID (repoUuid)".

## The four forms

| Form | Looks like | What it is |
| --- | --- | --- |
| **numeric id** | `"303088927"` | The numeric database id of a pipe, card, organization, automation, and most other objects. GraphQL types it as `ID`, so pass it as a string. |
| **uuid** | `"5f66417e-5adc-4c83-908f-0b888493c847"` | The UUID of a pipe, organization, portal, AI agent, knowledge-base item, or log. |
| **slug** | `"document_upload"` | The human-readable id of a field. GraphQL returns it as the `id` of a field. |
| **internal_id** | `"429659034"` | The numeric id of a field. GraphQL returns it as the `internal_id` of a field. |

A pipe has both a numeric id and a uuid. A field has both a slug and an internal_id. To find them, read a pipe with `get_pipe` (`pipefy pipe get`) and the fields of a phase with `get_phase_fields` (`pipefy field list --phase`).

## Slug or internal_id for a field

A field takes its **slug** when you edit a value on one card or one table record. A field takes its **internal_id** when an automation, a field condition, or an AI prompt refers to the field.
