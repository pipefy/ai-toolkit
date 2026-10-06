# Skills rules

Scoped to `skills/`. [`docs/contributing/skills.md`](../docs/contributing/skills.md) is the authoring guide, and it holds the template, the frontmatter fields, and what CI checks.

- Start a new skill from [`.github/skill-template/pipefy-skill-template/`](../.github/skill-template/pipefy-skill-template/).
- Give the skill a kebab-case name that starts with `pipefy-`, and make the frontmatter `name` match the directory name exactly.
- Use the word that the Pipefy product uses. Do not coin a term.
- Keep the body neutral to the component. Put MCP-only detail in `references/mcp.md` and CLI commands and flags in `references/cli.md`.
- Name only a tool or a command that has shipped. Check a CLI equivalent against [`docs/parity.md`](../docs/parity.md).
- Refer to another skill by its name, never by a path.
- Keep a skill under 500 lines.
- When you add or remove a published skill, edit the `skills` array in both `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json`.
- Before you push, stage the skill and run `uvx pre-commit run`.
- A skill in a regulated domain needs a `COMPLIANCE.md` and a review by Pipefy's Privacy, Legal and Compliance team.
