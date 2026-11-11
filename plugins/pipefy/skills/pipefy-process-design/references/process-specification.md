# Process specification examples

This file has two complete process specifications in the contract format of the skill. Use the owning domain skills for implementation constraints.

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
      Valor vazio: não acontece, o formulário inicial exige o valor.
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
  D1 a D4: automação tradicional (campo atualizado + condição sobre Valor e parecer). Alternativa: encaminhamento manual pelo responsável da fase. Motivo: a decisão lê campos e um valor fixo. Estado inicial: ligada, exceto a regra de D1 que aprova abaixo de R$ 5.000,00, desligada até P2.
  Motivo da recusa: condição de campo (mostra e exige só na recusa). Alternativa: campo sempre visível.
  Lembrete: automação por prazo da fase (SLA). Alternativa: lembrete manual do gerente de compras. Estado inicial: ligada.
Restrições: sem IA (política do financeiro). Nenhum e-mail para fora da empresa.
Autorização: construir.
Premissas: abaixo de R$ 5.000,00, compras aprova sem gerente.
Pendências:
  P1. Quem recebe o lembrete de Análise nas férias do comprador. Bloqueia só o destinatário substituto do lembrete.
  P2. Confirmar se compras aprova abaixo de R$ 5.000,00 sem gerente. Bloqueia só a ativação da regra de aprovação abaixo desse valor.
Exemplos de aceitação:
  A1. Depois de P2 confirmada: Valor 4.999,99, parecer Aprovar -> Aprovado, sem passar pelo gerente.
  A2. Valor 5.000,00, parecer Aprovar -> Aprovação gerencial.
  A3. Parecer Recusar, motivo preenchido -> Recusado.
  A4. Parecer Falta documento -> Aguardando documento; depois do anexo, volta a Análise.
  A5. Gerente escolhe Recusar sem motivo -> o card não sai da fase.
```


---

## Example 2: vendor approval with parallel reviews

This example has parallel work with a join rule and a cancellation rule. It also has a rejection that ends the case, and an AI recommendation that the user did not confirm.

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
  Tax id: short text, Document check, the AI automation or the procurement analyst (see P3), not required.
  Certificate expiry date: date, Document check, the AI automation or the procurement analyst (see P3), not required.
Platform choices:
  D2: traditional automation when a card enters Reviews, with a spend condition. It sets Finance decision to Not required below 10,000.00.
    Alternative: the Finance reviewer sets the field. Start state: on.
  D3, D4: traditional automations on a decision field update, with conditions. Alternative: child cards in a separate review pipe.
    Reason: two fields in one phase hold both results, and the rules read fields. Start state: D4 on. D3 off until P2.
  Rejection reason: field condition. Alternative: a field that is always visible.
  Reminder at 3 days: automation on the phase time limit. Alternative: a manual follow-up. Start state: on.
  Deadline at 7 days: automation on the phase time limit. Alternative: the procurement analyst moves the case to the new owner. Start state: not created until P1.
  Read the tax id and the expiry date from the tax certificate: AI automation, recommended. Alternative: the analyst reads the certificate.
    Reason: the step reads a document on one event and writes two fields. Test: 20 sample certificates read correctly.
    Wrong output: a wrong date goes to the analyst. State: recommended, not confirmed (P3). The user did not confirm the specification with this recommendation. Start state: not created until P3.
  Email to the vendor on rejection: email template and an automation that sends it. This is an external effect, and Authorization does not permit it (P4). Start state: not created until P4.
Constraints: only the Legal reviewer approves legal terms. Bank data does not leave Pipefy.
Authorization: build ("build it"). External effects: not allowed.
Assumptions: Finance = Not required counts as a Finance result in the join.
Pending items:
  P1. Who owns the case at the 7-day deadline. Blocks only the deadline rule.
  P2. Does Not required count as a Finance result in the join? Blocks only D3 activation.
  P3. Confirm the AI automation that reads the tax certificate. Blocks only that AI automation. Until then, the procurement analyst fills Tax id and Certificate expiry date.
  P4. Permit the email to the vendor on rejection. Blocks only the email automation. The email template is a manual step in the Pipefy interface.
Acceptance examples:
  A1. After P2 is confirmed: spend 9,999.99, Legal Approved -> Vendor setup. Finance is Not required.
  A2. Spend 10,000.00, Legal Approved, Finance empty -> the case stays in Reviews.
  A3. Finance Rejected, Legal empty, rejection reason filled -> Rejected. The Legal review stops.
  A4. Legal Rejected while Finance is open -> Rejected. The Finance review stops.
  A5. Bank letter missing -> On hold. After the buyer attaches it -> Document check.
```


---

## Common structures

Use these structures as a start for a proposal. Change them to fit the decisions that the user gives.

- **Linear approval.** Submission, Under review, then Approved or Rejected. The requester fills the start form. The review phase holds the approver's decision field. A rule routes the case on that field.
- **Multi-stage work.** Intake, Triage, In progress, Testing, Done. Each phase has the fields of its owner. Rules move a card when a field test is true. A phase time limit sends a reminder.
- **Central intake with related pipes.** One intake pipe receives every request. A pipe relation connects it to the pipes that do the specialized work. A rule creates a connected card when a case needs that work. Use this structure only when each related pipe has its own cases and owners.
