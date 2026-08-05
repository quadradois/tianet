# DOMAIN-008 — Value Object Periodicidade

**ID:** DOMAIN-008

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Definição

Periodicidade representa o intervalo utilizado para determinar a recorrência das obrigações financeiras de uma operação de crédito.

É um Value Object imutável.

Não possui identidade própria.

Seu valor é definido exclusivamente pela periodicidade escolhida para a operação.

---

# 2. Imutabilidade

Após criada, uma Periodicidade nunca poderá ser alterada.

Toda alteração na periodicidade deverá resultar na criação de um novo Value Object.

---

# 3. Regras de Validação

## RN-001

Toda operação de crédito deverá possuir exatamente uma Periodicidade.

---

## RN-002

A Periodicidade define apenas a recorrência das obrigações financeiras.

Ela não define datas específicas de vencimento.

---

## RN-003

As datas efetivas de vencimento serão determinadas em conjunto com o Calendário Financeiro e as regras do Contrato de Crédito.

---

## RN-004

A Periodicidade deverá pertencer ao conjunto de valores suportados pela plataforma.

Na versão 1 são suportadas:

- Diária
- Semanal
- Quinzenal
- Mensal

---

## RN-005

A Periodicidade não executa cálculos financeiros.

Ela apenas representa a recorrência utilizada pela operação.

---

# 4. Exemplos

Mensal

Quinzenal

Semanal

Diária

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do VO Periodicidade. |
