# FOUNDATION-002 — Modelo de Domínio e Linguagem Ubíqua

**ID:** FOUNDATION-002

**Versão:** 1.1.0

**Status:** Aprovado

---

# 1. Objetivo

Este documento estabelece a Linguagem Ubíqua oficial da plataforma de Operações de Crédito.

Todo termo utilizado no produto deverá possuir exatamente um significado dentro do domínio.

Nenhum conceito poderá possuir definições conflitantes.

Toda nova funcionalidade deverá utilizar exclusivamente os termos definidos neste documento.

---

# 2. Contexto

A plataforma é organizada segundo princípios de Domain-Driven Design (DDD).

A comunicação entre Produto, Negócio e Engenharia deverá utilizar uma linguagem única, compartilhada e consistente.

Este documento representa a principal referência terminológica do projeto.

---

# 3. Definições Oficiais

## Carteira

Conjunto de operações de crédito pertencentes a um Credor.

Representa o Aggregate Root do domínio.

---

## Credor

Pessoa responsável por conceder crédito aos seus Devedores.

É o proprietário da Carteira.

---

## Devedor

Pessoa responsável pelas obrigações financeiras decorrentes de uma operação de crédito.

Todo Devedor pertence exatamente a uma Carteira.

---

## Contrato de Crédito

Acordo formal celebrado entre Credor e Devedor.

Define todas as condições comerciais e financeiras da operação.

Não executa cálculos.

---

## Empréstimo

Representa o estado atual da operação de crédito.

Reflete o resultado consolidado do último processamento realizado pelo Motor Financeiro.

---

## Parcela

Obrigação financeira prevista em operações na modalidade Prazo Fixo.

Não representa um pagamento.

Representa aquilo que deverá ser pago.

---

## Pagamento

Registro financeiro de um valor recebido pelo Credor.

Representa um fato financeiro ocorrido.

---

## Motor Financeiro

Domain Service responsável por executar todas as regras financeiras da plataforma.

É a única autoridade para cálculos financeiros.

---

## Dinheiro

Value Object que representa um valor monetário.

---

## Periodicidade

Value Object que representa a recorrência das obrigações financeiras.

---

## Modalidade de Empréstimo

Value Object que define como a operação será administrada.

Na versão 1:

- Livre
- Prazo Fixo

---

## Estado Atual

Representação consolidada da situação financeira da operação após o último processamento.

---

## Histórico da Operação

Conjunto de todos os fatos financeiros ocorridos durante a vida da operação.

É composto por pagamentos, eventos e memórias de cálculo.

---

## Memória de Cálculo

Registro detalhado produzido pelo Motor Financeiro contendo todas as operações matemáticas realizadas durante um processamento financeiro.

Representa a base de auditoria da plataforma.

---

## Juros

Remuneração financeira calculada conforme as regras do Contrato de Crédito.

---

## Amortização

Redução do saldo principal da operação.

---

## Quitação

Estado em que todas as obrigações financeiras da operação foram integralmente cumpridas.

---

## Inadimplência

Estado em que existem obrigações financeiras vencidas e não liquidadas.

---

## Tenant

Organização que utiliza a plataforma.

Representa a fronteira de isolamento entre clientes.

É o Aggregate Root do Platform Context.

---

## Usuário

Pessoa autorizada a acessar a plataforma em nome de um Tenant.

---

## Perfil de Acesso

Conjunto de permissões concedidas ao Usuário.

---

## Permissão

Autorização concedida a um Usuário para executar operações na plataforma conforme seu perfil de acesso.

---

## Autenticação

Processo de verificação da identidade de um Usuário para acesso à plataforma.

---

## Configuração

Parâmetro específico de um Tenant que define o comportamento da plataforma para sua organização.

---

# 4. Princípios da Linguagem Ubíqua

## Princípio 01

Um conceito possui exatamente um significado.

---

## Princípio 02

Um mesmo termo nunca poderá representar conceitos diferentes.

---

## Princípio 03

Toda comunicação entre Produto, Negócio e Engenharia deverá utilizar esta terminologia.

---

## Princípio 04

Toda evolução do domínio deverá atualizar este documento antes da implementação.

---

## Princípio 05

O Domain é a referência oficial para o significado de cada conceito.

---

# 5. Critérios de Aprovação

Este documento será considerado aprovado quando:

- todos os conceitos fundamentais estiverem definidos;
- não existirem ambiguidades terminológicas;
- Foundation e Domain estiverem consistentes;
- a equipe adotar esta linguagem como referência oficial.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Modelo de Domínio e Linguagem Ubíqua. |
| 1.1.0 | 01/08/2026 | Incorporação oficial dos conceitos do Platform Context (Tenant, Usuário, Perfil de Acesso, Permissão, Autenticação e Configuração), mantendo íntegros os conceitos do Credit Context. Consistente com FOUNDATION-006, DOMAIN-017, DOMAIN-018 e DOMAIN-019. |
