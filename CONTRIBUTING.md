# Contributing to ai-toolkit

Follow the guide for your change:

| Change | Guide |
| --- | --- |
| A skill (Markdown only) | [`docs/contributing/skills.md`](docs/contributing/skills.md#add-a-skill) |
| The SDK, the MCP server, or the CLI | [`docs/contributing/development.md`](docs/contributing/development.md) |
| Documentation | [`docs/contributing/authoring.md`](docs/contributing/authoring.md) |
| A design decision that outlives one change | [`docs/contributing/adr/`](docs/contributing/adr/README.md) |

## Developer Certificate of Origin (DCO)

By contributing to this repository, you certify the [Developer Certificate of Origin v1.1](https://developercertificate.org). Sign off every commit, because CI fails a pull request with an unsigned commit:

```bash
git commit -s -m "feat(skills): add vendor-onboarding skill"
```

Contributions are licensed to Pipefy and to all recipients under the Apache License 2.0.

## Content review for regulated domains

Pipefy's Privacy, Legal & Compliance team reviews every skill and blueprint under `skills/legal/`, `skills/human-resources/`, `skills/finance/`, and `skills/compliance/`, and any skill that decides about a natural person, before it merges. Expect more review time and possible content changes. A published blueprint in a regulated domain includes a `COMPLIANCE.md` beside the skill, started from [`COMPLIANCE.template.md`](template/COMPLIANCE.template.md).

Community skills are published as templates and are not professional advice. Pipefy may decline, edit, or remove any contribution.

## Questions

Open an issue, or write to **<dev@pipefy.com>**.
