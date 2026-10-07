# RFC-0002: Every test guards a behavior

Status: Draft
Author: Gabriel Custodio
Created: 2026-10-07
Discussion: the pull request that adds this file

## Summary

Every test in the toolkit should protect a behavior that a caller can observe, and fail on a regression that could really happen. Today a large share of the suite asserts how the code is built, not what it does, so those tests break on safe refactors and pass on real bugs. This RFC proposes a gate for new tests, a baseline that stops the count of weak tests from growing, and an audit procedure that shrinks it.

## Problem

The suite is larger than the code it tests. On `dev` at `e85483bf`, 204 test files hold 4,134 tests in 90,315 lines, against 55,495 lines of package source. Size alone is not a defect. The defect is the share of tests that assert the implementation, because each of them costs maintenance and adds little confidence.

A scan of the syntax trees of every test on `dev` found these signals. Each count is a list of candidates, not a verdict:

| Signal | Count | Why it is a candidate |
|---|---|---|
| Mock call-shape assertions (`assert_called*`, `assert_awaited*`, `call_count ==`) | 830 | They assert that a call happened, not what the caller received |
| `patch(` calls | 412, in 78 files that build mocks | A mock tests the author's understanding of a dependency, not the dependency |
| Imports of a `_private` symbol from a `pipefy*` package | 36 | A test bound to a private name breaks on a rename that changes no behavior |
| Tests whose only checks are mock call shapes | 22 | Nothing they assert is visible to a caller |
| Tests whose only asserts are `is not None` or `isinstance` | 20 | The name promises more than the test checks |
| Tests with no `assert`, `raises`, or `assert_*` call | 19 | They can fail only on an exception |

The most common assertion in the suite is `executor.execute_query.assert_awaited_once()`, with 28 uses, plus `assert_called_once()` on the same method 20 times. A test that checks only that the executor was called once passes when the method sends the wrong query, parses the response wrongly, or returns the wrong value.

Some candidates are legitimate. `test_validate_https_allow_insecure_accepts_http_localhost` has no assert because "does not raise" is its contract. For this reason, the counts above are a starting baseline, and each removal needs evidence, not a pattern match.

No written rule rejects these tests today. A reviewer who objects to a mock-heavy test has only taste to point to, and the author has the existing 830 assertions as precedent.

## Goals

1. **New tests guard behavior.** A new or changed test names the behavior it protects and the regression that makes it fail, and it asserts through the surface a real caller uses.
2. **Weak tests only decrease.** The count of each countable weak pattern can go down and never up.
3. **Each contract has one owning test.** A behavior is tested once, at the strongest boundary that reaches it, and other layers test only risks of their own.

Each goal has a measure:

| Measure | Today on `dev` | Target |
|---|---|---|
| Tests with no assertion, excluding those marked as "does not raise" | 19 | 0 |
| Tests whose only checks are mock call shapes | 22 | 0 |
| Tests whose only asserts are `is not None` or `isinstance` | 20 | 0 |
| Imports of private symbols in tests | 36 | 0 |
| Mock call-shape assertions | 830 | Down, with no fixed target |

The last measure has no target because some call-shape assertions are the contract, such as a test that a destructive tool makes no write call before confirmation.

## Non-goals

- A coverage percentage. Coverage counts the lines that run, not the behaviors that are checked, so it rewards the tests this RFC targets.
- Deleting tests to reach a number. The goal is confidence, and a removal without evidence lowers it.
- Speed or layout of the suite. A test that is slow or static is not weak for that reason.

## Proposal

### Part A: an authoring gate for new tests

Three rules join the testing conventions, next to TEST-1 to TEST-3 ("a port's contract suite runs against the real adapter and every fake", "exercise real infrastructure over mocks", and "drive a package through its driving port"):

- **TEST-4. A test names the regression that makes it fail.** Why: a test that no credible change can fail costs maintenance and protects nothing.
- **TEST-5. One contract has one owning test, at the strongest boundary.** Another layer adds a test only for a risk the owner cannot reach, such as a transport failure. Why: duplicate tests multiply the cost of a change without adding confidence.
- **TEST-6. Production code has no seam that only a test uses.** A test that needs a private export, a flag, or a hook moves to the public boundary instead. Why: a test-only seam binds the test to the structure and keeps dead code alive.

A regression test must fail on the code before the fix, for the reason the bug report states. A regression test that never failed proves the mock, not the fix.

### Part B: a baseline that only shrinks

A test, `tests/test_test_hygiene.py`, walks the syntax tree of every test file and collects the countable patterns from the measures table. It compares them with a committed file, `tests/test_hygiene_baseline.txt`, which lists today's violations by test ID.

- A new violation fails CI, and the message names the rule it breaks.
- A violation that disappears also fails CI until its line leaves the baseline file. This keeps the file honest, so the remaining work is readable from the file.
- A test whose contract is "does not raise" carries a marker, such as `@pytest.mark.no_raise_contract`, and the scan skips it.

Fitness functions in *Building Evolutionary Architectures* and tools such as Betterer work the same way: the check measures how far the code is from the goal, and it allows movement in one direction only.

### Part C: an audit procedure for the rest

Most weak patterns need judgment that a scan cannot make: two tests that prove the same contract, an expected value computed by the renderer under test, or a negative test that passes for an unrelated reason. A skill, `.claude/skills/test-audit/SKILL.md`, gives an agent or a contributor the procedure. It is adapted from the [`test-audit` skill in OpenClaw](https://github.com/openclaw/openclaw/blob/main/.agents/skills/test-audit/SKILL.md), and it keeps three parts of that skill:

1. **The evidence for a candidate.** The test name and location, the failure it can actually detect, the non-test callers of the code it covers, the stronger test that remains, and the command that validates the change. A candidate with a missing field is not ready for removal.
2. **The retention bar.** A test stays when it is the only guard of a public API, a protocol, a config key, a security rule, or a release contract, even when it looks like an implementation test.
3. **The batch shape.** One pull request covers one package, and it removes the test-only seams that its deletions free.

The skill cites the TEST rules by ID and does not restate them.

## Rollout

| Phase | Scope | Gate to the next phase |
|---|---|---|
| 0. Rules | TEST-4 to TEST-6 added to the testing conventions | The rules are accepted |
| 1. Baseline | `tests/test_test_hygiene.py` and its baseline file, with the markers for "does not raise" tests | CI fails on a new violation |
| 2. Skill | The audit skill, adapted to this repository's paths and commands | One audit pull request lands with it |
| 3. Audits | One pull request per package, starting with `packages/auth/tests`, which holds several of the weak-assert and no-assert candidates | Every countable pattern is at 0 |

Phase 3 runs over many pull requests, and each one shows its progress as lines removed from the baseline file.

## Alternatives considered

**Review only, with no baseline.** Reviewers would apply the TEST rules by reading. That is what happens today, and the count of mock assertions grew to 830 under it.

**A lint rule that bans mocks.** A ban would fail on day one across 78 files, and some mocks are correct, such as a fake clock. A baseline lets the existing cases stay while it stops new ones.

**A one-time cleanup.** One large pull request would remove the weak tests at once. It would be hard to review, and without a check, the patterns would return.

## Risks and costs

- **False positives.** The scan matches syntax, not intent, so it will flag some correct tests. The marker for "does not raise" tests and an explicit allow entry in the baseline file handle these cases.
- **Friction for contributors.** A new check is another way for a pull request to fail. The failure message names the rule and the fix.
- **Lost coverage.** An audit can remove a test that was the only guard of a behavior. The evidence fields in Part C and the retention bar exist to prevent this.

## Open questions

- Should the pull request that adds this RFC include the working baseline test, so reviewers can run it, or only propose it?
- Where do the TEST rules live on `dev`, which has no `conventions.md` yet?
- Does the mock call-shape count get a target, or does it only need to decrease?
- Do integration tests against the live Pipefy API count toward the baseline, or only the offline suite?

## References

- [`test-audit` skill](https://github.com/openclaw/openclaw/blob/main/.agents/skills/test-audit/SKILL.md), OpenClaw
- *Building Evolutionary Architectures*, Neal Ford, Rebecca Parsons, and Patrick Kua, 2017, for fitness functions
- [Betterer](https://phenomnomnominal.github.io/betterer/), a baseline tool for incremental improvement

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/contributing/rfc/0002-every-test-guards-a-behavior.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/contributing/rfc/0002-every-test-guards-a-behavior.md).
