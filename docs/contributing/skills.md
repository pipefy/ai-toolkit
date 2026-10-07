# Skill authoring

This guide says how to add, write, name, and review a skill in `skills/`. A skill is Markdown only, so it needs no Python code and no tests. You need [`uv`](https://docs.astral.sh/uv/getting-started/installation/) only to run the checks. [`CONTRIBUTING.md`](../../CONTRIBUTING.md) has the sign-off and the review for a regulated domain.

## What a skill is

A skill is a directory with a `SKILL.md` entrypoint that describes one Pipefy workflow. Its body holds the domain rules, payload shapes, steps, and failure modes that the SDK, the MCP server, and the CLI share. Instructions for one component live in reference files beside it, so a client loads only the file for the component it uses.

## Directory structure

```text
skills/
  <domain>/
    <skill-name>/
      SKILL.md          ← the skill
      references/       ← only when the workflow has component-specific instructions
        mcp.md          ← MCP controls, confirmation tokens, response envelopes
        cli.md          ← shipped commands and flags
      COMPLIANCE.md     ← required for a regulated-domain skill or blueprint
  README.md             ← catalog index
```

Each folder directly under `skills/` is a domain, named for an area of the MCP tool surface. Open an issue before you add a domain.

A skill in a regulated domain (`legal`, `human-resources`, `finance`, `compliance`, or any skill that decides about a natural person) needs a filled `COMPLIANCE.md`, started from [`COMPLIANCE.template.md`](../../template/COMPLIANCE.template.md), and the review that [`CONTRIBUTING.md`](../../CONTRIBUTING.md#content-review-for-regulated-domains) describes.

## Add a skill

1. Fork and clone the repository.
2. Choose a domain folder under `skills/`.
3. Copy the template and rename it:

   ```bash
   cp -R template/pipefy-skill-template skills/<domain>/pipefy-<name>
   ```

4. Fill in `SKILL.md` by the rules below. The template's [`SKILL.md`](../../template/pipefy-skill-template/SKILL.md) shows every section a skill has.
5. Add the skill to the `skills` array in both `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json`.
6. Stage the skill and run the checks, which are the same checks that CI runs:

   ```bash
   git add skills/<domain>/pipefy-<name> .cursor-plugin/plugin.json .claude-plugin/plugin.json
   uvx pre-commit run
   ```

7. Load your branch in Claude Code, as [Test the Claude Code plugin from a local checkout](development.md#test-the-claude-code-plugin-from-a-local-checkout) describes, and run the skill end to end against a real Pipefy organization.
8. Open a pull request.

## Names

- A skill name is kebab-case and starts with `pipefy-`, such as `pipefy-process-design`.
- A domain folder is kebab-case, and plural where that reads naturally, such as `automations`.
- A name uses the word that the Pipefy product uses, never a new one. Pipefy's domain model settles each name and is internal, so open an issue and ask rather than coin a term.
- A published skill keeps its name. A rename needs a CHANGELOG note, so that an agent prompt with the old name still resolves.

## Frontmatter

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Must match the directory name exactly. |
| `description` | Yes | One-line summary that agents use to choose this skill. |
| `tags` | No | List of relevant keywords. |
| `metadata.surfaces` | No | Space-separated string of the components the workflow applies to: `sdk`, `mcp`, `cli`. Omitting it means all three. |

`sdk` means a program that builds agent tools from `PipefyClient`, `mcp` means an MCP client, and `cli` means the `pipefy` command. The field states where the workflow applies, not that every call signature matches or that every deployment profile offers it, so state prerequisites separately. A skill limited to the MCP server and the CLI declares:

```yaml
metadata:
  surfaces: "mcp cli"
```

An MCP-only skill, such as an iPaaS one, uses `"mcp"`. Do not use a YAML list, an empty value, a repeated token, or another component name. A duplicate YAML key fails, including a repeated `metadata` or `surfaces` key. Unrelated metadata does not change the default.

## Body style

- Write action-first headings: "Create a pipe", not "Pipe creation".
- Keep the body neutral to the component. Name each operation by its shared tool name, and keep domain argument examples in the body. Put MCP confirmation tokens, elicitation, tool profiles, MCP-only parameters, and envelopes in `references/mcp.md`, and CLI commands and flags in `references/cli.md`. Link each existing reference from the body. A router with no component-specific behavior needs no reference file.
- Show concrete MCP and CLI invocations in their references, as code blocks. Document only the CLI equivalents that [`docs/parity.md`](../parity.md) marks shipped, and mark a missing one as deferred rather than invent a command.
- Prefer explicit IDs over names in examples, because a Pipefy ID is stable and a name changes.
- Put the common path first, and edge cases and failure modes last.
- Keep a skill under 500 lines. When it grows past that, split it by sub-domain.
- Refer to another skill by its name, as in `See also: the pipefy-automations skill`, optionally with a section. Do not link a path between skills or copy their content, because a consumer may flatten the catalog to `<skill-name>/SKILL.md`. Inside a skill, a relative link to `references/` stays portable. Use a repository URL for any other doc.

## Linking to repository docs

When a skill needs a stable link into this repository:

- MCP tool semantics: `docs/mcp/tools/<domain>.md`, and `docs/mcp/tools/cross-cutting.md` for the rules that cross tools.
- CLI-only flows: `docs/cli/`, such as `docs/cli/self-healing.md`.
- SDK usage: `docs/sdk/README.md`.
- Install: [`docs/install.md`](../install.md), and `skills/onboarding/pipefy-toolkit-setup/SKILL.md` for the first-time agent checklist.
- `PIPEFY_*` variables and `config.toml`: `docs/config.md`.
- The MCP tool and CLI command matrix: `docs/parity.md`.

## What CI checks

`skills-lint.yml` runs on every pull request:

- `lint_skill_frontmatter.py` validates the frontmatter of every `skills/**/SKILL.md`.
- `lint_skill_refs.py` checks every operation name against the components that the skill declares. An MCP reference must name a registered MCP tool, and a `name=` argument in an example must exist on that MCP tool or on the `PipefyClient` method. Every `pipefy` invocation written as code, inline or in a fenced block, must resolve to a real subcommand path with `--` options that exist on that command. `pipefy` in plain prose is checked for the root command only.

A reference to a tool or a command that has not shipped fails CI. Wait for it to ship, or open the pull request as a draft and link the pull request that implements it.

When a pull request renames a tool or a command, it updates every skill that names it, in the same pull request or in a paired one opened in the same review window. A rename that leaves a skill behind fails the build.

The `test` job runs `lint_plugin_packaging.py`, which checks that `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json` each list every published skill. So adding or removing a published skill also edits the `skills` array in both files.

## Review rubric

CI checks what the previous section lists. A reviewer checks the rest:

1. The content is accurate against the current MCP tools and CLI commands.
2. The examples run. For a high-impact skill, the reviewer runs them against a real Pipefy organization.
3. The body follows [Body style](#body-style).
4. The skill is generic, with no content tailored to one agent persona.

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/contributing/skills.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/contributing/skills.md).
