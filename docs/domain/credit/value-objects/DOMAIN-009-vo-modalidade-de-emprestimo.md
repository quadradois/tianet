# DOMAIN-009 — Value Object Modalidade de Empréstimo

**ID:** DOMAIN-009

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Definição

A Modalidade de Empréstimo representa a forma como uma operação de crédito será administrada durante sua execução financeira.

É um Value Object imutável.

Não possui identidade própria.

Seu valor é definido exclusivamente pela modalidade escolhida no Contrato de Crédito.

---

# 2. Imutabilidade

Após criada, uma Modalidade de Empréstimo nunca poderá ser alterada.

Caso a modalidade precise ser modificada, um novo Contrato de Crédito deverá ser formalizado.

---

# 3. Regras de Validação

## RN-001

Toda operação de crédito deverá possuir exatamente uma Modalidade de Empréstimo.

---

## RN-002

Na versão 1 da plataforma são suportadas duas modalidades:

- Livre
- Prazo Fixo

---

## RN-003

Na modalidade Livre não existem Parcelas previamente geradas.

Os pagamentos são processados conforme as regras do Motor Financeiro, respeitando a prioridade de liquidação dos juros e posterior amortização do principal.

---

## RN-004

Na modalidade Prazo Fixo o sistema deverá gerar as Parcelas previstas no Contrato de Crédito.

Os pagamentos poderão liquidar uma ou mais Parcelas, total ou parcialmente.

---

## RN-005

A Modalidade de Empréstimo não executa cálculos financeiros.

Ela apenas define o comportamento esperado da operação de crédito.

---

# 4. Exemplos

## Livre

Operação sem cronograma fixo de Parcelas.

Os pagamentos ocorrem conforme negociação entre Credor e Devedor.

---

## Prazo Fixo

Operação com cronograma de Parcelas previamente definido.

Cada Parcela possui data de vencimento e valor previsto.

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do VO Modalidade de Empréstimo. |
