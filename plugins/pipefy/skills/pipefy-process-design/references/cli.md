# CLI reference

| Operation | Command |
|-----------|---------|
| `search_pipes` | `pipefy pipe list --json` |
| `get_organization` | `pipefy org get <ORGANIZATION_ID>` |
| `get_pipe` | `pipefy pipe get <PIPE_ID> --json` |
| `get_automations` | `pipefy automation list --pipe <PIPE_ID> --json` |
| `get_ai_agents` | `pipefy agent list --repo <PIPE_UUID> --json` |

Run `pipefy pipe list` without `--name` to list pipes for the reuse check. The list holds only the pipes that the caller belongs to, with a cap per organization (`--max-per-org`, up to 500). Read `search_limits.max_pipes_per_org` before you treat the result as complete. Without a name filter, `pipes_truncated: true` can also come from membership scope, so the flag alone does not prove that the cap removed results.

Report unresolved access or cap limits in the reuse assessment. A short list does not prove that no reusable pipe exists outside the returned scope.

`--repo` takes the pipe UUID that `pipefy pipe get` returns, not the numeric pipe id.

`pipefy automation list` returns one page of up to 50 rules. While `pageInfo.hasNextPage` is true, run it again with `--after <pageInfo.endCursor>`.

When the design is ready to build, read `pipefy-building`. It names the domain skill for each part.
