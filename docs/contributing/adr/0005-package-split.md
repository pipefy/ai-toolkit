# ADR-0005: One package per way in, over shared libraries

Status: Accepted
Target release: none

## Context

ADR-0001 decides the layers inside a package, and no record says why the toolkit has the packages it has. `Package decomposition` in [`architecture.md`](../architecture.md#package-decomposition) states the split: three components, which are the SDK, the CLI and the MCP server, and two libraries beneath them, which are Identity and Commons. The skills ship as files and hold no code. The map states each package's responsibility and leaves the reasoning to this record.

Two forces pull on a package boundary. The first is the reason to change. A program that imports the SDK needs a stable domain value, a shell user needs output that the next command can parse, and an agent needs a tool call that states an intent, so a change for one caller seldom concerns the others. The second is the cost of an install. A caller pays for every dependency that a package declares, whether or not it calls the code behind it. A program that imports the SDK has no use for a browser login or a keychain.

## Decision

Give each way that a caller uses the toolkit its own package, and put the code that more than one of them needs in a library beneath them. Code that changes for one caller's reason lives in that caller's package, which is the Common Closure Principle. A library holds only code that every package which declares it uses, which is the Common Reuse Principle.

The two principles pull apart on the shared code. Closure alone would put it in one library, because it changes together. Reuse splits it where one caller would install what it never calls. So the credential operations are their own library, Identity, and the SDK does not declare it. Commons holds what carries no Pipefy concept and declares only `pydantic` and `pydantic-settings`, so every package takes it cheaply.

Every package lives in one repository and ships on one version, so a change to shared behavior lands as one reviewed change.

Four alternatives lost:

- One distribution with optional extras, such as `pipefy[mcp]`. Every install would ship the code of every component, and the boundary between the CLI and the MCP server would be a convention with no declared dependency for a check to hold.
- One shared library beneath the components. It would put the login machinery and the keychain in every SDK install.
- A fifth package for the application logic that the CLI and the MCP server share. The only duplication found between them was a sequence that the vendor's API shape forced, and that sequence moved down into the SDK. Nothing that an actor decides was left to share.
- One repository per package. A change to shared behavior would ship as several releases, tested against one application at a time.

## Consequences

`QR-26` is satisfied: one test run gates a change to shared behavior, and every package ships it at once on the same version. The cost is that a fix to one component releases all of them.

`QR-14` is partly satisfied. Ruff `TID251` holds the direction between packages, and it bans the SDK's private modules in the CLI and the MCP server only. Import-linter holds the layers inside `packages/mcp` alone, so the epic for an import contract per package in [`adr/README.md`](README.md) carries the rest.

The reason to change has no `QR` row. No row demands that the CLI and the MCP server can change apart, so this decision rests on the reasoning above and changes no row. [Risks and technical debt](../architecture.md#risks-and-technical-debt) is where that missing row belongs.

The fifth-package question can reopen. [Risks and technical debt](../architecture.md#risks-and-technical-debt) records SDK calls that run work which belongs above the SDK, such as `update_ai_agent` resolving field references. When that work moves up, the CLI and the MCP server can duplicate it, and that duplication is application logic that the rejection above did not weigh.

Commons is the one package that a layered stack cannot place, because it holds pure coercion beside a file read and a hostname lookup. The split does not depend on it: a strict stack would divide Commons into a pure kernel and a set of adapters, and every other boundary would stay.

The current rule lives in [`architecture.md`](../architecture.md#package-decomposition).
