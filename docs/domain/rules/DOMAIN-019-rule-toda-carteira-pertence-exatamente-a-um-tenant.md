# DOMAIN-019 — Business Rule Toda Carteira pertence exatamente a um Tenant

**ID:** DOMAIN-019

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Identificador

BR-004

---

# 2. Descrição

Toda Carteira deverá pertencer exatamente a um Tenant.

Não é permitida a existência de Carteiras sem Tenant, nem o compartilhamento de uma mesma Carteira entre diferentes Tenants.

---

# 3. Motivação

O Tenant representa a fronteira de isolamento da plataforma.

A Carteira representa a fronteira operacional do domínio financeiro.

A associação obrigatória entre Tenant e Carteira garante o isolamento dos dados, a segurança das operações e a integridade do modelo de domínio.

---

# 4. Regra

Toda Carteira deverá estar vinculada a exatamente um Tenant desde sua criação.

Essa associação permanecerá durante todo o ciclo de vida da Carteira.

Na versão 1 da plataforma, cada Tenant poderá criar apenas uma Carteira.

Essa limitação é operacional e poderá ser ampliada em versões futuras sem alteração do modelo de domínio.

---

# 5. Exceções

Não existem exceções na versão 1 da plataforma.

---

# 6. Exemplos

## Válido

Tenant "Financeira ABC"

↓

Carteira Principal

---

## Inválido

Carteira sem Tenant.

---

Carteira pertencendo simultaneamente aos Tenants "Financeira ABC" e "Financeira XPTO".

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da regra de associação obrigatória entre Tenant e Carteira. |
