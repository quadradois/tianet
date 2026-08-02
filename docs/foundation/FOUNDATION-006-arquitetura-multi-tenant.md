# FOUNDATION-006 — Arquitetura Multi-Tenant

**ID:** FOUNDATION-006

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Este documento estabelece a arquitetura oficial da camada Multi-Tenant da plataforma.

Seu objetivo é garantir o isolamento lógico entre organizações, preservando a independência do domínio financeiro.

A arquitetura Multi-Tenant pertence ao Platform Context e não ao Credit Context.

---

# 2. Contexto

A plataforma foi concebida para atender múltiplas organizações de forma simultânea.

Cada organização será representada por um Tenant.

Cada Tenant possuirá seus próprios usuários, configurações e Carteiras.

Todo processamento financeiro ocorrerá exclusivamente dentro de uma Carteira pertencente a um Tenant.

---

# 3. Conceitos Fundamentais

## Tenant

Organização que utiliza a plataforma.

Representa a fronteira de isolamento entre clientes.

---

## Usuário

Pessoa autorizada a acessar a plataforma em nome de um Tenant.

---

## Carteira

Unidade operacional onde ocorrem as operações de crédito.

Pertence exatamente a um Tenant.

Na versão 1, cada Tenant poderá possuir apenas uma Carteira.

Essa limitação é operacional e não arquitetural.

---

## Platform Context

Responsável por:

- Tenant;
- Usuários;
- Autenticação;
- Configurações;
- Permissões.

---

## Credit Context

Responsável por:

- Carteira;
- Devedor;
- Contrato de Crédito;
- Empréstimo;
- Parcela;
- Pagamento;
- Motor Financeiro.

---

# 4. Relação entre os Contextos

O Platform Context administra o acesso à plataforma.

O Credit Context administra as operações financeiras.

O único ponto de ligação entre ambos é a Carteira.

Todo acesso ao domínio financeiro deverá ocorrer dentro do contexto de uma Carteira pertencente a um Tenant.

---

# 5. Princípios

## Princípio 01

Todo recurso pertence exatamente a um Tenant.

---

## Princípio 02

Nenhum dado poderá ser compartilhado entre Tenants.

---

## Princípio 03

O isolamento entre Tenants é obrigatório.

---

## Princípio 04

Um Tenant poderá possuir uma ou mais Carteiras.

Na versão 1, apenas uma Carteira poderá ser criada.

---

## Princípio 05

O domínio financeiro permanece independente do gerenciamento de usuários e autenticação.

---

# 6. Critérios de Aprovação

Este documento será considerado aprovado quando:

- o conceito de Tenant estiver formalizado;
- os limites entre Platform Context e Credit Context estiverem definidos;
- as responsabilidades de cada contexto estiverem claramente estabelecidas.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Arquitetura Multi-Tenant. |
