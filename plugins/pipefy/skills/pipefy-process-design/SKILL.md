---
name: pipefy-process-design
description: >
  Designs a Pipefy process with the user before anyone builds it. Finds the
  start, the end states, the steps and owners, the decision rules with exact
  boundary values, the exceptions and the data. Compares a native rule, an AI
  automation, an AI agent, an integration and human work for each step.
  Returns a process specification that a builder can use. Use it when the user
  wants to think a process through ("help me design", "how should this flow
  work", "I do not know who approves"). Use it also when a request to build a
  whole process still has an open business decision. Use it when the user
  wants advice and no change, or brings a specification to check. Not for one
  part such as a field, a phase or one automation (pipefy-building). Not for
  building a process that is already specified (pipefy-building). Not for
  diagnosing an existing pipe (pipefy-process-intelligence) or sizing the
  return of a change (pipefy-process-impact).
tags: [pipefy, process-design, specification, consulting]
---

# Design a Pipefy process

This skill helps the user design a process before anyone builds it. The result is a process specification: the business decisions that a builder needs to build the process.

When an organization is connected, read the [MCP reference](references/mcp.md) or the [CLI reference](references/cli.md) for the reads in step 1. Load only the reference for your surface.

---

## When to use

- The user wants to think a process through. Examples: "help me design a purchasing process", "what is the best structure for incident handling", "I do not know who approves".
- The user asks to build a whole process, and a business decision that changes the build is still open. Examples: who approves, which value routes a case, what happens on a rejection. A verb such as "create" or "build" does not close the decision.
- The user wants advice and no change.
- The user brings a specification and wants a check.

## When not to use

Read `pipefy-building` for these requests. It sends each one to the skill that owns it.

- One part, such as a field, a phase, one automation, or one agent.
- A whole process that is already specified: every blocking field of the [process specification](#process-specification) has a value.
- A deletion, or a change to a part that already exists.

To diagnose an existing pipe, read `pipefy-process-intelligence`. To size the return of a change, read `pipefy-process-impact`.

## What this skill writes

- This skill does not write to Pipefy. It ends with a specification.
- A request for advice only gets advice. Write nothing and build nothing.
- A design works without a connected organization. Design from the conversation, and say that you did not check the existing pipes for reuse.
- When the user asks to build what you designed, read `pipefy-building`. It sends the build to the domain skills, or to a skill in your catalog that builds a whole process from a specification. Give that skill the specification.

---

## Ask in proportion to what is missing

- When the user brings a specification, do not interview. Compare it with the specification fields. Equal content in another format counts. Do not ask the user to rewrite it.
- When every blocking field has a value, return the specification in the contract format. Mark each value that you added as an assumption.
- When a blocking field has no value, ask only for that field. Ask all of them in one message, with a proposed answer for each.
- Do not ask again about a decision that the user or the specification already settled.
- Keep the user's names for phases, fields, and roles.
- When the user does not know the process, propose a structure and two alternatives. Ask 5 questions or fewer in a turn. Each question has a proposed answer.
- Use documents that the user gives and the pipes you can read before you ask.

## Steps

1. **Read what exists.** With a connected organization, list the pipes before you propose a new one. When a pipe already does part of the work, read what runs there and propose to reuse it. Without a connected organization, skip this step.

   | Operation | Read-only | Purpose |
   |-----------|-----------|---------|
   | `search_pipes` | Yes | List pipes within the caller's memberships and the per-organization cap. Inspect `search_limits` before declaring reuse discovery complete. |
   | `get_organization` | Yes | Read the organization that holds the pipes. |
   | `get_pipe` | Yes | Read the phases and fields of a pipe that you can reuse. |
   | `get_automations` | Yes | Read the rules that already run in that pipe. |
   | `get_ai_agents` | Yes | Read the AI agents that already run in that pipe (pipe `uuid`). |

2. **Find the blocking fields.** Compare the request with the [process specification](#process-specification). Sort each field into three groups: the user gave it, you can propose it, or it stays open.

3. **Propose a structure and alternatives.** When the structure is open, give one proposal and two concrete alternatives. For each one, give the cost, the risk, and the effect. The cost is the parts to build and maintain, and AI credits when known. The risk is what goes wrong, and who sees it. The effect is the work that it removes from the team or adds. Recommend one, and give the reason.

4. **Choose the Pipefy part for each step.** Use the [selection table](#choose-the-pipefy-part-for-each-step).

5. **Review the specification.** Use the [review questions](#review-questions). Ask only the ones that change the build.

6. **Return the specification and the summary.** Use the [output format](#output).

Read [references/process-specification.md](references/process-specification.md) when the user asks for a written specification, or when more than three decisions stay open. It has two complete specifications and what a builder does with each one.

Read [references/feature-selection.md](references/feature-selection.md) when two Pipefy parts fit the same step, or when the user asks why you chose one part and not another.

## Design principles

- **Start with the outcome.** What does "done" look like for a case?
- **Name phases for states, not actions.** "Under review", not "Review it".
- **Keep the start form short.** Ask only for the data that the requester has on day 1.
- **Make a field required only when a decision reads it.** Each required field can stop a card.
- **Plan for the exception.** A rejection, a pause for a fix, and a time limit each need a path.
- **One phase is one state of the case.** A participant is an owner of a phase, not a separate pipe, unless that work has its own cases.

---

## Process specification

The specification holds business decisions, not Pipefy ids. The builder finds ids and product limits when it builds. The builder never finds a business decision: it returns the decision to the user as a question.

| Field | What it holds | Who writes it | Blocks the build | Default when absent |
|---|---|---|---|---|
| Objective | The result that "done" gives, and what is out of scope. | User. The design skill writes it down. | Yes | None. Propose one sentence from the request and ask the user to confirm it. |
| Start trigger | What creates a case: a start form, an email, another pipe, a portal page. | User | Yes | A requester fills the start form. |
| End states | Each result that closes a case, with what the case must hold at that point. | User | Yes | One end phase for success. Add one end phase for refusal when a step can refuse. |
| Steps and owners | The ordered states of a case. Each state has one owner (a role), the person who decides, and the person who handles its exceptions. | Design skill proposes. User confirms. | Yes | The phases the user named. The owner is the role the user named, else the pipe members. |
| Decisions | For each branch: the field it reads, the operator, and the value. Also the result at the exact boundary value, the result for an empty field, and the destination. | User | Yes, but only for the branch | No automatic rule. A person in that phase decides. |
| Parallel work | The steps that run at the same time, and the join rule: all results, any result, or a stated combination. Also what happens to open work when one result ends the case. | User | No | No parallel work. Steps run in sequence. |
| Exceptions | Rejection: ends the case, or pauses it until someone fixes it. Time: a reminder only notifies, a deadline moves, escalates or reassigns. Correction: return point, owner, and the condition to continue. | User | No | A rejection pauses the case in an on-hold phase. A time limit is a reminder. A correction returns to the step that owns the missing data. No retry limit. |
| Data | For each field: name, type, source, author (role), the step where it is filled, and when it is required. | Design skill proposes. User confirms. | Yes, for a field that a decision reads | Only the fields that decisions and end states read. A field is required only when a decision reads it. |
| Platform choices | For each step: the Pipefy part that does it, one alternative, the reason in one line, and the existing part to reuse. | Design skill | No | The least complex native option in the selection table. No AI without an explicit yes. |
| Constraints | Limits the user states: no AI, no email outside the company, who may approve, data that must not leave Pipefy. | User | No | None stated. |
| Authorization | One level: advise only, build, build inactive, publish, or external effects allowed. For external effects, also state the build level and each permitted effect. | User | No | Advise only until the user requests a build. A build request defaults to build. No external effects. |
| Assumptions | Values that the design skill or the builder chose and the user did not confirm. | Design skill and builder | No. A rule that reads a business assumption starts inactive and waits for the user's answer. | Empty. The builder writes each assumption in the plan step that uses it. |
| Pending items | Open decisions, each with the work or activation that it blocks. | Design skill and builder | Only the named work or activation | Empty. |
| Acceptance examples | Two to five cases: input, expected path, final state. Include the boundary value, the empty value, and one exception. | Design skill proposes. User confirms. | No | One example for each decision branch, plus its boundary value and its empty value. The builder reports each example it did not check. |

Authorization levels:

- **Advise only.** No write. Use it when the user has not requested construction, or explicitly says to change nothing.
- **Build.** Create the parts of a new process and activate its automations and AI agents. This is the default for a build request. A new pipe has no cards, so no rule runs before the first card. The builder checks each part with the acceptance examples before a real card arrives.
- **Build inactive.** Create the parts, and keep every automation and AI agent inactive. Use it when the user asks for it.
- **Publish.** Also publish what has a draft state: a sub-portal, an integration flow. Create an HTML interface only when the user asks for one by name.
- **External effects allowed.** Permit only the effects that the user names: external email, member invitations, or a webhook. Record a separate build level. This permission does not activate or publish unrelated parts.

Without the publish level, a sub-portal stays unpublished and an integration flow stays a draft. Without permission for a named external effect, nothing sends data outside Pipefy.

At the build level, the builder creates these rules inactive. In this list, a rule is an automation or an AI agent.

- A rule that the build adds to a pipe that existed before this conversation, when the pipe has cards that the rule can match.
- A rule that runs on a time limit or a schedule, on a pipe that has cards.
- A rule that reads an unconfirmed business assumption (a pending item).
- A rule that moves a card through a phase connection that does not exist yet.

For the first two kinds, the builder reads the rule again, compares it with the specification, and then activates it. For an automation, use the "Create disabled" step in `pipefy-automations`. An AI agent is active by default, so create it disabled (`pipefy-ai-agents`). A rule that reads an unconfirmed assumption waits for the user's answer. A rule that needs a missing phase connection waits for the connection.

Rules that connect the design skill and the builder:

- A specification holds no ids. Do not invent an id to make a specification look complete.
- A complete specification gets no second questionnaire. The builder asks only about pending items.
- A pending item blocks only the dependent work or activation. The builder continues the independent work.
- If a rule reads an unconfirmed business assumption, record it as a pending item for that rule. Create it inactive. Activate it only after the user confirms the decision.
- "No AI" in Constraints removes AI from Platform choices. AI enters Platform choices as confirmed only after an explicit yes from the user. The user's answer to the review question about AI is that yes.

Specification template (one line for each field):

```text
Objective:
Start trigger:
End states:
Steps and owners:
Decisions:
Parallel work:
Exceptions:
Data:
Platform choices:
Constraints:
Authorization:
Assumptions:
Pending items:
Acceptance examples:
```

---

## Choose the Pipefy part for each step

Use the least complex part that gives the result and the controls the user needs. Before you propose a new part, check what already runs in the pipe and reuse it.

| Part | Choose it when | Ask before you choose it | Do not choose it when |
|---|---|---|---|
| Traditional automation | An event, a test on fields, and a supported action describe the step. | Does the native rule cover the whole requirement, including the exact boundary value and the empty value? | The step needs judgment that no field test can express. |
| AI automation | The step reads card fields or an attachment on one event. It writes a fixed output: a category, a summary, or a value from a document. Recommend it for that step. | Which representative examples show the quality that the team accepts? What happens when the output is wrong? | A field test decides the step. Use a traditional automation. |
| AI agent | The step needs process context, an action that an AI automation cannot take, or a trigger that only an agent has. Actions: move a card, create a card, ask a person to review the result, call a tool on an MCP server. Recommend one agent with one responsibility and 1 to 5 behaviors. | Which context, which action limits, and which human review does this responsibility need? | One prompt with fixed output fields does the work. Use an AI automation. The step runs on a schedule: `scheduler` is never an agent trigger. |
| Integration | Another system owns the data or the action. | Is one call on a card event enough (a webhook)? Or does the work need several steps, a schedule, or routing (an integration flow)? | The external action happens one time only. Do not create a permanent flow for it. |
| Human work, field condition, or formula | A person must judge with no fixed test, or automation costs more than it returns. A field condition shows or requires a field inside a phase. A formula field calculates a value from other fields. | Can a field condition, a formula, or a clear task for a named owner solve the problem? | A rule with a field test does the same work with less effort. |

Rules for the choice:

- Native rule before AI. Do not stack a rule and AI on the same step. When a rule leaves part of the step manual, name the AI step as optional.
- Integration and AI are separate choices. A flow can read data from another system, an AI step can read the content, and a rule can route the result.
- Repeated work alone does not prove a need for AI. A document to read does not prove a need for a new agent.
- A missing automation or agent is not an improvement by itself. Some results need human work, a field condition, or a formula.
- For each choice, write the work it removes, the alternative, and the cost: maintenance, credits when known, and the effect of an error.
- When the user did not exclude AI and an AI row fits the step, recommend that AI part. Give the reason, the test, and what happens when the output is wrong. Ask about it with the review questions. The user's answer there is the explicit yes: do not ask again, and the builder does not ask again. Do not record AI as a confirmed choice without that yes.

---

## Review questions

Use these questions to check a specification. Ask the user only the ones that change the build, in one message. The user's answers confirm the specification, and they include the yes to each AI recommendation. Do not ask again before the build.

| Question | It finds | Change in the specification |
|---|---|---|
| What creates a case? Can a case start in another way, such as an email or another pipe? | A start path with no data rules | Start trigger lists each source and the data it must bring. |
| For each decision, what happens at the exact boundary value, and when the field is empty? | A branch with no result at the edge | Decisions get the boundary result and the empty result. Acceptance examples test both. |
| Can two conditions be true at the same time, or can a case match no condition? | Overlaps and gaps | Decisions get one result for each case, plus a default path. |
| Does work run at the same time? Does the next step need all results, any result, or a stated combination? | A missing join rule | Parallel work gets its join rule. |
| When one parallel result ends the case, what happens to the open work? | Open work with no owner | Parallel work gets its cancellation rule. |
| Is a rejection a normal end, or does it pause the case until someone fixes it? | A rejection that should be an interruption, or the opposite | Exceptions say "ends" or "pauses". End states or an on-hold phase change. |
| Does a time limit only remind, or does it move, escalate, or reassign the case? | A reminder that should be a deadline | Exceptions name the action and the new owner. |
| When work returns for correction, where does it return, who fixes it, and what lets it continue? | A loop with no exit | Exceptions get the return point, the owner, and the exit condition. Do not invent a retry limit. |
| Is this the process today, the target process, or an optional improvement? | Proposals recorded as facts | Assumptions and Platform choices mark what the user did not confirm. |
| Which Pipefy part does each step? Is each activity really a phase, and is each participant really a separate pipe? | Too many phases or pipes | Platform choices get one part for each step, with reuse. |
| Do you accept AI for each step where the design recommends it? | AI recorded without a yes | A yes marks that AI line as confirmed. A no makes the alternative the choice. |
| Does a rule go into a pipe that has cards today? Does a rule read an assumption that nobody confirmed? | A rule that acts on real cards before anyone checks it | Platform choices mark that rule to start inactive, with the reason. |

---

## Output

End the design with the specification in the template format, then this summary:

```text
Process: <name>
Pending items: <each open decision with the part it blocks, or "none">
Manual steps: <parts that only the Pipefy interface creates, or "none">
Impact: <one line: time this design returns to the team against a fully manual run of the same flow; if a phase exists only for human triage, what an automation or an AI agent would change there. Do not start a pipe diagnosis.>
Next step: <one offer with a one-line reason. Nothing is built until the user says yes.>
```

- Say that the specification is ready to build only when every blocking field has a value. Otherwise name each field that is missing.
- When the user wants to build next, the next step is the handoff to `pipefy-building`, with the specification. Say that the build activates the new parts, and name each rule that starts inactive, with the reason.

Manual steps name the parts of the design that only the Pipefy UI creates:

- Phase connections other than the links that a new phase gets to its neighbours (`pipefy-pipes-and-cards`).
- Email templates (`pipefy-members-email-webhooks`).
- Rules that apply a label (`pipefy-automations`).

Keep Impact to one line. Do not invent volume, hourly cost, or lead time; name every missing number and ask for all of them in one question. For a fuller justification, read `pipefy-process-impact`.

## Success criteria

- Every blocking field of the specification has a value, or it is a pending item with the part it blocks.
- Each step has one Pipefy part, one alternative, and a reason. No AI is a confirmed choice without an explicit yes.
- The design reuses the pipes and parts that already exist, or it says that nobody checked them.
- The design promises only parts that Pipefy can build, and it names the manual steps.
- Nothing was written to Pipefy.

## See also

- `pipefy-building`: read it when the user asks to build. It routes the build.
- `pipefy-pipes-and-cards`: phases, fields, field conditions, and phase connections.
- `pipefy-automations`: traditional and AI automations, and their limits.
- `pipefy-ai-agents`: AI agents and their behaviors.
- `pipefy-process-intelligence`: diagnose an existing pipe. This skill designs a new one.
- `pipefy-process-impact`: justify a material change in full. This skill only emits the Impact line.
