# DOMAIN-007 — Value Object Dinheiro

**ID:** DOMAIN-007

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Definição

Dinheiro representa um valor monetário utilizado nas operações financeiras da plataforma.

É um Value Object imutável.

Não possui identidade própria.

Seu valor é definido exclusivamente por sua composição.

---

# 2. Imutabilidade

Após criado, um objeto Dinheiro nunca poderá ser alterado.

Toda operação financeira deverá produzir um novo Value Object.

---

# 3. Regras de Validação

## RN-001

Todo valor monetário deverá possuir exatamente duas casas decimais.

---

## RN-002

Não são permitidos valores indefinidos.

---

## RN-003

Operações matemáticas deverão preservar a precisão financeira.

---

## RN-004

Comparações entre valores monetários deverão considerar a precisão decimal.

---

## RN-005

O Value Object não executa regras de negócio.

Ele apenas representa um valor monetário.

---

# 4. Exemplos

R$ 1.000,00

R$ 35,40

R$ 0,00

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do VO Dinheiro. |
