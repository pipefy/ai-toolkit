# Decision records

These are the decision records behind the toolkit design: how the SDK, MCP server, and CLI are layered, how their contracts are shaped, and how the code is structured. Each record holds one decision with its context and reasoning. A record becomes immutable once it is adopted.

Each record opens with two header lines:

- `Status` is `Proposed`, `Accepted`, or `Superseded by ADR-NNNN`. A proposed record carries planned work, and it is the only kind of doc that does. An accepted record is adopted.
- `Target release` names the version that is meant to ship the decision, or `none`.

After a record is accepted, only these two lines change. Git holds the author and the date of each record. Whether the code has caught up with an accepted record is current state, so `Risks and technical debt` in [`architecture.md`](../architecture.md#risks-and-technical-debt) tracks it, not the header.

Every record is accepted. The rule each decision produces lives in a living doc, and that is what a contributor follows day to day. A record can defer part of its decision, and its row names the deferred part. The record keeps the why. To change an adopted decision, add a new record that supersedes the old one. Do not edit an adopted record, and do not change its decision by a refactor. See [`authoring.md`](../authoring.md).

| ADR | Decision | Status | Deferred part | Current rule |
|---|---|---|---|---|
| [0001](0001-layered-responsibility.md) | Layered responsibility | Accepted | none | [`architecture.md`](../architecture.md) |
| [0002](0002-typed-single-form-contract.md) | Typed, single-form contract | Accepted | the typed-output rollout | [`conventions.md`](../conventions.md) |
| [0003](0003-mcp-tools-express-outcomes.md) | MCP tools express outcomes | Accepted | the consolidation, the resolver migration, and the gate reshaping | [`conventions.md`](../conventions.md) |
| [0004](0004-vertical-slice-structure.md) | Vertical-slice structure and naming | Accepted | the slice folders and the `Pipefy` rename | [`architecture.md`](../architecture.md), [`conventions.md`](../conventions.md) |
| [0005](0005-package-split.md) | One package per way in, over shared libraries | Accepted | none | [`architecture.md`](../architecture.md#package-decomposition) |
| [0006](0006-envelope-outcome.md) | The envelope states the outcome | Accepted | the envelope migration | [`architecture.md`](../architecture.md#response-shape) |

The governance rule that says when to refactor lives in [`conventions.md`](../conventions.md), not as a separate record.

## Rollout epics

The deferred work of these decisions is tracked in epics outside the records:

- Outcome-tool audit and consolidation (0003).
- Resolver migration for the two tools that ask for a missing input (0003).
- Destructive-gate reshaping: a declared effect on every write, and a dry run in place of the confirmation gate (0003).
- Vertical-slice refactor and the `Pipefy` root rename (0004).
- An import contract per package, so a check holds the role direction outside `packages/mcp` (0004).
- Typed-output rollout, resource by resource with Card first (0002).
- The envelope migration from `success` to `status`, with `isError` set from the outcome (0006).

The step-by-step exploration behind these decisions is in the repository history.
