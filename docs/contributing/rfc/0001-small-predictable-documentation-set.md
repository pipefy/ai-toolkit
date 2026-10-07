# RFC-0001: A small, predictable documentation set

Status: Draft
Author: Gabriel Custodio
Created: 2026-10-07
Discussion: the pull request that adds this file

## Summary

The toolkit's docs should hold only the text that the code cannot state, and each page should sit where a reader expects it. Today the docs repeat facts that the code already owns, so the hand-written pages change almost as often as the code and drift from it. No rule says where a page belongs either, so each page lands where its author chose. This RFC proposes two goals and a set of checks that hold them.

## Problem

### The docs repeat the code

The same behavior is written in 3 to 7 places: the docstring, the CLI help, a guide in `docs/mcp/tools/`, one or more skills, `docs/parity.md`, and sometimes `architecture.md`. Each copy is edited on its own schedule, so the copies drift apart. These statements are false on `dev` at `e85483bf` today:

| Where | What the doc says | What the code does |
|---|---|---|
| `skills/pipes-and-cards/pipefy-pipes-and-cards/references/cli.md:19` | `get_pipe` runs as `pipefy phase get <id>` | `get_pipe` is `pipefy pipe get` |
| `skills/pipes-and-cards/pipefy-pipes-and-cards/references/cli.md:84` | `get_pipe` runs as `pipefy label list --pipe <id>` | That command belongs to `get_labels` |
| `skills/introspection/pipefy-introspection/references/mcp.md:44` | Pass `debug=true` to `execute_graphql` | `execute_graphql` has no `debug` parameter |
| `docs/mcp/tools/cross-cutting.md`, section `extra_input` | Keys that repeat a parameter are ignored | `automation_tools.py` lets the `extra_input` value win, and `field_condition_tools.py` lets the parameter win |
| `docs/mcp/tools/cross-cutting.md`, section IDs | Zero and invalid IDs fail before the network call | `PipefyId` accepts 0 and negative numbers |

Every one of these passed the existing checks, because the checks test names and links, not meaning. A row that pairs a real tool with a real command passes even when it pairs the wrong two.

The commit history shows the same cause from another side. Of the 1,329 commits on `dev`, these Markdown files changed most often, and most of their commits also changed Python code:

| File | Commits | Share that also touch `.py` | What changes |
|---|---|---|---|
| `CHANGELOG.md` | 190 | 71% | One entry per change |
| `README.md` | 85 | 44% | Tool counts and feature lists |
| `packages/mcp/AGENTS.md` | 59 | 77% | Rules that restate the code |
| `docs/parity.md` | 58 | 70% | Table rows: 476 of 536 added lines |
| `RELEASE.md` | 42 | 61% | Release steps |
| `packages/mcp/README.md` | 30 | 70% | Tool lists |
| `docs/config.md` | 25 | 72% | Settings tables |

A file that changes in the same commit as the code is a copy of the code. A generator can keep it current, and a person cannot.

The hand-written corpus is large for a project of this size. On `dev`, `docs/` holds 32 Markdown files with 3,137 lines, and the skills hold 4,426 lines. In `docs/mcp/tools/`, an estimated 40 to 85% of each page restates docstrings. The skills hold 162 rows that map MCP tools to CLI commands, which repeat `docs/parity.md`.

### No rule says where a page belongs

The 32 files in `docs/` on `dev` mix kinds of content at every level. `architecture.md`, `response-typing.md`, and `dependencies.md` are contributor material at the top of the user docs. `MIGRATION.md` and `DEPRECATION.md` are policy pages, and `docs/` has no tutorial for any surface. `docs/mcp/tools/` holds 15 pages that are part reference and part explanation. A reader cannot predict where a fact lives, so they search, and an author cannot predict where a new page goes, so the tree grows by taste.

## Goals

1. **Small.** Hand-written docs keep only what the code cannot say: the reasons behind a design, tutorials, task procedures, and concepts that span many tools. Every fact about one tool, command, or setting comes from the code, through a generator, a `--help` text, or a docstring.
2. **Predictable.** Each page has one kind and one place, set by a rule. A reader finds a fact where its kind says it is, and the tree does not change shape when its authors change.

Each goal has a measure, so a reviewer can tell when the work is done:

| Measure | Today on `dev` | Target |
|---|---|---|
| Hand-written lines in `docs/` and `skills/` | 7,563 | Down, with generated lines counted separately |
| Places that state one tool behavior | 3 to 7 | 1, plus generated copies |
| Hand-kept rows that map a tool to a command | 162 in skills, plus every row of `parity.md` | 0 |
| Pages without a declared kind | 32 | 0 |
| Pages whose path does not match their kind | Not measured | 0 |

Generated pages will grow as hand-written pages shrink. That growth is the intended result, so the measures count the two kinds of lines apart.

## Non-goals

- A rendered docs site. Raw GitHub Markdown needs no build step, and agents read it directly. The Markdown stays the source if a site comes later.
- The rename of the SDK import from `pipefy_sdk` to `pipefy`. `architecture.md` already tracks that gap.
- The workflows and judgment calls inside each skill. This RFC changes only the parts of a skill that restate tools and commands.

## Proposal

The proposal has two parts, one per goal. Each change names the class of defect it removes.

### Part A: generate what the code owns

**A1. Docstrings own single-tool facts.** The MCP client already shows the tool docstring to the model, and `scripts/gen_mcp_reference.py` already renders it into `docs/mcp/reference.md`. The per-tool content in `docs/mcp/tools/` moves into docstrings, and those pages merge into a few explanation pages for concepts that span tools: identifiers, destructive operations, and response shape. Removes: per-tool restatements.

**A2. Each CLI command declares its MCP tool.** A Typer command carries its match, for example `mcp_tool="get_labels"`. A generator renders `docs/parity.md` from that data plus the tool registry, and the `references/cli.md` tables in skills are generated from the same data or replaced with a link. Removes: 349 hand-kept rows (187 in `parity.md` and 162 in skills) and the wrong-pair defect.

**A3. Generated regions inside hand-written pages.** Some pages mix prose with a table that the code owns, such as the settings tables in `docs/config.md`. One script renders every region between a pair of markers:

```markdown
<!-- docgen: cli-commands get_pipe create_pipe -->
...generated table...
<!-- /docgen -->
```

The script has a `--check` mode, one pre-commit hook, and one test. A2 and the `config.md` tables are its first users. Removes: hand-kept tables inside prose pages.

**A4. Rules that span tools become registry-wide tests.** A sentence such as "keys that repeat a parameter are ignored" is first made true in the code, then backed by a test that runs over every registered tool. The page states the rule and links to the test. `TOOL-2` already works this way for annotations. Removes: general rules that are false for some tools.

**A5. Examples run.** `pytest-markdown-docs` runs the Python blocks in tutorials with a client backed by recorded responses. A small collector runs each `console` block of the CLI tutorial through Typer's `CliRunner` and compares the output. Removes: tutorials that break without anyone noticing.

### Part B: place every page by its kind

**B1. Every page declares one kind.** The four kinds come from [Diataxis](https://diataxis.fr/): a tutorial helps the reader learn, a how-to guide helps the reader do a task, a reference gives facts to look up, and an explanation helps the reader understand. Each page states its kind and a one-line summary in front matter:

```markdown
---
kind: how-to
summary: Rotate a service account token without downtime.
---
```

Contributor docs use two more kinds, which Diataxis does not cover: `adr` for a decision record and `rfc` for a proposal.

**B2. The path follows from the audience, the surface, and the kind.** Diataxis sorts content, not directories, so the directories follow the reader instead: first the audience (user or contributor), then the surface (SDK, CLI, or MCP), and the kind sets the file name.

```text
docs/
  README.md               generated index
  quickstart.md           tutorial across all surfaces
  config.md               reference, tables generated
  parity.md               reference, generated
  troubleshooting.md      how-to
  sdk/ cli/ mcp/
    README.md             explanation: what the surface is and when to use it
    tutorial.md           tutorial
    reference.md          reference, generated
    guides/<task>.md      how-to, one task per page
    concepts/<topic>.md   explanation, one topic per page
  contributing/
    architecture.md       explanation, arc42 sections
    conventions.md        reference, rule IDs
    development.md        how-to
    adr/NNNN-<title>.md   adr
    rfc/NNNN-<title>.md   rfc
```

A test reads `git ls-files docs/` and the front matter, and it fails when a page sits outside this tree or its path does not match its kind.

**B3. The index is generated.** `docs/README.md` and the contents table of each surface are rendered from the front matter by the A3 script. Removes: hand-kept indexes.

**B4. Paths stay stable.** A moved or deleted page leaves an entry in a redirect list, and a test fails when a published path disappears without one. External links and agent instructions keep working after the tree changes.

### Principles

Reviewers cite these rules by ID, as they cite `PARSE-3` in `conventions.md`. Each one names its check, because a rule without a check is a wish.

| ID | Rule | Serves | Check |
|---|---|---|---|
| DOC-1 | The code owns every fact it can state. A page links to the generated reference and does not copy it. | Small | Freshness test for each generated page |
| DOC-2 | A rule exists only with a check. | Small | Each rule's `Enforced by:` line |
| DOC-3 | One fact, one home. Other pages link to it. | Small | Review, plus A1 and A2 removing most copies |
| DOC-4 | Docs describe the default branch in the present tense. Only a proposed ADR or an RFC describes planned work. | Predictable | Vale word list |
| DOC-5 | Every page fits one slot in the tree. | Predictable | Tree test (B2) |
| DOC-6 | A page has one kind, declared in front matter. | Predictable | Front matter test (B1) |
| DOC-7 | A page earns its place by serving a task that no other page serves. Delete it, do not archive it. | Small | Review |
| DOC-8 | Every rule and decision says why. | Predictable | `tests/test_adr_index.py` for records |
| DOC-9 | Every link resolves. | Predictable | Link tests and lychee |
| DOC-10 | Every example runs, or is marked as illustrative. | Small | A5 |

## Rollout

The work lands on `dev` as small pull requests, in five phases. Each phase starts after the gate of the phase before it passes.

| Phase | Scope | Gate to the next phase |
|---|---|---|
| 0. Fix | The five false statements in the Problem section | No known false statement remains |
| 1. Checks | Markdownlint, lychee, the link and name tests, and the generated CLI reference, taken from the `docs/v1-groundwork` branch | The `Docs` workflow passes on `dev` |
| 2. Engine | A3 with its first users: A2 and the `config.md` tables | No hand-kept row maps a tool to a command |
| 3. Tree | B1 to B4: front matter, the moves, the generated index, and redirects | Every page has a kind, and the tree test passes |
| 4. Thin pages | A1 and A4: docstrings take the per-tool content, and each cross-tool rule gets its test | No page in `docs/mcp/tools/` restates a docstring |

A5 depends on no phase, so it can land at any time. Phase 4 changes runtime behavior where a rule is not yet true, so its pull requests need a changelog entry and a review by the MCP owners.

## Alternatives considered

**Keep a branch as the target.** Agents would read `docs/v1-groundwork` as the desired state and land pull requests that converge on it. The branch describes a snapshot of the code, and it already lags `dev`. Its pages also read as present-tense fact while describing a future state, which breaks DOC-4. This RFC states the target instead, and the branch stays a source of content.

**Add more name checks and keep the structure.** Name checks catch a renamed tool. They cannot catch a rule that is false, or a row that pairs the wrong tool and command, and those are the defects in the Problem section.

**Organize directories by Diataxis kind.** Four top-level folders (`tutorials/`, `how-to/`, `reference/`, `explanation/`) would mix three surfaces in each folder. A CLI user would then read past SDK and MCP pages in every folder. The Diataxis author also advises against starting from four empty sections. Kind as the file name keeps the surface together.

## Risks and costs

- **Docstrings grow.** A1 moves text into docstrings, and the model reads every docstring on each `tools/list` call. A size budget per docstring limits the cost.
- **Behavior changes in phase 4.** Making a cross-tool rule true can change what clients receive. Each such change needs a changelog entry, and it may need the deprecation window that `DEPRECATION.md` defines.
- **Recorded responses go stale.** A5 runs against recordings, so it cannot detect a change in the Pipefy API. The integration tests stay the check for that.
- **Moves break links.** Phase 3 moves most pages once. B4 limits the damage, but bookmarks to a line number will still break.
- **More ways to fail a pull request.** Each check prints the command that fixes it, as the existing generators do.

## Open questions

- Which `extra_input` precedence wins: the explicit parameter or the extra key?
- Do ADRs 0001 to 0006 go through review as they stand, or does this RFC replace parts of them?
- Where does `docs/mcp/tools/identifiers.md` belong after A1? About 75% of it is not stated in code.
- Do `CHANGELOG.md` and `RELEASE.md` stay hand-written, or do change fragments (towncrier or scriv) replace the single changelog file?
- When this RFC is accepted, does it become ADR-0007, or does it stay as an RFC that ADRs cite?

## References

- [Diataxis](https://diataxis.fr/), Daniele Procida
- [arc42](https://arc42.org/), the template for `architecture.md`
- [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents), Anthropic
- [pytest-markdown-docs](https://github.com/modal-labs/pytest-markdown-docs), Modal
- [trycmd](https://docs.rs/trycmd/), the reference design for CLI transcript tests
- [Vale](https://vale.sh/docs)

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/contributing/rfc/0001-small-predictable-documentation-set.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/contributing/rfc/0001-small-predictable-documentation-set.md).
