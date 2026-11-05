# Process specification examples

This file has two complete process specifications in the contract format of the skill, and what a builder does with each one.

Contents:

- [Example 1: purchase requests (Portuguese)](#example-1-purchase-requests-portuguese)
- [Example 2: vendor approval with parallel reviews](#example-2-vendor-approval-with-parallel-reviews)
- [Common structures](#common-structures)

---

## Example 1: purchase requests (Portuguese)

The user wrote in Portuguese. The specification keeps the user's language and the user's names for phases, fields, and roles. The labels follow the field order of the contract.

```text
Objetivo: aprovar ou recusar pedidos de compra em até 3 dias úteis. Fora do escopo: emitir o PO no ERP.
Gatilho de início: o solicitante preenche o formulário inicial do pipe.
Estados finais: "Aprovado", com o número do PO preenchido; "Recusado", com o motivo preenchido.
Etapas e responsáveis:
  1. Solicitação: solicitante.
  2. Análise: comprador (papel: compras). Decide se o pedido segue.
  3. Aprovação gerencial: gerente da área do solicitante. Decide aprovar ou recusar.
  4. Aguardando documento: solicitante corrige.
  5. Aprovado (final).
  6. Recusado (final).
Decisões:
  D1. Parecer de compras = Aprovar e Valor >= R$ 5.000,00 -> Aprovação gerencial.
      Valor exatamente R$ 5.000,00 sobe ao gerente.
      Valor < R$ 5.000,00 -> Aprovado sem gerente.
      Valor vazio -> volta a Solicitação com a tarefa "informar valor".
  D2. Parecer de compras = Recusar -> Recusado.
  D3. Parecer de compras = Falta documento -> Aguardando documento.
  D4. Decisão do gerente = Aprovar -> Aprovado. Recusar -> Recusado.
Trabalho paralelo: nenhum.
Exceções:
  Rejeição: a recusa encerra o caso (Recusado). Não é interrupção.
  Interrupção: falta de documento leva a Aguardando documento. O solicitante anexa e o caso volta a Análise. Sem limite de tentativas.
  Tempo: Análise com mais de 2 dias úteis -> lembrete ao comprador. Só notifica, não move.
Dados:
  Valor: moeda, formulário inicial, solicitante, obrigatório.
  Centro de custo: seleção, formulário inicial, solicitante, obrigatório.
  Parecer de compras: seleção (Aprovar, Recusar, Falta documento), Análise, comprador, obrigatório para sair de Análise.
  Decisão do gerente: seleção (Aprovar, Recusar), Aprovação gerencial, gerente, obrigatório para sair da fase.
  Motivo da recusa: texto longo, Análise ou Aprovação gerencial, quem recusa, obrigatório só quando o parecer ou a decisão é Recusar.
  Número do PO: texto curto, Aprovado, comprador, obrigatório.
Escolhas de plataforma:
  D1 a D4: automação tradicional (campo atualizado + condição sobre Valor e parecer). Alternativa: encaminhamento manual pelo responsável da fase. Motivo: a decisão lê campos e um valor fixo.
  Motivo da recusa: condição de campo (mostra e exige só na recusa). Alternativa: campo sempre visível.
  Lembrete: automação por prazo da fase (SLA). Alternativa: lembrete manual do gerente de compras.
Restrições: sem IA (política do financeiro). Nenhum e-mail para fora da empresa.
Autorização: construir inativo.
Premissas: abaixo de R$ 5.000,00, compras aprova sem gerente.
Pendências:
  P1. Quem recebe o lembrete de Análise nas férias do comprador. Bloqueia só o destinatário substituto do lembrete.
  P2. Confirmar se compras aprova abaixo de R$ 5.000,00 sem gerente. Bloqueia só a ativação da regra de aprovação abaixo desse valor.
Exemplos de aceitação:
  A1. Valor 4.999,99, parecer Aprovar -> Aprovado, sem passar pelo gerente.
  A2. Valor 5.000,00, parecer Aprovar -> Aprovação gerencial.
  A3. Valor vazio -> volta a Solicitação com a tarefa "informar valor".
  A4. Parecer Falta documento -> Aguardando documento; depois do anexo, volta a Análise.
  A5. Gerente escolhe Recusar sem motivo -> o card não sai da fase.
```

What a builder does with it:

1. The specification supports an inactive build. The builder asks only about P1 and P2.
2. It lists the pipes and compares the names ("Compras", "Pedidos de compra", "Purchase"). With no plausible match, it continues. With a match, it stops and asks the user before it uses that pipe or creates another one.
3. It resolves three technical details without a question:
   - The native conditions have no "greater than or equal" test. D1 becomes `number_greater_than` 4999.99 for the manager path and `number_less_than` 5000 for the path without the manager. A1 and A2 check the boundary.
   - Valor is required on the start form, so the form already stops A3. The builder creates no return rule and records A3 as covered by the required field.
   - Six moves skip a neighbor phase. A new pipe connects each phase only to the phases beside it. After it creates the pipe, the builder reads the connections with `get_phase_allowed_move_targets`. It lists each missing connection as a manual step. The six moves:
     - Análise to Aprovado, Análise to Recusado, and Análise to Aguardando documento.
     - Aguardando documento to Análise.
     - Aprovação gerencial to Aprovado, and Aprovação gerencial to Recusado.
4. It asks about P1 and P2 in one message, each with a proposed answer. The low-value approval rule stays inactive while P2 is open.
5. It builds the pipe with its phases and start form first. Then it builds the phase fields and the field condition for Motivo da recusa. Last, it builds the rules and the reminder. All rules stay inactive. D1 and D4 each need two rules, one for each destination.
6. It reads back each rule and the field condition, compares them with the specification, and names each difference.
7. It builds no AI, because of the constraint. It activates nothing, because the authorization is "build inactive".

Questions that the builder returns, in the user's language:

```text
1. P1. Quem recebe o lembrete de Análise quando o comprador está de férias? Proposta: o gerente de compras.
2. P2. Abaixo de R$ 5.000,00, compras aprova sem o gerente? Proposta: sim. A regra fica inativa até a confirmação.
```

Report at the end of the build:

```text
Pipe Pedidos de compra (<id>): created
Field condition Motivo só na recusa (<id>): created
Automation Valor a partir de 5.000 vai ao gerente (<id>): created inactive
Automation Valor abaixo de 5.000 aprova (<id>): created inactive
Automation Parecer Recusar encerra (<id>): created inactive
Automation Parecer Falta documento pausa (<id>): created inactive
Automation Gerente aprova (<id>): created inactive
Automation Gerente recusa (<id>): created inactive
Automation Lembrete de Análise (<id>): created inactive
Manual steps: six phase connections, from Análise to Aprovado and five more. Only the Pipefy interface creates them.
Next step: confirm P2 and create the missing phase connections before activating the affected rules. Nothing runs until the user authorizes activation.
```

The process is not ready for use: the rules are inactive and the phase connections are missing. A1, A2, and A5 are checked by a read of the rule and the condition. They did not run, because the rules are inactive. A3 is covered by the required field. A4 depends on the phase connections.

---

## Example 2: vendor approval with parallel reviews

This example has parallel work with a join rule and a cancellation rule. It also has a rejection that ends the case, and an AI option without a yes from the user.

```text
Objective: approve a new vendor for payment in 10 business days or less. Out of scope: contract signature.
Start trigger: a buyer fills the start form with the vendor data and three documents.
End states: Approved, with a vendor code. Rejected, with the reason of the reviewer who rejected.
Steps and owners:
  1. Intake: buyer.
  2. Document check: procurement analyst. Decides if the document package is complete.
  3. Reviews: Legal reviewer and Finance reviewer, at the same time.
  4. Vendor setup: procurement analyst writes the vendor code.
  5. Approved (end).
  6. Rejected (end).
  7. On hold: buyer fixes the documents.
Decisions:
  D1. Document check: all three documents attached -> Reviews. One or more missing -> On hold.
  D2. Expected annual spend below 10,000.00 -> Finance decision = Not required. At exactly 10,000.00, Finance reviews.
      Empty spend: not possible, the start form requires it.
  D3. Legal = Approved AND (Finance = Approved OR Finance = Not required) -> Vendor setup. P2 blocks activation.
  D4. Legal = Rejected OR Finance = Rejected -> Rejected.
Parallel work: Legal and Finance review in the same phase, at the same time. Join: both results. Not required counts as a result only after confirmation (P2).
  Cancellation: when one reviewer rejects, the case moves to Rejected and the other review stops.
Exceptions:
  Rejection ends the case. It does not pause it.
  A missing document pauses the case in On hold. The buyer attaches it and the case returns to Document check. No retry limit.
  Time: Reviews for more than 3 business days -> reminder to both reviewers (notify only).
  Time: Reviews for more than 7 business days -> deadline. The case goes to a new owner (see P1).
Data:
  Expected annual spend: currency, start form, buyer, required.
  Tax certificate, Bank letter, Signed form: attachments, start form, buyer, required for D1.
  Legal decision: select (Approved, Rejected), Reviews, Legal reviewer, not required to leave Reviews. D3 requires Approved for Vendor setup.
  Finance decision: select (Approved, Rejected, Not required), Reviews, Finance reviewer or the D2 rule.
  Rejection reason: long text, Reviews, the reviewer who rejects, required when a decision is Rejected.
  Vendor code: short text, Vendor setup, procurement analyst, required.
Platform choices:
  D2: traditional automation when a card enters Reviews, with a spend condition. It sets Finance decision to Not required below 10,000.00.
    Alternative: the Finance reviewer sets the field.
  D3, D4: traditional automations on a decision field update, with conditions. Alternative: child cards in a separate review pipe.
    Reason: two fields in one phase hold both results, and the rules read fields.
  Rejection reason: field condition. Alternative: a field that is always visible.
  Reminder at 3 days: automation on the phase time limit. Alternative: a manual follow-up.
  Read the tax id and the expiry date from the tax certificate: option, AI automation.
    Reason: the step reads a document. Test: 20 sample certificates read correctly, and a wrong date goes to the analyst.
    State: option only. The user did not say yes to AI.
  Email to the vendor on rejection: email template and an automation that sends it. This is an external effect.
Constraints: only the Legal reviewer approves legal terms. Bank data does not leave Pipefy.
Authorization: activate ("build it and activate it"). External effects: not allowed.
Assumptions: Finance = Not required counts as a Finance result in the join.
Pending items:
  P1. Who owns the case at the 7-day deadline. Blocks only the deadline rule.
  P2. Does Not required count as a Finance result in the join? Blocks only D3 activation.
Acceptance examples:
  A1. After P2 is confirmed: spend 9,999.99, Legal Approved -> Vendor setup. Finance is Not required.
  A2. Spend 10,000.00, Legal Approved, Finance empty -> the case stays in Reviews.
  A3. Finance Rejected, Legal empty, rejection reason filled -> Rejected. The Legal review stops.
  A4. Legal Rejected while Finance is open -> Rejected. The Finance review stops.
  A5. Bank letter missing -> On hold. After the buyer attaches it -> Document check.
```

What a builder does with it:

1. The specification supports a partial build. The builder asks only about P1 and P2.
2. It lists the pipes and compares names. It finds no plausible match and continues.
3. It resolves technical details without a question:
   - D3 is an OR of two AND groups. One rule condition holds it: `[[legal_approved, finance_approved], [legal_approved, finance_not_required]]`.
   - D2 uses `card_moved`, filtered to Reviews, and `number_less_than` 10000. It does not depend on `field_updated` from start-form population. A2 checks that 10,000.00 goes to Finance.
   - D4 fires on a change to either decision field. The rule lists both fields as its trigger fields.
   - It checks the phase moves with `get_phase_allowed_move_targets`. Three moves skip a neighbor phase: Document check to On hold, Reviews to Rejected, On hold to Document check. It lists them as a manual step.
4. It does not build the AI automation, because the user did not say yes. It lists the AI automation as an offer.
5. It does not create the vendor email. External effects are not allowed, and only the Pipefy interface creates an email template.
6. It does not create the deadline rule, because P1 blocks it. It builds the rest.
7. Authorization is "activate", so activation is the last step of the same build. D3 stays inactive until the user confirms P2. The three rules that need a missing phase connection also stay inactive. It activates only independent rules that can run now.
8. It reads back each rule and compares it with the specification. It names each difference.

Questions that the builder returns, in one message with the build plan:

1. P1. At the 7-day deadline, who owns the case? Proposed: the procurement manager.
2. P2. Does Not required count as a Finance result, so that Legal approval alone moves the case? Proposed: yes. Until confirmation, D3 stays inactive.

---

## Common structures

Use these structures as a start for a proposal. Change them to fit the decisions that the user gives.

- **Linear approval.** Submission, Under review, then Approved or Rejected. The requester fills the start form. The review phase holds the approver's decision field. A rule routes the case on that field.
- **Multi-stage work.** Intake, Triage, In progress, Testing, Done. Each phase has the fields of its owner. Rules move a card when a field test is true. A phase time limit sends a reminder.
- **Central intake with related pipes.** One intake pipe receives every request. A pipe relation connects it to the pipes that do the specialized work. A rule creates a connected card when a case needs that work. Use this structure only when each related pipe has its own cases and owners.
