# ADR-0006: The envelope states the outcome, and a partial write says so

Status: Accepted
Target release: none

## Status notes

The envelope migration is deferred.

## Context

Every MCP tool answers in one envelope, which `Response shape` in [`architecture.md`](../architecture.md#response-shape) describes: `success: true` with `data`, or `success: false` with an `error`. The boolean claims more than some calls can deliver, and `QR-12` demands that a response never reports success for a part that did not succeed.

The maintainer already settled reads. A read that names a denied resource fails as a denial, and a read over a set returns only what the caller may see. That rule holds a read to all or nothing, which is what [Google AIP-231](https://google.aip.dev/231) requires of a batch get: "it must fail for all resources or succeed for all resources (no partial success)."

A write cannot always be held to all or nothing. `create_service_account` with `pipe_ids` creates the account, and then adds it to each pipe. If one pipe refuses, the account already exists, so the call cannot become a clean failure. Today the tool returns `success: true` and records each pipe's result in a `pipe_memberships` list, so a caller that reads `success` alone takes the refused pipe for a success.

The same misreading happens one layer down, in the MCP protocol. The [specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) separates a protocol error, such as an unknown tool, from a tool execution error, which a tool returns in a normal result with `isError: true`. Revision 2025-11-25 clarified that an input validation error is a tool execution error, "to enable model self-correction" (SEP-1303, in the [changelog](https://modelcontextprotocol.io/specification/2025-11-25/changelog)). Our server sets `isError: false` on every result that a tool returns, the failure envelope included. Only `short_circuit_error` in `packages/mcp/src/pipefy_mcp/core/tool_middleware.py` sets `isError: true`, when a middleware stops a call before the tool runs. A client or a policy engine that reads `isError` therefore sees every failure inside a tool as a success.

Published APIs answer a partial result in three ways:

- All or nothing. AIP-231 for a batch get, and [JSON:API](https://jsonapi.org/format/1.1/), where "the members `data` and `errors` MUST NOT coexist in the same document." AIP-233 and AIP-234 allow a partial batch create or update only in the asynchronous form, which reports each failed item in a `failed_requests` map.
- Per-item outcomes under a neutral top level. AWS SQS `SendMessageBatch` returns `Successful` and `Failed`, and its reference warns that a caller "should check for batch errors even when the call returns an HTTP status code of `200`". S3 `DeleteObjects` returns `Deleted` beside `Errors`. HTTP 207 Multi-Status reports "multiple independent operations" ([RFC 4918, section 11.1](https://www.rfc-editor.org/rfc/rfc4918#section-11.1)). A [GraphQL](https://spec.graphql.org/October2021/) response "may contain both a partial response as well as any field errors", and each error tied to a field must carry its `path`.
- A success flag with a warning. The [Slack Web API](https://docs.slack.dev/apis/web-api/) returns `ok: true` with a `warning` code. That is our shape today, and it carries the same flaw.

## Decision

The top level of the envelope states the outcome of the whole call, and it never claims more than happened.

- A `status` of `ok`, `partial`, or `error` replaces the `success` boolean. `ok` means that every part succeeded. `error` means that nothing changed, or that a read was refused. `partial` means that a write happened in part.
- A `partial` result carries an outcome per item in `data`, and each failed item carries an error in the same shape as the top-level `error`. A caller who acts on a `partial` result reads those items.
- `isError` follows `status`. A tool sets it to `true` for `error`, and to `false` for `ok` and `partial`, because a partial write is a call that ran and changed something. The envelope also travels as `structuredContent`, so a client that reads typed output finds the same outcome there.
- A read stays all or nothing, as `Response shape` states, so a read never returns `partial`.
- An access probe reports access as data. `validate_knowledge_base_access` and the LLM provider probe exist to say what the caller may reach, so a denial is their answer and not their failure. A probe that ran returns `ok`, with the denial in its `problem` field. A probe that could not run returns `error`.

## Consequences

`QR-12` is satisfied for in-tool failures, at both layers: a caller that reads `status`, or a client that reads `isError`, never takes a failed call for a success. It is partly satisfied for a partial write. A client that reads `isError` alone sees a `partial` result as a success, so the per-item outcomes reach a caller only through `status` and `data`.

`QR-1` is satisfied in the form that the protocol expects. An invalid argument already returns a failure envelope that names the field, and it now also returns `isError: true`, which matches SEP-1303.

`QR-8` does not change. A denial still states its cause and its next step, now under `status: error`.

The change breaks the contract of every tool, because every caller that reads `success` must read `status` instead. That makes it cheapest before v1.0, the same argument that ADR-0003 makes for the destructive gate. After v1.0 it would violate `QR-11` and would need a deprecation period first.

This decision covers the MCP server alone. The SDK raises an exception on a failure and returns a value on success, so it has no envelope to change. The CLI prints the SDK payload, and it has no exit code for a partial write. [`docs/parity.md`](../../parity.md) records that difference, and a later decision settles it.

The specification moves on its own schedule. Revision [2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog) keeps the split between the two kinds of error and the `outputSchema` rule, and it lets `structuredContent` be any JSON value. The envelope is an object, so this decision holds under both revisions.

## Target rule

No living doc carries this rule until the migration lands. On adoption, `Response shape` in [`architecture.md`](../architecture.md#response-shape) states it:

- The top level states the outcome of the whole call as `ok`, `partial`, or `error`, and `isError` is `true` for `error` alone.
- A partial write carries an outcome per item, and a read is never partial.
