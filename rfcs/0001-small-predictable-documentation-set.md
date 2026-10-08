# RFC-0001: A small, predictable documentation set

- Status: Draft
- Created: 2026-10-08
- Evidence base: `dev` as of the merge of PR #757 (commit `e85483bf`). Line numbers and counts in this RFC hold at that commit.
- Neighbors: RFC-0002 (the quality bar for tests) and RFC-0003 (code behavior and architecture)

## Summary and motivation

The toolkit's docs copy facts that the code already owns, and no rule says where a page belongs. Authors keep the copies by hand, so the copies drift from the code, and each new page goes wherever its author chose. Today 11 statements in the docs and docstrings are false or misleading, or contain links that break where readers see them. The existing doc checks pass on all 11.

This RFC proposes two principles:

1. A fact that the code owns has no hand-written copy. A page points to the command that shows the fact, such as `pipefy --help`. When the reader cannot run a command at the moment they need the fact, the fact is generated into the page, and CI fails when the generated text is stale.
2. The path of a page tells the reader who the page is for, which part of the toolkit it covers, and what kind of page it is. The reader is a user or a contributor. The part is the MCP server, the CLI, or the SDK. The kind is one of the four kinds of the [Diataxis](https://diataxis.fr) framework: tutorial, how-to guide, reference, or explanation.

People write the rest by hand: tutorials, how-to guides, explanations, and the reasons behind a design. A machine checks each statement in them that a machine can check, such as a link, a command, or an example.

"Small" follows from the first principle: the docs hold fewer statements, and each fact has one source. "Predictable" follows from the second: an author knows where a new page goes, and a reader knows where to look. The proposed solution turns both principles into rules that a reviewer can check, and each rule points to the evidence below.

The outcome has three parts. A fact that the code owns stops drifting, because no person keeps a copy of it. A code change touches fewer hand-written pages, because the copies that the change would make stale no longer exist. A reader finds a fact by its path, not by a search.

## Problem statement

### Copies of facts that the code owns

Authors describe one behavior in up to 7 places: the docstring, the CLI help, a tool page in `docs/mcp/tools/`, one or more skills, `docs/parity.md`, and sometimes `docs/architecture.md` or a package `AGENTS.md`. Each copy changes on its own schedule. These statements are false or misleading:

| Where | What the text says | What the code or the tree shows |
|---|---|---|
| `skills/pipes-and-cards/pipefy-pipes-and-cards/references/cli.md:19` | `get_pipe` runs as `pipefy phase get <id>` | `pipefy phase get` calls `get_phase_fields` (`packages/cli/src/pipefy_cli/commands/phase.py:43`), as `docs/parity.md:144` also says |
| `skills/pipes-and-cards/pipefy-pipes-and-cards/references/cli.md:84` | `get_pipe` runs as `pipefy label list --pipe <id>` | The command calls the SDK method `get_pipe`, but the MCP tool for it is `get_labels`. The "Operation" column mixes MCP tool names and SDK method names, so the row reads as a wrong mapping |
| `skills/introspection/pipefy-introspection/references/mcp.md:44` | Pass `debug=true` to `execute_graphql`, and check `path` | `execute_graphql` has no `debug` parameter, and its error branch keeps only the `message` of each error, so neither `path` nor `correlation_id` reaches the caller |
| `README.md:198`, and the layout block at `AGENTS.md:21-26` | The workspace has three Python packages | `pyproject.toml:13` lists five: `sdk`, `mcp`, `cli`, `auth`, and `infra` |

Three more statements describe behavior that the code does not have:

- `docs/mcp/tools/cross-cutting.md:21` says that keys in `extra_input` that repeat a parameter are ignored. The 19 tools with `extra_input` handle such a key in several different ways, and some raise `TypeError`.
- `docs/mcp/tools/cross-cutting.md:11` says that empty, zero, and invalid IDs fail before any network call. `PipefyId` accepts `0`, `-1`, and `"abc"`, and about a third of the 122 tools with `PipefyId` parameters never call `validate_tool_id`.
- The docstrings at `packages/mcp/src/pipefy_mcp/tools/automation_tools.py:518` and `packages/sdk/src/pipefy_sdk/client.py:1073` say that an `active` key in `extra_input` wins. `packages/sdk/src/pipefy_sdk/client.py:1097` passes `active=active, **extra_input`, which raises `TypeError`.

RFC-0003 owns this behavior, so this RFC corrects these three statements only after RFC-0003 settles it.

Each of these statements passes the existing checks. `lint_skill_refs.py` checks that an operation name exists, and that a `pipefy` command path and its options exist. It checks each cell on its own, so a row that pairs a real tool with the real command of another tool passes. `tests/test_parity.py` checks that every tool has a row and that the command path exists, but not that the command implements the tool.

Docs also drift when no code changes. The first two rows were correct until PR #715. That PR changed skills, tests, and the skill lint, but no code under `packages/`. Its commit "docs: Separate skill surface instructions" split the skill tables per surface and dropped the note column that explained them.

The copies also multiply. The false `debug=true` advice appears in 6 pages in `docs/mcp/tools/` and in 4 skills. The tool count "187" appears in `docs/parity.md:5`, `docs/parity.md:229`, `packages/mcp/README.md:3`, and `packages/mcp/README.md:100`. A test compares the number at `docs/parity.md:5` with the registry (`tests/test_parity.py:131`), and no test reads the other three.

`docs/parity.md` holds 187 rows that map an MCP tool to a CLI command, and the 17 skill files named `references/cli.md` hold 162 more. Each of these 349 tool-to-command pairs is a copy of a fact that the code owns. In 161 of the 187 rows of `docs/parity.md`, a note follows the pair, such as the reason for a deferral. No code owns those notes, so they stay hand-written.

The commit history shows how often a code change also needs a doc edit. Of the 10 Markdown files with the most commits on `dev` that are not merges, 2 are `CHANGELOG.md` and `RELEASE.md`, which change with the code by design. For 5 of the other 8, more than half of the commits also change `.py` files, and 3 of those 8 are skills. A commit that changes both does not prove that the doc repeats the code, but it shows that doc edits follow code changes closely.

### Outdated references and broken links

Four more statements point at things that do not exist, that have changed, or that break where readers see them:

| Where | What the text says | What the code or the tree shows |
|---|---|---|
| `docs/config.md:122` | "A future file-backed keyring backend will write its credential store as `~/.config/pipefy/keyring.cfg`" | The backend exists: `configure_keychain_backend("file")` writes `keyring.cfg` through `_KEYRING_FILENAME` (`packages/auth/src/pipefy_auth/storage.py:34`) |
| `packages/cli/README.md:85` | See `CLAUDE.md` for contributor guidance | The root has no `CLAUDE.md`. The only tracked one is the symlink `packages/mcp/CLAUDE.md` |
| `README.md:341` | "Each published blueprint ships with a `COMPLIANCE.md`" | No skill ships a `COMPLIANCE.md`. The only tracked one is the template, `docs/compliance/COMPLIANCE.template.md`. `packages/sdk/hatch_build.py` packs only `SKILL.md` and `references/`, so a `COMPLIANCE.md` would not reach the wheel. No code or skill uses the term "blueprint" |
| `packages/mcp/README.md`, `packages/cli/README.md`, `packages/sdk/README.md` | 12 relative links of the form `../../docs/...`, on 8 lines | Each `pyproject.toml` sets `readme = "README.md"`, so these READMEs become PyPI pages, where relative links break |

No check covers these statements. CI and the pre-commit hooks run no link checker and no Markdown linter, and no check reads the prose of `docs/` or of the READMEs.

### Page placement

The 32 pages in `docs/` mix kinds of content at every level:

- `architecture.md`, `response-typing.md`, and `dependencies.md` are pages for contributors, but they sit at the top of the user docs.
- `DEPRECATION.md` is a policy page, and `docs/README.md` does not link it.
- `docs/mcp/tools/` holds 16 pages: 14 domain pages that are part reference and part explanation, plus `cross-cutting.md` and `identifiers.md`.
- `docs/cli/auth.md` mixes a quick start, a reference section, and a troubleshooting section in 292 lines.
- `docs/` has no tutorial for any surface. The only quick starts are sections inside `docs/cli/auth.md` and `packages/cli/README.md`.

The repository root holds 8 Markdown files. Six of them follow a convention that readers expect at the root. `RELEASE.md` and `TERMS.md` follow none, so a reader cannot predict that they exist. Because no rule exists, each author picks the place for a new page, and each new page adds to the mix.

### The cheaper alternative

The cheapest response is to fix the 11 statements, add a link checker, and extend the skill lint so that it checks each tool-to-command pair. This RFC includes the first two. They do not stop the next drift, for three reasons.

First, a fixed copy is still a copy, and nothing ties it to the code. `README.md:198` has said "three Python packages" since 2026-05-18. The `pipefy-auth` package arrived four days later, in PR #216. After that, 55 commits that are not merges changed `README.md`, and none of them corrected the sentence.

Second, a link checker finds broken links. It does not find a false statement whose links work, such as the three-package row or the keyring row.

Third, a check of each pair needs a correct pair to compare against. No code records which CLI command implements which MCP tool, so the only record is the hand-kept tables that the check would test. Once the code records the mapping, the tables only repeat it, and generating them costs less than checking them.

### Consequences

- **Agents act on false instructions.** Authors write skills for agents. An agent that follows the first three rows of the first table calls the wrong command, or passes a parameter that does not exist.
- **A code change carries doc edits in several files.** A change to one tool can touch its docstring, a tool page, a skill, and `docs/parity.md`. Each extra file is one more place to forget, and one more diff to review.

## Explicit non-goals

This RFC decides where a fact is written, how it reaches readers and agents, where each page belongs, and what the doc checks verify. It leaves these items to others:

| Item | Decided by |
|---|---|
| Code behavior, such as the `extra_input` precedence and the ID checks above, the promises in docstrings and `--help` texts, and the content of the architecture docs | RFC-0003. This RFC decides only where these texts live and how they reach readers |
| How the doc checks are tested, and the quality bar that every test meets | RFC-0002. This RFC decides only what the doc checks verify |
| The legal text of `TERMS.md` | The owner of the legal text. This RFC proposes only where the file lives |

This RFC does not propose a docs site with its own user interface, and the layout that it proposes keeps that option open.

## Proposed solution

### Rules

Four rules put the two principles into practice. Each rule says what a reviewer or a check verifies, and each one points to the evidence in the problem statement. The layout below follows from these rules.

#### R1: One owner per fact

Every fact has one owner: the one place where the fact is written. The code owns each fact that it can state, such as the parameters of an MCP tool, the commands and options of the CLI, the settings that the packages read, and the flags of `install.sh` and `uninstall.sh`. A person owns every other fact.

Every other place reaches a fact that the code owns in one of two ways:

1. A pointer to the command that shows the fact, such as "Run `pipefy phase --help` for the options." This is the default, because a pointer has no copy that can go stale.
2. A generated block, when the reader cannot run a command at the moment they need the fact. Three cases exist today: a comparison across commands, as in `docs/parity.md`, a page that readers see outside the repository, such as a package README on PyPI, and an agent that chooses a tool before it calls one.

A generator writes each generated block between two markers. CI runs the generator again and fails when the committed text differs from its output.

The evidence is in "Copies of facts that the code owns": four false statements in the first table, the `debug=true` advice in 10 places, the tool count in 4 places, and 349 tool-to-command pairs. "The cheaper alternative" shows that a corrected copy drifts again.

No code records today which CLI command implements which MCP tool. This RFC asks RFC-0003 to add that record to the tool registry. Until the record exists, the 349 pairs stay hand-written, and the existing checks keep covering them.

#### R2: The path of a page declares its role

A path table maps each path pattern to a role. Every tracked Markdown file matches one pattern, and CI fails on a file that matches none. A new pattern needs a reviewed edit to the table.

Under `docs/`, a path has three parts: `docs/<scope>/<kind>/<subject>.md`.

- The scope is one of `docs/` (global), `docs/contributing/`, `docs/mcp/`, `docs/cli/`, and `docs/sdk/`. R3 decides the scope of each fact.
- The kind is one of the folders `tutorial/`, `how-to/`, `reference/`, and `explanation/`. The file `README.md` in each scope is its landing page.
- The subject names what the page covers, such as `login.md` or `identifiers.md`.

Every scope uses the same kind folders, so a reader who knows one scope can find a page in any other. A folder exists only when it holds a page.

Each page starts with front matter that holds two fields: `title` and `description`. The landing page of a scope lists its pages with these fields. The front matter does not repeat the kind, because the path already holds it (R1).

Outside `docs/`, the path table names each other role. The repository root holds six Markdown files, each of which follows a convention that readers expect: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `AGENTS.md`, and `CHANGELOG.md`. `RELEASE.md` and `TERMS.md` move into `docs/`. The table also names the package READMEs, the skills, and `rfcs/`.

A package README becomes a page on PyPI, so it links only to scope landing pages, with absolute GitHub URLs.

The evidence is in "Page placement" and in the last row of the table in "Outdated references and broken links".

#### R3: The scope of a fact

The scope rule places each fact, not each page. It starts with one question: what is the reader working with when they need the fact?

1. If the reader is changing the repository, the fact belongs to the contributor scope, `docs/contributing/`.
2. Otherwise, the reader uses a surface: the MCP server, the CLI, or the SDK. A fact that holds for one surface belongs to the scope of that surface.
3. A fact that holds for two or more surfaces belongs to the global scope, `docs/`.

The answer follows the surface, not the location of the code. For example, `pipefy_auth/flow.py` raises `State mismatch on OAuth callback`, but only `pipefy auth login` runs that flow, so the fix for that error belongs to the CLI scope.

The contributor scope shares no fact with the user scopes. Its pages can link to user pages, but no page includes text from the other side.

Hand-written content flows up only. Each surface scope is complete on its own. A global page can include sections from the surface scopes and adds only the ideas that span surfaces. A surface page links to global pages and never includes them. As a result, two scopes never hold the same fact.

This RFC uses "global" for a fact that holds for two or more surfaces. It does not use "cross-cutting", because today that word names `docs/mcp/tools/cross-cutting.md`, a page about one surface.

The evidence is in "Page placement": contributor pages sit at the top of the user docs, and each author picks the place for a new page.

#### R4: A machine checks every claim that it can check

CI runs these checks at every commit on `dev`:

- The path table check (R2).
- The freshness check for generated blocks (R1).
- A link checker over all Markdown files.
- `markdownlint` with a committed config.
- Executable examples: each `pipefy` command block and code snippet in a hand-written page runs as an offline test.

Each claim about behavior in a hand-written page carries its proof: an executable example, a pointer or a generated block (R1), or a link to a named test. A reviewer deletes a claim that has no proof.

The evidence is in the problem statement: the existing checks pass on all 11 false statements, and CI runs no link checker and no Markdown linter. RFC-0002 sets the quality bar for these checks as tests.

### Layout

Pending (pass 3).

## Drawbacks and alternatives

Pending (pass 4).

## Unresolved questions

Pending (pass 4).

## Migration plan

Pending (pass 5).
