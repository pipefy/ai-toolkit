---
name: pipefy-skill-template
description: >
  Copy this file when authoring a new Pipefy skill. Replace placeholders,
  then rename the folder so it matches the frontmatter name.
tags: [pipefy, template]
---

# [Skill title]

[One or two sentences: what this skill does and when an agent should load it.]
[Optional: number of shared operations.]

[When surface-specific guidance exists, create references/mcp.md and/or
references/cli.md and link them here. MCP clients load the MCP reference;
CLI users load the CLI reference. Keep domain rules and payloads in this body.]

---

## When to use

- [User intent / example phrase that should trigger this skill.]
- [Another trigger.]

Do not use this skill for:

- [Out of scope — point to another skill or approach when relevant.]

## Prerequisites

- [IDs, roles, or config that must exist first — e.g. `pipe_id`, org access.]
- [Shared access prerequisites; put surface-specific setup in references.]

## Tools needed

| Operation | Read-only | Purpose |
|-----------|-----------|---------|
| `[operation_name]` | Yes/No | [Domain outcome] |

Replace bracket placeholders with real MCP tool names from the live server
(or [`docs/parity.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/parity.md)).
Put shipped CLI mappings in references/cli.md and MCP controls in references/mcp.md.
Unknown names fail CI in this repository.

## Steps

1. **[Step name]** — [what to do and why.]

   Shared operation arguments (adapt to the active surface):
   ```
   [operation_name] [arg]=[value]
   ```

2. **[Next step]** — ...

## Success criteria

- [Observable outcome the agent or human can verify.]

## Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| [Error or bad state] | [Cause] | [Fix or fallback skill] |

## See also

- [Related skill name, e.g. `pipefy-pipes-and-cards`; no cross-skill paths.]
