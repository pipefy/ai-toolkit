# CLI reference

| Operation | Command |
|-----------|---------|
| `search_pipes` | `pipefy pipe list --name <text>` |
| `get_organization` | `pipefy org get <ORGANIZATION_ID>` |
| `get_pipe` | `pipefy pipe get <PIPE_ID> --json` |
| `get_automations` | `pipefy automation list --pipe <PIPE_ID> --json` |
| `get_ai_agents` | `pipefy agent list --repo <PIPE_UUID> --json` |

`--repo` takes the pipe UUID that `pipefy pipe get` returns, not the numeric pipe id.

`pipefy automation list` returns one page of up to 50 rules. While `pageInfo.hasNextPage` is true, run it again with `--after <pageInfo.endCursor>`.

When the design is ready to build, read `pipefy-building`. It names the domain skill for each part.
