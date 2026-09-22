# Documentation authoring

This guide describes the target structure for the `docs/` tree and where a new doc goes. Its siblings are [`architecture.md`](architecture.md) and [`conventions.md`](conventions.md).

The tree is mid-migration to this target. Where a file still sits in the wrong place, an open issue tracks the move.

## Where a doc goes

Sort by audience first, then by kind.

- Contributor docs live under `docs/contributing/`.
- Docs for the parties who use the toolkit live by application under `docs/mcp/`, `docs/cli/`, and `docs/sdk/`.
- A durable, cross-cutting one of those lives at the `docs/` root. A fast-changing one is generated instead (see below).

Then keep a doc to one kind where practical. The Diataxis kinds are tutorial, how-to, reference, and explanation. A file that mixes several is a split candidate.

## Decision records

A decision record is contributor explanation of a distinct kind: one architectural decision, immutable once adopted. The set lives under `docs/contributing/adr/`, one file per decision. To change a decision, add a record that supersedes the old one. Do not edit an adopted record. The rule a record produces graduates to `architecture.md` or `conventions.md`, where a contributor reads the current rule. The record keeps the reasoning. In its `Consequences` section, each consequence names what it changes, which is a `QR` row, a convention rule, or a constraint, and grades that change as satisfied, partly satisfied, or violated. A consequence that changes no row, no rule, and no constraint says so.

## Citing by ID

A reviewer settles a point with an ID rather than an argument. Three families exist, and each one has one home:

- A convention ID, such as `PARSE-3`, names a rule for how we write code, and [`conventions.md`](conventions.md) is the reference.
- An `FR` ID names a function the toolkit delivers, and `Requirements overview` in [`architecture.md`](architecture.md) is the list.
- A `QR` ID names a demand the code must meet, and `Quality requirements` in [`architecture.md`](architecture.md) is the list.

## Authoring a convention

[`conventions.md`](conventions.md) is a rule reference, and every rule takes the same form:

- A permanent ID, such as `PARSE-3`. A retired rule keeps its ID, so a citation never changes meaning.
- One rule line, which states the commitment.
- A `Do` list and a `Do not` list.
- A `Why` line, capped at three sentences.
- An optional `Weighed` line, which names the alternative that was rejected.

The `Why` line exists so that a later reader can tell when the reason stopped holding. It is part of the rule entry, so a rule reference stays one kind of document.

A new rule earns its place by correcting something that happened. A rule written against a hypothetical costs every reader and catches nobody.

A code example names no shipped symbol. A symbol in an example rots on the next refactor. A reader who greps a name that no longer exists stops trusting the whole document.

## Authoring a section of `architecture.md`

[`architecture.md`](architecture.md) fills part of the [arc42 template](https://docs.arc42.org). The rules in the four groups below hold in every section, and a rule that is arc42's says so. A block per section then carries only what holds for that section alone: its shape, its admission test, and the facts it owns.

**Shape.**

- The map takes arc42's sections, their names, and their breakdown, and a level that arc42 leaves to the author is ours to fill. Where a section merges or splits arc42's sublevels, renames one, or stops above one, its block below says so.
- A section that nothing owns yet stays absent, and `Risks and technical debt` names it as the target. Arc42 7 stays absent today.
- A part of the system goes under arc42 5. A rule that holds whichever part you are in goes under arc42 8, and arc42 8 says that a concept can concern a few elements rather than all, so a rule that one component alone obeys still belongs there. A settled choice goes in `Solution strategy` where it serves a goal or where every contributor holds it whatever they change, and in [`adr/`](adr/README.md) otherwise. Sort a rule from a choice by whether a contributor follows it while writing code.

**Ownership.**

- A section states what it owns and points at every other owner, under [Point at the owner of a fact](#point-at-the-owner-of-a-fact). A section whose whole content another owner holds is a pointer, which is what `Architecture decisions` is. A pointer sits under a table, never in a cell.
- A name comes from its catalog. A capability comes from Pipefy's domain model, a quality from [`quality.arc42.org`](https://quality.arc42.org/), a category from Q42, and a block from the code. Where the catalog is silent, name the thing and settle nothing.
- A permanent ID, `FR` or `QR`, follows the same rule as a convention ID above.
- A `QR` handle runs from a demand to what serves it. A section names the `QR` it satisfies, `Quality goals` cites the one row each goal owns, and a `Solution strategy` driver cites the demand it answers. No other cell carries an `FR` or a `QR`, because a run of IDs costs every reader and pays only a completeness check.
- A gap is stated once, in `Risks and technical debt`, under [Where a gap is documented](#where-a-gap-is-documented). Every other section states what the code does.

**Altitude.**

- Level 1 names no mechanism, no parameter, no count, and no tool or command. The code owns each of them, and a mechanism changes without the function changing.
- Every claim is a third-person declarative, because the map explains rather than instructs. A cell reads on its own, takes no referent from a neighbor, and matches the meaning of what it cites without overclaiming past it.
- A risk, a quality mark, a cost, and a conflict each sit beside the decision or the concept that produced them, and nowhere else.

**Components.**

- A component is a unit of the toolkit with exactly one way in, and `Glossary` fixes the word. The vocabulary is `SDK`, `CLI`, `MCP`, and `Skills`, in that order, in every cell and every list that names the axis. A claim about the axis states the way in, and it names no party.
- A section whose subject plays out differently per component ends with a `**By component.**` block: four bullets, one per component, in that order. A bullet states the difference in one or two sentences at level-1 altitude, or it reads `no difference`, or it reads `not reached`. A section whose subject is the same everywhere carries no block, and the absence is the statement.
- A table that carries the axis as a column names that column by the verb that runs between the row and the component, such as `Applies to` or `Reached by`, and places it second, beside the row name. A cell lists the components it concerns, and no aggregate word stands for the list. `The repository` is the one wider referent, because it reaches `docs/` and the support packages too. A table whose rows are the components carries no axis column.
- A stakeholder expectation that differs by component names each component, in the fixed order, inside its cell.

**`Requirements overview`, arc42 1.1.** The business goal, then the functions the toolkit delivers, then the capabilities they act on.

- The opening states the business goal, which arc42 asks for here as the driving force, and it names the party that holds it. It pairs no party with a component, because a party is not an axis. It defines no domain term and no package responsibility, because arc42 3 owns the first and arc42 5 owns the second.
- A function is the toolkit's own work, and what Pipefy's API already offers is a capability. A function line says what the act is and what it delivers, with the trigger first, and it names no party.
- If a new tool would add a bullet, the list is too detailed.

**`Quality goals`, arc42 1.2.** Three to five qualities, in the priority order that arc42 asks for here.

- A goal is a catalog name plus the reason it holds its rank, and it cites the most important `QR` in its category. The name is abstract, the `QR` carries the demand, and the reason says what is at stake. `Quality scenarios` states the demand, and `Solution strategy` states what the goal produced, so 1.2 states neither. Arc42's form for 1.2 suggests a scenario instead, and the reason is this map's choice.
- The `QR` rows carry no rank, because a rank there would reopen where each new row slots in.
- The order changes only when something outside this file changes what matters: a pivot, an incident, a regulation, a cost limit, a vendor change, or a new key stakeholder.

**`Stakeholders`, arc42 1.3.** A role, a contact, and expectations in prose.

- A party earns a row on arc42's five criteria: it needs to know the architecture, it has to be convinced of it, it works with the architecture or the code, it needs the documentation for its work, or it decides about the system. A party that is not a person can meet them.
- A row is keyed to the party, never to a component. A demand stated outside this table points at the row that holds it, and names no party of its own.
- Expectations cover the architecture and its documentation, which is what arc42 asks for.

**`Architecture constraints`, arc42 2.** The limits every decision works inside: a technical table, an organizational table, and a block for the conventions we set. Arc42 2 offers those three groups, and the third is a block rather than a table here, because each convention set lives in its own file.

- A constraint takes a choice away from a contributor, and every one takes a row here, even where another file states the rules. A requirement is not a constraint.
- The kind of limit picks the group. A limit on technology is technical, and so is a limit that a code change relieves, whoever set it. A limit from the organization, from a contract, or from law is organizational. A rule we set about how we write and work is a convention, and the block names each set with its file.
- A row names the limit and explains where it comes from, and another section says what we do about it. A row leaves when we lift the limit, and `Risks and technical debt` then carries the code still written against it.

**`Context and scope`, arc42 3.** The parties the toolkit exchanges data with, in one diagram and one table, under prose that states the domain it acts on and who it acts as.

- Draw the toolkit as one box, and draw every partner, inbound and outbound. Completeness is arc42's demand here and almost nowhere else in the template. A host that holds or carries a credential is a partner, and so is a party that stands between an application and the party that reaches it.
- A table beside the diagram carries which components reach each partner and what crosses. Arc42 3.1 offers the table as an alternative to the diagram, and this map takes both. It exists because no install reaches every partner. `Package decomposition` draws the same partners on the package that performs each crossing, and arc42 asks that the two stay consistent.
- An inbound arrow carries the way in, and an outbound arrow carries no label, so the two pictures cannot come to claim different things.
- One diagram carries the business context and the technical context, although arc42 keeps 3.1 and 3.2 apart, so the merge is this map's choice. Technology appears only where it marks the boundary. Mark no risk and no quality goal on a partner. Arc42 tip 3-4 recommends a risk mark, and this rule overrides that tip, because `Risks and technical debt` owns every risk.

**`Solution strategy`, arc42 4.** The most important decisions in one table: a driver, the decision it produced, and the section that details it. The goal rows come first, in the `Quality goals` order, so they grow only when that section does.

- One table with three columns, although arc42 4 suggests four: a quality goal, a scenario, a solution approach, and a link. No scenario column exists here, because `Quality scenarios` states every demand and `Quality goals` carries the handle that reaches it. A second table would put a second grammar in one section.
- A driver says what happens, in words a person would say, and never the category it falls in. It opens with the phrase and puts the `QR` handle in parentheses after it. Where no `QR` carries the driver, write it out rather than borrow the nearest handle. Where a `QR` admits more than one mechanism, the driver says which demand rules the others out.
- A decision names the mechanism that meets its driver and never explains it, because the linked section owns the explanation. A decision and the check that keeps it true are two rows. Where a demand has a half that no settled mechanism serves, leave that half out.
- The last column links the owner, and never a decision record. An organizational commitment earns a row only where it shapes the architecture. The language and the distribution shape are stated here, with the reason that drove them.

**`Building block view`, arc42 5.** The static structure, with one subsection per whitebox, named after the axis that whitebox splits on. The two sublevels take our names, `Package decomposition` and `Inside each package`, where arc42 says `Whitebox overall system` and `Level 2`, because arc42's names label a slot and ours name the subject.

- Every part the diagram draws carries a responsibility line, because arc42 counts those lines as part of the level. A drawn part with no line is how `pipefy-auth` and `pipefy-infra` went undescribed.
- The reason says why the decomposition has these parts, and a rule the structure obeys fails as a reason, because every correct split obeys it. The kinds come from the scope list in [`DEPRECATION.md`](../DEPRECATION.md). `Requirements overview` says what the toolkit does, and this level says which block does it.
- A blackbox takes arc42's columns, and the quality and open-issues fields stay out, because `Identity lifetime` and `Risks and technical debt` own them. This level draws the external partners, because it alone says which package performs a crossing.

**`Runtime view`, arc42 6.** A few scenarios, each a subsection that names what the reader watches happen. A `###` name is ours, because arc42 6 numbers no sublevel.

- A scenario earns its place on architectural relevancy, and the section holds a representative selection, which is what arc42 asks for.
- A scenario names blocks that `Building block view` already names, coins no participant, and stays at level-1 altitude, because arc42 recommends a schematic scenario over a detailed one.
- The section splits on the axis that the concept owning the subject already chose. A difference by deployment profile goes in prose, or in a scenario of its own where that difference is the subject, and never in a second copy of the same flow.
- A scenario that one component alone runs names that component. A scenario that starts in the middle of a longer flow says what ran before it, which arc42 calls a partial scenario.

**`Quality requirements`, arc42 10.** Two subsections, as arc42 10.1 and 10.2 divide it.

- The overview at 10.1 groups every row by its Q42 category, and it is the only place that mapping is written. The categories overlap by design, so a row can appear under several, and never force a row to one. Arc42 10.1 offers ISO 25010 or Q42, and we take Q42.
- A scenario row at 10.2 carries its ID, then the demand in one line in the words of the party that holds it, then an acceptance criterion. The rows sit in arc42's two categories: a reaction while the system runs, and a change to the system or to what it depends on.
- A criterion is observable, it states what must hold, and it carries a number only where this repository owns that number.

**`Risks and technical debt`, arc42 11.** See [Where a gap is documented](#where-a-gap-is-documented). Arc42 11 wants those entries ordered by priority.

## Where a gap is documented

`conventions.md` states what we commit to, and it names no gap. A convention governs the next change, so older code that predates it is legacy rather than a shortfall.

[`architecture.md`](architecture.md) is a map rather than a rule set, so it works the other way. A map claim is either true of the code or not, and the document owes the reader every place the code is behind it. Those places gather in one final section, `Risks and technical debt`, and each entry names the target that closes it. A disabled import-linter contract is one such target, because it sits beside the live contracts and one edit enables it. This split follows [the arc42 template](#authoring-a-section-of-architecturemd), which keeps the building block view apart from risks and technical debt.

Neither document carries the inventory or the remediation plan for a gap. A concrete step is closeable work, so it belongs in an issue.

## Point at the owner of a fact

Every fact has one owner: the code, a schema, an enforced contract, or another document. A document that restates a fact it does not own holds a copy, and that copy drifts. A reader then cannot tell which copy is current, so name the owner and point there. A document holds a copy only where the argument on its own page depends on that copy. A measured count of what the code holds is one such copy. It goes stale on the next routine change, although the claim around it stays true, so state the claim and leave the number out. Keep a number only where the document owns the set it counts, or where the value itself is the defect. [`architecture.md`](architecture.md) names the import-linter contract rather than listing the layer modules, and it names the GraphQL schema rather than describing entity shape.

Where the code owns a list, generate the document from that code: docstrings, pydantic `Field(description=...)`, the tool registry, or Typer help. Hand-author only where there is no code source, such as a concept doc. Do not keep a generated table and durable prose in the same file.

## Name no vendor behind a capability

A Pipefy capability can run on a third-party service. Name the capability, and never the service. A document that names it hands a reader outside Pipefy the product to probe, and the vendor can change without the capability changing.

State a limit without its mechanism. [`docs/ipaas.md`](../ipaas.md) draws the iPaaS credential flow as a short-lived, pipe-scoped credential and a session-scoped access, with no endpoint, no token shape, and no step named. That is the altitude for every document here.

## Keep it small

Keep recognizable names: `README`, `CHANGELOG`, `CONTRIBUTING`, `SECURITY`, `MIGRATION`, `DEPRECATION`, and `ARCHITECTURE` (as `docs/contributing/architecture.md`). A directory earns its keep by file count and homogeneity, so do not invent a `guides/` or `reference/` bucket for a few files. A concrete cleanup or migration step is a closeable task, so open an issue instead of listing it here.
