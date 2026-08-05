# DOMAIN-005 — Entity Parcela

**ID:** DOMAIN-005

**Versão:** 1.0.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira

---

# 1. Definição

A Parcela representa uma obrigação financeira prevista em um Contrato de Crédito na modalidade Prazo Fixo.

Ela define o compromisso financeiro esperado para uma determinada data de vencimento.

A Parcela não representa um pagamento.

Ela representa aquilo que deverá ser pago.

O pagamento é um evento independente que poderá liquidar total ou parcialmente uma Parcela.

---

# 2. Identidade

Uma Parcela possui identidade única dentro de um Empréstimo.

Após sua geração sua identidade permanece imutável.

---

# 3. Responsabilidades

A Parcela é responsável por:

- representar uma obrigação financeira prevista;
- manter sua data de vencimento;
- manter seu valor previsto;
- indicar seu estado atual;
- permitir sua liquidação total ou parcial;
- servir de referência para cobrança;
- servir de referência para cálculo de inadimplência.

A Parcela não recebe pagamentos.

A Parcela não calcula juros.

A Parcela não calcula amortizações.

Essas responsabilidades pertencem ao Motor Financeiro.

---

# 4. Ciclo de Vida

## Prevista

A Parcela foi gerada e aguarda vencimento.

---

## Vencida

A data de vencimento foi alcançada e a obrigação permanece pendente.

---

## Parcialmente Liquidada

Parte do valor previsto foi liquidado.

Ainda existe saldo pendente.

---

## Liquidada

Toda a obrigação financeira foi satisfeita.

---

## Cancelada

A Parcela foi cancelada em razão de renegociação ou cancelamento da operação.

Seu histórico permanece preservado.

---

# 5. Regras

## RN-001

Toda Parcela pertence exatamente a um Empréstimo.

---

## RN-002

Parcela somente existe para Contratos na modalidade Prazo Fixo.

---

## RN-003

Toda Parcela deve possuir uma data de vencimento.

---

## RN-004

Toda Parcela deve possuir um valor previsto maior que zero.

---

## RN-005

Uma Parcela poderá ser liquidada por um ou mais Pagamentos.

---

## RN-006

Uma Parcela totalmente liquidada não poderá voltar ao estado pendente.

---

## RN-007

Uma Parcela cancelada preserva seu histórico.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Empréstimo (1)

↓

Parcela (0..N)

---

Parcela (1)

↓

Pagamento (0..N)

---

# 7. Invariantes

## INV-001

Toda Parcela pertence exatamente a um Empréstimo.

---

## INV-002

Toda Parcela possui exatamente uma data de vencimento.

---

## INV-003

O valor previsto da Parcela nunca poderá ser menor ou igual a zero.

---

## INV-004

Uma Parcela liquidada não poderá possuir saldo pendente.

---

## INV-005

Toda Parcela representa uma obrigação financeira prevista.

---

# 8. Glossário

## Parcela

Obrigação financeira prevista para determinada data de vencimento.

---

## Liquidação

Processo pelo qual um ou mais Pagamentos satisfazem total ou parcialmente uma Parcela.

---

## Valor Previsto

Valor originalmente esperado para liquidação da Parcela.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Entity Parcela. |
