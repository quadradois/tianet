# DOMAIN-009 — Value Object Modalidade de Empréstimo

**ID:** DOMAIN-009

**Versão:** 2.0.0

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

Desde a DR-004, a plataforma suporta **uma única modalidade**:

- Livre

A modalidade **Prazo Fixo foi revogada** junto com o plano de parcelas. Ver
DOMAIN-005, mantido apenas como registro histórico.

---

## RN-003

Na modalidade Livre não existe cronograma de pagamentos gerado no lançamento.

O empréstimo tem um **dia de acerto** combinado. Em cada acerto o devedor deve,
no mínimo, o juro do período; amortizar o principal é voluntário. Os juros
correm sobre o saldo devedor por trecho, e atraso não gera multa nem encargo —
são apenas mais dias do mesmo juro.

Os pagamentos são processados pelo Motor Financeiro, que liquida primeiro os
juros, depois os encargos, e por último amortiza o principal.

---

## RN-005

A Modalidade de Empréstimo não executa cálculos financeiros.

Ela apenas define o comportamento esperado da operação de crédito.

---

# 4. Exemplos

## Livre

Operação sem cronograma de pagamentos definido no lançamento.

R$ 10.000,00 a 5% ao mês, com dia de acerto no dia 10. No acerto de cada mês o
devedor deve no mínimo R$ 500,00 de juros. Se pagar apenas isso, o saldo segue
em R$ 10.000,00 e o próximo acerto pede os mesmos R$ 500,00. Se amortizar
R$ 4.500,00 junto, o saldo cai para R$ 5.500,00 e o acerto seguinte pede
R$ 275,00.

Nove dias depois do acerto sem pagamento, o devido são os mesmos juros
acumulados por nove dias a mais, com encargos em zero.

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 2.0.0 | 23/08/2026 | Modalidade Prazo Fixo revogada pela DR-004; resta apenas Livre, descrita com o acerto mensal e o exemplo numérico correspondente (IMP-337). |
| 1.0.0 | 01/08/2026 | Primeira versão oficial do VO Modalidade de Empréstimo. |
