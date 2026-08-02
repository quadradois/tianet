# HANDOFF-VIGENTE — Estado Atual do Projeto

> Este documento registra o estado do desenvolvimento entre sessões de trabalho, permitindo que
> qualquer membro da equipe retome o projeto rapidamente.

---

## Objetivo

> Registrar o estado do projeto entre sessões de trabalho. Seções sem informação ativa permanecem
> vazias até que exista conteúdo a registrar.

---

## Estado Atual

A **fase de Domain Modeling da camada Domain está concluída** — todos os documentos do domínio (DOMAIN-001 a DOMAIN-016) materializados e aprovados (v1.0.0).

O projeto inicia a introdução da **camada Multi-Tenant Nível 1**: estrutura de FOUNDATION-006, DOMAIN-017, DOMAIN-018 e DOMAIN-019 criada, aguardando fontes oficiais.

---

## Foundation

- **FOUNDATION-001** — Visão do Produto: criado e aprovado pelo Product.
- **FOUNDATION-002** — Modelo de Domínio e Linguagem Ubíqua: materializado e aprovado (v1.0.0) — define a Linguagem Ubíqua oficial (17 termos) e os Princípios 01–05.
- **FOUNDATION-003** — Mapa do Domínio: materializado e aprovado (v1.0.0).
- **FOUNDATION-004** — Core Domain: materializado e aprovado (v1.0.0).
- **FOUNDATION-005** — Inventário do Domínio: materializado e aprovado (v1.0.0).
- **FOUNDATION-006** — Arquitetura Multi-Tenant: estrutura criada (placeholder, v0.1.0), aguardando fonte oficial.

---

## Domain

Camada Domain totalmente materializada (DOMAIN-001 a DOMAIN-016, v1.0.0, Aprovado):

- **Aggregate:** DOMAIN-001 Carteira (Aggregate Root; diagrama Mermaid).
- **Entities:** DOMAIN-002 Pessoa, DOMAIN-003 Contrato de Crédito, DOMAIN-004 Empréstimo (estado atual da operação), DOMAIN-005 Parcela (Prazo Fixo), DOMAIN-006 Pagamento.
- **Value Objects:** DOMAIN-007 Dinheiro, DOMAIN-008 Periodicidade, DOMAIN-009 Modalidade de Empréstimo (Livre/Prazo Fixo).
- **Domain Service:** DOMAIN-010 Motor Financeiro (única autoridade para cálculos).
- **Domain Events:** DOMAIN-011 Empréstimo Criado, DOMAIN-012 Pagamento Registrado, DOMAIN-013 Empréstimo Quitado.
- **Business Rules:** DOMAIN-014 (BR-001, Empréstimo deve possuir Devedor), DOMAIN-015 (BR-002, Pagamento não pode ser negativo), DOMAIN-016 (BR-003, Quitado não recebe Pagamentos).

**Camada Multi-Tenant (Nível 1) — estruturas criadas (placeholders, v0.1.0):**

- **DOMAIN-017** — Aggregate Tenant (placeholder).
- **DOMAIN-018** — Entity Usuário (placeholder).
- **DOMAIN-019** — Business Rule Toda Carteira pertence exatamente a um Tenant (placeholder).

---

## Product

> Nenhum documento de Product criado até o momento. Próxima camada a ser trabalhada após o domínio.

---

## Architecture

> Nenhum documento de Architecture criado até o momento.

---

## Tasks em andamento

Nenhuma task em andamento.

---

## Tasks concluídas

| ID | Descrição | Conclusão | Commit/Referência |
|----|-----------|-----------|-------------------|
| TASK-001 | Criar estrutura inicial de documentação | 2026-08-01 | 5354fd8 |
| TASK-002 | Criar templates oficiais de documentação | 2026-08-01 | a576eb7 |
| TASK-003 | Refatorar templates para a metodologia do projeto | 2026-08-01 | c39f93b |
| TASK-004 | Criar estrutura de handoff do projeto | 2026-08-01 | 8435c73 |
| TASK-005 | Alinhar template Foundation ao padrão de IDs | 2026-08-01 | 5df522d |
| TASK-006 | Criar documento FOUNDATION-002 (estrutura) | 2026-08-01 | 685e9e8 |
| TASK-007 | Criar estrutura da camada Domain | 2026-08-01 | 855f89c |
| TASK-008 | Criar templates da camada Domain | 2026-08-01 | 9ec4270 |
| TASK-009 | Criar documento DOMAIN-001 (Aggregate Carteira) | 2026-08-01 | 2290b1c |
| TASK-010 | Criar template para diagramas Mermaid | 2026-08-01 | 323b3fd |
| TASK-011 | Configurar validação automática da documentação | 2026-08-01 | fdf9c29 |
| TASK-012 | Integrar validação da documentação ao Git (pre-commit) | 2026-08-01 | 3b3f87d |
| TASK-013 | Criar documento DOMAIN-002 (Entity Pessoa) | 2026-08-01 | 140fb02 |
| TASK-014 | Criar documento DOMAIN-003 (Entity Empréstimo) | 2026-08-01 | 59432fb |
| TASK-015 | Criar documentos restantes da camada Domain | 2026-08-01 | 3826692 |
| TASK-016 | Preencher handoff (estado do projeto) | 2026-08-01 | 3093d5e |
| TASK-017 | Adicionar diagrama Mermaid ao DOMAIN-001 | 2026-08-01 | 7c1526c |
| TASK-018 | Revisão de consistência da documentação | 2026-08-01 | d805875 |
| TASK-019 | Materializar DOMAIN-002 (Entity Pessoa) | 2026-08-01 | 3a9040f |
| TASK-020 | Criar FOUNDATION-003 e FOUNDATION-004 (estrutura) | 2026-08-01 | 3d1f023 |
| TASK-021 | Criar FOUNDATION-005 (estrutura) | 2026-08-01 | 8f4bb8c |
| TASK-022 | Reorganizar camada Domain (Contrato de Crédito antecede Empréstimo; renumeração em cascata 004–016) | 2026-08-01 | a441286 |
| TASK-023 | Preparar DOMAIN-001 para receber Fonte Oficial | 2026-08-01 | — |
| TASK-025 | Preparar FOUNDATION-002 para receber Fonte Oficial | 2026-08-01 | — |
| TASK-027 | Introduzir camada Multi-Tenant Nível 1 (FOUNDATION-006, DOMAIN-017, DOMAIN-018, DOMAIN-019) | 2026-08-01 | (este commit) |

### Materializações (fonte oficial v1.0.0)

| ID | Descrição | Conclusão | Commit/Referência |
|----|-----------|-----------|-------------------|
| — | Materializar DOMAIN-003 (Entity Empréstimo — posteriormente renumerado para DOMAIN-004) | 2026-08-01 | f0ff3d0 |
| — | Materializar FOUNDATION-003 (Mapa do Domínio) | 2026-08-01 | e224250 |
| — | Materializar FOUNDATION-004 (Core Domain) | 2026-08-01 | 68cdfc6 |
| — | Materializar FOUNDATION-005 (Inventário do Domínio) | 2026-08-01 | 7699091 |
| — | Materializar DOMAIN-001 (Aggregate Carteira) | 2026-08-01 | 04a55f7 |
| — | Materializar DOMAIN-003 (Contrato de Crédito) | 2026-08-01 | ceef502 |
| — | Materializar DOMAIN-004 (Empréstimo — estado atual da operação) | 2026-08-01 | 849a5a0 |
| — | Materializar DOMAIN-005 (Parcela) | 2026-08-01 | 7d1e059 |
| — | Materializar DOMAIN-006 (Pagamento) | 2026-08-01 | 9b5baa0 |
| — | Materializar DOMAIN-007 (Dinheiro) | 2026-08-01 | 2d18a13 |
| — | Materializar DOMAIN-008 (Periodicidade) | 2026-08-01 | 515889f |
| — | Materializar DOMAIN-009 (Modalidade de Empréstimo — substitui placeholder Status Empréstimo) | 2026-08-01 | 3293f33 |
| — | Materializar DOMAIN-010 (Motor Financeiro — substitui placeholder Gerenciamento de Empréstimos) | 2026-08-01 | 1a6d62c |
| — | Materializar DOMAIN-011 (Empréstimo Criado) | 2026-08-01 | 287782b |
| — | Materializar DOMAIN-012 (Pagamento Registrado) | 2026-08-01 | f45df03 |
| — | Materializar DOMAIN-013 (Empréstimo Quitado) | 2026-08-01 | 1264e68 |
| — | Materializar DOMAIN-014 (BR-001 — Empréstimo deve possuir Devedor) | 2026-08-01 | 2a2d681 |
| — | Materializar DOMAIN-015 (BR-002 — Pagamento não pode ser negativo) | 2026-08-01 | abe128a |
| — | Materializar DOMAIN-016 (BR-003 — Quitado não recebe Pagamentos) | 2026-08-01 | f8cbd7e |
| — | Materializar FOUNDATION-002 (Modelo de Domínio e Linguagem Ubíqua) | 2026-08-01 | 958a67a |

---

## Decisões aprovadas

| ID | Decisão | Data | Referência |
|----|---------|------|------------|
| PD-011 | O sistema armazenará apenas fatos financeiros. Todos os valores derivados (saldo devedor, juros acumulados, valor para quitação, juros por atraso, valor devido hoje e demais cálculos financeiros) serão calculados pelo Domain Service no momento da consulta. Essa decisão passa a orientar toda a modelagem financeira do sistema. | 2026-08-01 | — |

---

## Pendências

- Preencher FOUNDATION-006 (Arquitetura Multi-Tenant), DOMAIN-017 (Aggregate Tenant), DOMAIN-018 (Entity Usuário) e DOMAIN-019 (Business Rule Toda Carteira pertence exatamente a um Tenant) com as fontes oficiais do Head de Produto.
- Criar documentos da camada Product (épicos, features e user stories) quando o domínio estiver modelado.
- Registrar decisões arquiteturais (ADR) quando surgirem.

---

## Próximo passo

> Aguardar as fontes oficiais da camada Multi-Tenant Nível 1 (FOUNDATION-006, DOMAIN-017, DOMAIN-018, DOMAIN-019) e materializá-las.

---

## Histórico de Atualizações

| Data | Autor | Resumo da Atualização |
|------|-------|-----------------------|
| 2026-08-01 | Head de Produto | Encerramento da fase de infraestrutura documental; projeto entra em Domain Modeling. TASK-001 a TASK-015 concluídas. |
| 2026-08-01 | Head de Produto | Registro da decisão de domínio PD-011: o sistema armazenará apenas fatos financeiros; valores derivados calculados pelo Domain Service no momento da consulta. |
| 2026-08-01 | Head de Produto | Camada Domain 100% materializada e aprovada (DOMAIN-001 a DOMAIN-016, v1.0.0); FOUNDATION-002 a FOUNDATION-005 materializados e aprovados; FOUNDATION-006, DOMAIN-017, DOMAIN-018 e DOMAIN-019 criados como estrutura da camada Multi-Tenant Nível 1 (TASK-027). |
