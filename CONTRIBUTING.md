# Contributing to ai-toolkit

Thanks for helping improve the monorepo. This guide covers **skills** (Markdown playbooks). For **MCP tools, CLI commands, and SDK** work, follow [`docs/contributing/development.md`](docs/contributing/development.md).

---

## Contributing a skill

A skill is Markdown only, so you write no Python code and no tests. You need [`uv`](https://docs.astral.sh/uv/getting-started/installation/) only to run the checks. If you can write a numbered list and a YAML header, you can contribute a skill.

### Quick start

1. Fork and clone the repo.
2. Choose or create a domain folder under `skills/`.
3. Copy the starter skill and rename it:

   ```bash
   cp -R .github/skill-template/pipefy-skill-template \
     skills/<domain>/pipefy-<name>
   ```

   Fill in [`SKILL.md`](.github/skill-template/pipefy-skill-template/SKILL.md) using the rules in [`docs/contributing/skills.md`](docs/contributing/skills.md).
4. Add the skill to the `skills` array in both `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json`.
5. Stage the skill and run the checks. They are the same checks that CI runs on the pull request.

   ```bash
   git add skills/<domain>/pipefy-<name> .cursor-plugin/plugin.json .claude-plugin/plugin.json
   uvx pre-commit run
   ```

6. Open a PR.

> **Try your skill in Claude Code before opening the PR.** Point the plugin marketplace at your local clone so your branch loads live — see [Test the Claude Code plugin from a local checkout](docs/contributing/development.md#test-the-claude-code-plugin-from-a-local-checkout).

### Rules for a skill

[`docs/contributing/skills.md`](docs/contributing/skills.md) holds every rule for a skill: the frontmatter, the names, the body style, and what CI checks.

### Review rubric

PRs are reviewed for:

1. Frontmatter valid and `name` matches directory.
2. Content is accurate against the current MCP/CLI surface.
3. Examples are runnable (checked manually by reviewer against a real Pipefy org for high-impact skills).
4. Style matches [`docs/contributing/skills.md`](docs/contributing/skills.md).
5. No persona-specific content (skills are generic, not tailored to a specific agent identity).

---

## Developer Certificate of Origin (DCO)

By contributing to this repository you certify the [Developer Certificate of Origin v1.1](https://developercertificate.org). All commits must be signed off:

```bash
git commit -s -m "feat(skills): add vendor-onboarding skill"
```

Contributions are licensed to Pipefy and to all recipients under the Apache License 2.0. Pull requests without sign-off will fail CI.

---

## Content review for regulated domains

Skills and blueprints under `skills/legal/`, `skills/human-resources/`, `skills/finance/`, `skills/compliance/` (and any domain involving decisions about natural persons) undergo **substantive review by Pipefy’s Privacy, Legal & Compliance team** before merge, in addition to the standard CI lint. Expect additional review time and possible content changes. Community-contributed skills are published as templates and do not constitute professional advice; Pipefy may decline, edit, or remove any contribution at its discretion.

Published blueprints in regulated domains must include a `COMPLIANCE.md` beside the skill (start from [`docs/compliance/COMPLIANCE.template.md`](docs/compliance/COMPLIANCE.template.md)).

---

## Questions

Open an issue or reach out at **dev@pipefy.com**.
