# DOMAIN-003 — Entity Contrato de Crédito

**ID:** DOMAIN-003

**Versão:** 1.1.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira

---

# 1. Definição

O Contrato de Crédito representa o acordo formal estabelecido entre o Credor e o Devedor.

Nele são definidas todas as condições comerciais e financeiras que regerão a operação durante todo o seu ciclo de vida.

O Contrato não controla pagamentos, saldos ou amortizações.

Seu papel é definir as regras que serão executadas pelo Empréstimo através do Motor Financeiro.

---

# 2. Identidade

Um Contrato de Crédito possui identidade única dentro da Carteira.

Após sua formalização, sua identidade permanece imutável.

As condições originalmente pactuadas permanecem registradas para fins históricos, mesmo quando houver renegociação.

---

# 3. Responsabilidades

O Contrato de Crédito é responsável por:

- definir o valor originalmente contratado;
- definir a taxa de juros;
- definir a modalidade da operação;
- definir a periodicidade financeira;
- definir a data da contratação;
- definir o dia de acerto;
- registrar as condições negociadas entre as partes;
- servir como referência para a criação do Empréstimo.

O Contrato não realiza cálculos financeiros.

O Contrato não recebe pagamentos.

O Contrato não controla saldo devedor.

---

# 4. Ciclo de Vida

## Proposta

As condições comerciais estão sendo negociadas.

---

## Formalizado

As partes concordaram com as condições.

O contrato está apto para originar um Empréstimo.

---

## Executado

O crédito foi liberado e originou um Empréstimo.

---

## Encerrado

O contrato encontra-se encerrado por conclusão ou substituição em decorrência de renegociação.

Seu histórico permanece preservado.

---

# 5. Regras

## RN-001

Todo Contrato pertence exatamente a uma Carteira.

---

## RN-002

Todo Contrato pertence exatamente a um Devedor.

---

## RN-003

Todo Contrato deve possuir um valor contratado maior que zero.

---

## RN-004

Todo Contrato deve possuir uma taxa de juros válida.

---

## RN-005

Todo Contrato deve possuir uma Modalidade de Empréstimo.

---

## RN-006

Todo Contrato deve possuir uma Periodicidade.

---

## RN-007

Todo Contrato deve definir o dia de acerto do Empréstimo.

---

## RN-008

Um Contrato somente poderá originar um Empréstimo após sua formalização.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Devedor (1)

↓

Contrato de Crédito (0..N)

---

Contrato de Crédito (1)

↓

Empréstimo (0..1)

Na versão 1 do produto, um Contrato origina exatamente um Empréstimo.

Caso exista renegociação, um novo Contrato deverá ser criado, preservando o histórico do anterior.

---

# 7. Invariantes

## INV-001

Todo Contrato pertence exatamente a uma Carteira.

---

## INV-002

Todo Contrato pertence exatamente a um Devedor.

---

## INV-003

As condições originalmente contratadas nunca são alteradas.

---

## INV-004

Todo Empréstimo deve possuir exatamente um Contrato de origem.

---

# 8. Glossário

## Contrato de Crédito

Documento que estabelece as condições comerciais e financeiras da operação.

---

## Formalização

Momento em que as condições deixam de ser proposta e passam a produzir efeitos jurídicos e operacionais.

---

## Originação

Processo de criação de um Empréstimo a partir de um Contrato formalizado.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.1.0 | 23/08/2026 | Primeiro vencimento e dia de vencimento substituidos pelo dia de acerto do emprestimo livre (DR-004, IMP-337). |
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Contrato de Crédito. |
