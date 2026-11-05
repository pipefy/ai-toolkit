# Feature selection: criteria and edge cases

This file adds to the selection table in the skill: the limits of each part, and the cases where the first choice is often wrong.

Contents:

- [How to write a choice](#how-to-write-a-choice)
- [Traditional automation](#traditional-automation)
- [AI automation](#ai-automation)
- [AI agent](#ai-agent)
- [Integration](#integration)
- [Human work, field condition, or formula](#human-work-field-condition-or-formula)
- [Other parts of a design](#other-parts-of-a-design)
- [Edge cases](#edge-cases)

---

## How to write a choice

Write one line for each step in Platform choices:

```text
<step>: <part>. Alternative: <part>. Reason: <one line>. Cost: <maintenance, credits when known, effect of an error>. Reuse: <existing part, or "none">.
```

- Name the work that the part removes. "Moves the card when the review is done" is a result. "Adds an automation" is not.
- Name one alternative, also when the choice is clear. The user can then see what you did not choose.
- For an AI part, also write the test and the effect of a wrong output. Until the user says yes in the review, write "recommended, not confirmed" in the line. After the yes, write "confirmed".

---

## Traditional automation

- **Boundary values.** The native number tests are "greater than" and "less than". A rule for "5,000.00 or more" uses "greater than 4,999.99", or the other path uses "less than 5,000.00". Write the boundary result in Decisions so that the builder can test it.
- **Empty values.** Give the empty case its own result. Make the field required in the phase that collects it, or add a rule with the `blank` test.
- **Phase moves.** A move rule needs a connection between the two phases. A new pipe connects each phase only to the phases beside it. Other connections are a manual step in the Pipefy interface. See `pipefy-pipes-and-cards`.
- **Labels.** No automation action applies a label to a card. Propose a status field that a rule fills, or a manual step. See `pipefy-automations`.
- **Email.** A rule that sends email needs an email template. Only the Pipefy interface creates a template. Email to an address outside the company is an external effect.
- **Event and action pairs.** Not every event works with every action. Before you promise a rule, check the pair in `pipefy-automations`.

Cost: low maintenance. A wrong rule moves or changes cards without a person. Ask for acceptance examples at the boundary value and the empty value.

---

## AI automation

- **When to recommend it.** The step reads card fields or an attachment on one event. It writes a fixed output: a category, a summary, or a value from a document. Recommend an AI automation for that step. When a field test decides the step, recommend a traditional automation.
- **Fixed output.** The output goes into fields that you can name before the build. When you cannot name the output fields, the step is not an AI automation.
- **Test.** Ask for representative examples, such as 20 real documents, and the quality that the team accepts. The test is part of the recommendation.
- **Wrong output.** Say what happens when the output is wrong: a person checks it in the next phase, or a field condition asks for a review.
- **Credits.** An AI automation uses AI credits. Give the number of runs when the user knows the volume, so that the user can see the cost.
- **Trigger.** An AI automation runs on one card event, such as a new card or a move to a phase. When the step needs a trigger that an AI automation does not offer, recommend an AI agent. Before you promise a trigger, check the pair in `pipefy-automations`.
- **Consent.** Ask about the recommendation with the review questions. The user's yes there is the explicit yes, and nobody asks again. Without that yes, the line stays "recommended, not confirmed".

---

## AI agent

- **When to recommend it.** The step needs process context, an action that an AI automation cannot take, or a trigger that only an agent has. Recommend one agent with one responsibility for that step.
- **Actions.** An agent can update a card, move a card, or create a card or a connected card. It can also create a table record and send an email template. It can ask a person to review the result (`human_validation`) and call a tool on an MCP server (`mcp_tool`).
- **Start.** An agent starts on one of these triggers, without a conversation. See `pipefy-ai-agents`.
  - A card enters a phase, or a card leaves a phase.
  - A field is updated, or a card is created.
  - An alert is triggered (`sla_based`).
  - An email is received.
  - All connected cards move to a phase.
  - An HTTP response is received.
  - An interface button is clicked.
- **No schedule.** `scheduler` is never an agent trigger. For a step on a schedule, use a traditional automation or an integration flow.
- **Scope.** Give one agent one responsibility. An agent has 1 to 5 behaviors. When the work needs more, split the responsibility.
- **Action limits.** Name the actions the agent may take. An action that approves, rejects, pays, or sends a message outside the company needs a human review before it runs.
- **Not an agent.** When one prompt with fixed output fields does the work, use an AI automation. It is less to maintain and easier to test.
- **Consent.** The same rule as for an AI automation: the user's yes in the review confirms the agent.

---

## Integration

| Need | Part | Why |
|---|---|---|
| One call to another system on a card event | Webhook | One call, no steps between. See `pipefy-members-email-webhooks`. |
| Several steps, a schedule, routing, or a connected app | Integration flow (iPaaS) | The flow holds the steps and the connection. See `pipefy-ipaas`. |
| An action that happens one time only, such as a data import | No permanent part | Do the action one time. A permanent flow is maintenance with no return. |

- A webhook has no off state. It sends data to the other system on the first event. Treat it as an external effect.
- An integration flow has a draft state. It runs only after someone publishes it.

---

## Human work, field condition, or formula

- **Human work.** Give the step a named owner, the fields that the owner fills, and a time limit. A clear task for a named owner is a valid design.
- **Field condition.** Shows, hides, or requires a field inside a phase, based on another field. Use it for a reason that is required only on a rejection.
- **Formula.** A formula field calculates a value from other fields, such as a total. Use it before a rule that copies or adds values.
- **Low volume.** When a step runs a few times a month, a rule can cost more to maintain than the work it removes. Say so, and propose human work.

---

## Other parts of a design

| Need | Part | See |
|---|---|---|
| Reference data that many cases read, such as a vendor list | Database table | `pipefy-database-tables` |
| A link between cases in two processes | Pipe relation or table relation | `pipefy-relations` |
| A page where people outside the pipe start or follow a case | Portal page or sub-portal | `pipefy-portal-setup` |
| A standalone page with live data from pipes and tables | HTML interface, only when the user asks for one by name | `pipefy-html-interfaces` |

---

## Edge cases

| Case | First choice that is often wrong | Better choice | Why |
|---|---|---|---|
| The same manual step runs 200 times a week, and a field test decides it | AI automation | Traditional automation | Repeated work alone does not prove a need for AI. |
| A document arrives, and the team reads two values from it | New AI agent | AI automation with two output fields, recommended | A fixed output does not need an agent. |
| A rule routes most cases, and a small part stays manual | Rule and AI on the same step | Rule, with the AI step named as optional | Two parts on one step are hard to test and to maintain. |
| The user said "no AI" | AI recommended | No AI in Platform choices | The constraint removes the recommendation. |
| An AI step must run every morning | AI agent on a schedule | A traditional automation or an integration flow on the schedule | `scheduler` is never an agent trigger. |
| Two teams review at the same time | A separate pipe for each team | Two decision fields in one phase, with a join rule | One phase keeps one case. Use child cards in a separate pipe only when each review has its own cases and owners. |
| A time limit must move the case to a new owner | A reminder | A deadline rule with the new owner named | A reminder only notifies. |
| A rejection must notify a vendor outside the company | An automation that sends email | An email template made in the Pipefy interface, plus a rule, after a yes to external effects | The template is a manual step, and the email is an external effect. |
| Each participant gets a pipe | One pipe for each role | One pipe, one phase owner for each role | A participant is an owner, not a process. |
| The pipe has no automation, so the design adds one | New automation | Human work, a field condition, or a formula, when they give the result | A missing automation is not an improvement by itself. |
| A step needs a data copy one time | Integration flow | One manual import | A permanent flow for a one-time action is maintenance with no return. |
