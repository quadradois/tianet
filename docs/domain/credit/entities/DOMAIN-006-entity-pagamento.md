# DOMAIN-006 — Entity Pagamento

**ID:** DOMAIN-006

**Versão:** 1.0.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira

---

# 1. Definição

O Pagamento representa o registro financeiro de um valor recebido pelo Credor para liquidação total ou parcial de uma operação de crédito.

O Pagamento nunca executa cálculos financeiros.

Ele representa o resultado do processamento realizado pelo Motor Financeiro.

---

# 2. Identidade

Um Pagamento possui identidade única dentro de um Empréstimo.

Após seu registro sua identidade permanece imutável.

---

# 3. Responsabilidades

O Pagamento é responsável por:

- registrar a data do recebimento;
- registrar o valor recebido;
- registrar a distribuição do valor entre juros e amortização;
- registrar quais Parcelas foram liquidadas, quando aplicável;
- registrar o resultado do processamento financeiro;
- compor o histórico financeiro da operação.

O Pagamento não calcula juros.

O Pagamento não calcula amortizações.

O Pagamento não altera diretamente o Empréstimo.

Essas responsabilidades pertencem exclusivamente ao Motor Financeiro.

---

# 4. Ciclo de Vida

## Recebido

O valor foi recebido pelo Credor.

---

## Processado

O Motor Financeiro distribuiu o pagamento conforme as regras da operação.

---

## Confirmado

O estado do Empréstimo foi atualizado.

O Pagamento passa a compor definitivamente o histórico da operação.

---

## Estornado

O registro permanece preservado para auditoria.

Seu efeito financeiro foi revertido conforme as regras da operação.

---

# 5. Regras

## RN-001

Todo Pagamento pertence exatamente a um Empréstimo.

---

## RN-002

Todo Pagamento possui um valor recebido maior que zero.

---

## RN-003

Todo Pagamento deverá ser processado pelo Motor Financeiro.

---

## RN-004

Todo Pagamento deverá registrar quanto foi destinado aos juros.

---

## RN-005

Todo Pagamento deverá registrar quanto foi destinado à amortização.

---

## RN-006

Quando existirem Parcelas, o Pagamento deverá registrar quais Parcelas foram liquidadas total ou parcialmente.

---

## RN-007

Todo Pagamento deverá atualizar o estado atual do Empréstimo através do Motor Financeiro.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Empréstimo (1)

↓

Pagamento (0..N)

---

Pagamento (0..N)

↓

Parcela

(apenas quando a modalidade for Prazo Fixo)

---

Pagamento

↓

Motor Financeiro

↓

Atualiza

↓

Empréstimo

---

# 7. Invariantes

## INV-001

Todo Pagamento pertence exatamente a um Empréstimo.

---

## INV-002

O valor recebido deve ser maior que zero.

---

## INV-003

A soma dos valores destinados aos juros e à amortização deverá ser exatamente igual ao valor recebido.

---

## INV-004

Todo Pagamento confirmado compõe permanentemente o histórico da operação.

---

## INV-005

Nenhum Pagamento poderá alterar diretamente o Empréstimo sem processamento do Motor Financeiro.

---

# 8. Glossário

## Pagamento

Registro financeiro de um valor recebido para liquidação total ou parcial de uma operação.

---

## Processamento Financeiro

Execução realizada pelo Motor Financeiro para distribuir corretamente o valor recebido.

---

## Estorno

Processo controlado de reversão dos efeitos financeiros de um Pagamento.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Entity Pagamento. |
