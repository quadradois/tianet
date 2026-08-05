# DOMAIN-017 — Aggregate Tenant

**ID:** DOMAIN-017

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

O Tenant representa o Aggregate Root do Platform Context.

Seu objetivo é estabelecer a fronteira de isolamento entre organizações que utilizam a plataforma.

Todo recurso da plataforma pertence exatamente a um Tenant.

Nenhum recurso poderá ser compartilhado entre Tenants.

---

# 2. Responsabilidades

O Tenant é responsável por:

- manter a identidade da organização;
- manter seus Usuários;
- manter suas Configurações;
- manter suas Carteiras;
- garantir o isolamento dos dados;
- estabelecer a fronteira transacional do Platform Context.

O Tenant não executa regras financeiras.

Essas responsabilidades pertencem exclusivamente ao Credit Context.

---

# 3. Invariantes

## INV-001

Todo Usuário pertence exatamente a um Tenant.

---

## INV-002

Toda Carteira pertence exatamente a um Tenant.

---

## INV-003

Nenhum Usuário poderá pertencer simultaneamente a dois Tenants.

---

## INV-004

Nenhuma Carteira poderá pertencer simultaneamente a dois Tenants.

---

## INV-005

Um Tenant poderá possuir uma ou mais Carteiras.

Na versão 1 da plataforma, será permitida apenas uma Carteira por Tenant.

Essa limitação é operacional e não altera o modelo de domínio.

---

# 4. Entidades Filhas

O Tenant é composto pelas seguintes entidades:

- Usuário
- Carteira

---

# 5. Value Objects

O Tenant poderá utilizar Value Objects próprios do Platform Context.

Nenhum Value Object do Credit Context pertence ao Aggregate Tenant.

---

# 6. Domain Services

O Tenant poderá utilizar serviços próprios do Platform Context.

O Motor Financeiro não pertence ao Aggregate Tenant.

---

# 7. Domain Events

Exemplos de eventos produzidos pelo Tenant:

- Tenant Criado
- Usuário Convidado
- Usuário Removido
- Carteira Criada

---

# 8. Relacionamentos

O Tenant representa a fronteira de isolamento da plataforma.

Sua estrutura conceitual é:

Tenant
│
├── Usuários
│
└── Carteiras
      │
      ├── Devedores
      ├── Contratos de Crédito
      ├── Empréstimos
      ├── Parcelas
      └── Pagamentos

Todo acesso ao Credit Context ocorre através de uma Carteira pertencente ao Tenant.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Aggregate Tenant. |
