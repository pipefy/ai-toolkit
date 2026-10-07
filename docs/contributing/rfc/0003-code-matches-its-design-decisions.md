# RFC-0003: The code matches its design decisions

Status: Draft
Author: Gabriel Custodio
Created: 2026-10-07
Discussion: the pull request that adds this file

## Summary

The toolkit's code should follow the six design decisions in ADRs 0001 to 0006, and a check should show how far it still is from each one. The decisions are written down, but part of each one is deferred, and nothing measures the distance between the code and the decision. This RFC proposes that each deferred part gets an exit criterion that a check can verify, a tracking issue, and a baseline that only shrinks.

## Problem

ADRs 0001 to 0006 record how the SDK, the MCP server, and the CLI are layered, how their contracts are shaped, and how the code is structured. They exist on the `docs/v1-groundwork` branch, not on `dev`, and four of the six defer part of their decision to later work:

| ADR | Decision | Deferred part |
|---|---|---|
| [0001](../adr/0001-layered-responsibility.md) | Layered responsibility | none |
| [0002](../adr/0002-typed-single-form-contract.md) | Typed, single-form contract | The typed-output rollout, resource by resource with Card first |
| [0003](../adr/0003-mcp-tools-express-outcomes.md) | MCP tools express outcomes | The outcome-tool consolidation, the resolver migration for two tools, and the reshaping of the destructive gate into a declared effect and a dry run |
| [0004](../adr/0004-vertical-slice-structure.md) | Vertical-slice structure and naming | The slice folders, the `Pipefy` root rename, and an import contract per package |
| [0005](../adr/0005-package-split.md) | One package per way in, over shared libraries | none |
| [0006](../adr/0006-envelope-outcome.md) | The envelope states the outcome | The envelope migration from `success` to `status`, with `isError` set from the outcome |

The ADR index lists seven rollout epics for these deferred parts. Three problems follow from that state:

1. **No one can tell how much work is left.** An epic is a sentence. It does not say which tools, modules, or packages still follow the old shape, so progress is a matter of opinion.
2. **New code can follow the old shape.** Except for the import contracts inside `packages/mcp`, no check rejects a new tool that returns `success` instead of `status`, or a new module outside its slice. Each such change adds to the deferred work.
3. **The decisions are not visible on `dev`.** Contributors who work from `dev` cannot see the ADRs, so they cannot follow or argue with them.

## Goals

1. **Every accepted decision is visible on `dev`.** ADRs 0001 to 0006 live in `docs/contributing/adr/` on `dev`, with the conventions and the architecture page they cite.
2. **Every deferred part has a measured distance.** A check lists the places that do not follow the decision yet, so the remaining work can be read from the code.
3. **The distance only shrinks.** New code follows each decision from the day its check lands.

When the baseline for an ADR's deferred part is empty, its `Target release` line changes from `none` to the version that shipped it.

## Non-goals

- Changing any of the six decisions. A change to a decision needs a new ADR that supersedes the old one.
- A date for each migration. The order and the pace come from refinement of each tracking issue.
- The documentation and testing work in RFC-0001 and RFC-0002.

## Proposal

### Part A: land the decisions on `dev`

A base pull request adds `docs/contributing/` to `dev`: `conventions.md`, and `architecture.md` moved from `docs/architecture.md`. A second pull request adds ADRs 0001 to 0006 and their index with `Status: Proposed`. The ADRs link to both pages, so the base pull request lands first. Each ADR moves to `Accepted` after its review.

### Part B: one exit check per deferred part

Each deferred part gets a check that lists the places that do not follow the decision. These are the proposed checks. Their first job is to measure the baseline, which no one has counted yet:

| Deferred part | ADR | Proposed check |
|---|---|---|
| Typed-output rollout | 0002 | A test over the tool registry that lists the tools without a typed output schema |
| Outcome-tool consolidation | 0003 | A test that lists the tools that the ADR marks for merging and that are still registered |
| Resolver migration | 0003 | A test that lists the tools that still ask the client for a missing input |
| Destructive-gate reshaping | 0003 | A test over the registry that lists the write tools without a declared effect |
| Slice folders | 0004 | An import-linter contract per package, with the current violations in `ignore_imports` |
| `Pipefy` root rename | 0004 | A test that lists the public names that still use the old root |
| Envelope migration | 0006 | A test over the registry that lists the tools whose response has `success` and no `status` |

Each check follows the pattern from RFC-0002: a committed baseline lists today's violations, a new violation fails CI, and a fixed violation must leave the baseline in the same pull request. Import-linter supports this pattern already through `ignore_imports`.

### Part C: one tracking issue per deferred part

Each deferred part gets a GitHub issue with fixed sections: the problem with evidence, a link to its ADR, the exit check from Part B, the non-goals, and the open questions. The issue links to the ADR and does not copy it, so the decision has one home. Refinement passes add sub-issues, one per pull request, and each sub-issue removes entries from the baseline.

An umbrella issue holds the seven tracking issues as sub-issues, and a milestone collects them all. The milestone closes when every baseline is empty.

## Rollout

| Phase | Scope | Gate to the next phase |
|---|---|---|
| 0. Visible | Part A: the base pull request, then ADRs 0001 to 0006 as `Proposed` | The ADRs are accepted on `dev` |
| 1. Measured | Part B: one pull request per check, each with its baseline | Every deferred part has a check in CI |
| 2. Tracked | Part C: the umbrella issue, the seven tracking issues, and the milestone | Each tracking issue links its check |
| 3. Converged | Refinement and migration, one ADR at a time, starting with the one whose baseline is smallest | Every baseline is empty |

Phase 1 can start for one ADR as soon as that ADR is accepted, so phase 0 and phase 1 can overlap.

## Alternatives considered

**Track the epics as issues, with no checks.** This is close to the current state. Each issue would need a person to judge progress, and new code could still grow the deferred work.

**Migrate each decision in one large pull request.** A single migration per ADR would end the split state sooner. Each one would touch most tools at once, which makes review hard and conflicts likely. A baseline allows the same migration in small steps.

**Keep the ADRs on the `docs/v1-groundwork` branch as the target.** Contributors on `dev` would not see them, and the branch would drift from the code it describes.

## Risks and costs

- **Behavior changes for clients.** The envelope migration and the gate reshaping change what clients receive. Each step needs a changelog entry and may need the deprecation window that `DEPRECATION.md` defines.
- **Checks that are hard to write.** Some deferred parts, such as the consolidation, depend on a list in the ADR more than on a property of the code. Their check reads that list, so the list must stay current.
- **Parallel work in the same files.** Several migrations touch the tool modules. One ADR at a time, as phase 3 says, limits the conflicts.

## Open questions

- Does each ADR go through review as it stands, or does review change parts of them before they are accepted?
- Which ADR migrates first? The baselines from phase 1 should decide, but a client deadline can override them.
- Does the milestone stay an initiative bucket, or does the repository move milestones to releases and track the initiatives in a GitHub project?

## References

- [Kubernetes Enhancement Proposals](https://github.com/kubernetes/enhancements/tree/master/keps), for tracking issues and graduation criteria
- [Rust RFC process](https://github.com/rust-lang/rfcs), for tracking issues after acceptance
- [import-linter](https://import-linter.readthedocs.io/), for contracts with ignored imports
- *Building Evolutionary Architectures*, Neal Ford, Rebecca Parsons, and Patrick Kua, 2017, for fitness functions

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/contributing/rfc/0003-code-matches-its-design-decisions.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/contributing/rfc/0003-code-matches-its-design-decisions.md).
