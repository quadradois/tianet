# FOUNDATION-006 — Arquitetura Multi-Tenant

**ID:** FOUNDATION-006

**Versão:** 1.1.0

**Status:** Aprovado

---

# 1. Objetivo

Este documento estabelece a arquitetura oficial da camada Multi-Tenant da plataforma.

Seu objetivo é garantir o isolamento lógico entre organizações, preservando a independência do domínio financeiro.

A arquitetura Multi-Tenant pertence ao Platform Context e não ao Credit Context.

---

# 2. Contexto

A plataforma foi concebida para atender múltiplos Credores de forma simultânea.

Cada Credor será representado por um Tenant.

Cada Tenant possuirá seus próprios usuários, configurações e Carteiras.

Todo processamento financeiro ocorrerá exclusivamente dentro de uma Carteira pertencente a um Tenant.

---

# 3. Conceitos Fundamentais

## Tenant

Credor que utiliza a plataforma — na FOUNDATION-001, a **pessoa** que empresta o
próprio dinheiro e administra pessoalmente suas operações.

Representa a fronteira de isolamento entre Credores.

> **Por que o Tenant continua existindo se o Credor é uma pessoa.** Tenant é
> unidade de **isolamento**, não de personalidade jurídica. Ele existe para que
> os dados de um Credor jamais alcancem outro, independentemente de o titular
> ser pessoa física ou jurídica. Um Credor individual precisa dessa fronteira
> exatamente como uma organização precisaria.
>
> **Por que o campo `identificador_institucional` sobrevive.** O nome é herança
> da cerimônia institucional que a FOUNDATION-001 v2.0.0 invalidou, mas o
> **campo** continua necessário: todo Tenant precisa de um identificador
> estável e único, e um Credor individual também tem um. Renomeá-lo seria
> mudança **não aditiva** de contrato público atingindo 72 pontos em `src/` e 9
> no frontend, além de snapshot, cliente tipado, matriz e cadeia do PLAN-026 —
> custo alto para ganho puramente estético. **Decisão registrada em 2026-08-23
> pelo IMP-338: o campo permanece com o nome atual.** Quem estranhar o nome no
> futuro deve ler este parágrafo em vez de reabrir a questão.

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
| 1.1.0 | 23/08/2026 | Tenant deixa de ser definido como organizacao e passa a representar o Credor da FOUNDATION-001. Registrada a razao de o Tenant existir para um credor individual e a decisao de preservar o nome do campo `identificador_institucional` (IMP-338). |
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Arquitetura Multi-Tenant. |
