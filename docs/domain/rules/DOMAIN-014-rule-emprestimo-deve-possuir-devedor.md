# DOMAIN-014 — Business Rule Empréstimo deve possuir Devedor

**ID:** DOMAIN-014

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Identificador

BR-001

---

# 2. Descrição

Toda operação de crédito deverá estar vinculada exatamente a um Devedor.

Não é permitida a existência de Empréstimos sem um Devedor identificado.

---

# 3. Motivação

O Devedor é a parte responsável pelas obrigações financeiras da operação.

A ausência dessa informação inviabiliza o controle financeiro, a cobrança, a comunicação e a rastreabilidade da operação.

---

# 4. Regra

Todo Empréstimo deverá possuir exatamente um Devedor associado desde sua criação.

Essa associação permanecerá durante todo o ciclo de vida da operação.

---

# 5. Exceções

Não existem exceções na versão 1 da plataforma.

---

# 6. Exemplos

## Válido

João possui um Empréstimo ativo.

---

## Inválido

Empréstimo criado sem Devedor associado.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da regra de associação obrigatória entre Empréstimo e Devedor. |
