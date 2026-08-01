# HANDOFF-VIGENTE — Estado Atual do Projeto

> Este documento registra o estado do desenvolvimento entre sessões de trabalho, permitindo que
> qualquer membro da equipe retome o projeto rapidamente.

---

## Objetivo

> Registrar o estado do projeto entre sessões de trabalho. Seções sem informação ativa permanecem
> vazias até que exista conteúdo a registrar.

---

## Estado Atual

O projeto encerra a **fase de infraestrutura documental** e entra oficialmente na fase:

> **Domain Modeling**

---

## Foundation

- **FOUNDATION-001** — Visão do Produto: criado e aprovado pelo Product.
- **FOUNDATION-002** — Modelo de Domínio e Linguagem Ubíqua: estrutura preparada (cabeçalho institucional preenchido, corpo com placeholders), aguardando preenchimento pelo Head de Produto.

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

---

## Decisões aprovadas

| ID | Decisão | Data | Referência |
|----|---------|------|------------|
| PD-011 | O sistema armazenará apenas fatos financeiros. Todos os valores derivados (saldo devedor, juros acumulados, valor para quitação, juros por atraso, valor devido hoje e demais cálculos financeiros) serão calculados pelo Domain Service no momento da consulta. Essa decisão passa a orientar toda a modelagem financeira do sistema. | 2026-08-01 | — |

---

## Pendências

- Preencher FOUNDATION-002 (Modelo de Domínio e Linguagem Ubíqua) pelo Head de Produto.
- Criar documentos da camada Product (épicos, features e user stories) quando o domínio estiver modelado.
- Registrar decisões arquiteturais (ADR) quando surgirem.

---

## Próximo passo

> Modelagem do DOMAIN-001 — Aggregate Carteira.

---

## Histórico de Atualizações

| Data | Autor | Resumo da Atualização |
|------|-------|-----------------------|
| 2026-08-01 | Head de Produto | Encerramento da fase de infraestrutura documental; projeto entra em Domain Modeling. TASK-001 a TASK-015 concluídas. |
| 2026-08-01 | Head de Produto | Registro da decisão de domínio PD-011: o sistema armazenará apenas fatos financeiros; valores derivados calculados pelo Domain Service no momento da consulta. |
