# DOCUMENT-ARCHITECTURE-MANIFEST — Manifesto Executável da Migração Documental

**ID:** DOCUMENT-ARCHITECTURE-MANIFEST

**Versão:** 1.0.0

**Status:** Rascunho para revisão

**Data:** 2026-08-04

**Autor:** Principal Software Architect / Documentation Architect / CTO / Migration Architect

---

# 1. Propósito

Este documento é a **fonte de verdade executável** da migração da arquitetura documental. Ele não contém opinião, arquitetura alvo de longo prazo nem discussões estratégicas — apenas a lista determinística de ações a serem executadas no branch `docs/migration-2026-08-04`.

Cada linha representa um arquivo ou pasta do estado atual. As colunas definem o destino, a ação, a fase e uma observação objetiva.

---

# 2. Instruções de Execução

1. Trabalhar exclusivamente no branch `docs/migration-2026-08-04`.
2. Nunca modificar conteúdo dos documentos (salvo `README.md`).
3. Usar `git mv` para todas as ações de "Mover".
4. Usar `git rm` para todas as ações de "Remover".
5. Executar `npm run docs:validate` ao final de cada fase.
6. Congelar alterações em `docs/` até o merge.

---

# 3. Manifesto

## 3.1 Foundation

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/foundation/FOUNDATION-001-product-vision.md` | Camada Foundation | `docs/foundation/FOUNDATION-001-product-vision.md` | Manter | 2 | Nome e conteúdo inalterados. Pasta `foundation` permanece sem prefixo numérico. |
| `docs/foundation/FOUNDATION-002-modelo-de-dominio-e-linguagem-ubiqua.md` | Camada Foundation | `docs/foundation/FOUNDATION-002-modelo-de-dominio-e-linguagem-ubiqua.md` | Manter | 2 | Divisão em glossário separado é evolução futura, não migração. |
| `docs/foundation/FOUNDATION-003-mapa-do-dominio.md` | Camada Foundation | `docs/foundation/FOUNDATION-003-mapa-do-dominio.md` | Manter | 2 | — |
| `docs/foundation/FOUNDATION-004-core-domain.md` | Camada Foundation | `docs/foundation/FOUNDATION-004-core-domain.md` | Manter | 2 | — |
| `docs/foundation/FOUNDATION-005-inventario-do-dominio.md` | Camada Foundation | `docs/foundation/FOUNDATION-005-inventario-do-dominio.md` | Manter | 2 | Refatoração para glossary é evolução futura. |
| `docs/foundation/FOUNDATION-006-arquitetura-multi-tenant.md` | Camada Foundation | `docs/foundation/FOUNDATION-006-arquitetura-multi-tenant.md` | Manter | 2 | — |
| `docs/foundation/FOUNDATION-007-product-map.md` | Camada Foundation | `docs/foundation/FOUNDATION-007-product-map.md` | Manter | 2 | — |
| `docs/foundation/FOUNDATION-008-mvp-scope.md` | Camada Foundation | `docs/foundation/FOUNDATION-008-mvp-scope.md` | Manter | 2 | — |

## 3.2 Domain

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/domain/aggregates/.gitkeep` | Placeholder vazio | — | Remover | 1 | Pasta será populada após migração. |
| `docs/domain/entities/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/domain/events/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/domain/glossary/.gitkeep` | Placeholder vazio | — | Remover | 1 | Glossário é evolução futura. |
| `docs/domain/rules/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/domain/services/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/domain/value-objects/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/domain/aggregates/DOMAIN-001-aggregate-carteira.md` | Credit Context | `docs/domain/credit/aggregates/DOMAIN-001-aggregate-carteira.md` | Mover | 3 | Bounded context Credit. |
| `docs/domain/aggregates/DOMAIN-017-aggregate-tenant.md` | Platform Context | `docs/domain/platform/aggregates/DOMAIN-017-aggregate-tenant.md` | Mover | 3 | Bounded context Platform. |
| `docs/domain/entities/DOMAIN-002-entity-pessoa.md` | Credit Context | `docs/domain/credit/entities/DOMAIN-002-entity-pessoa.md` | Mover | 3 | — |
| `docs/domain/entities/DOMAIN-003-entity-contrato-de-credito.md` | Credit Context | `docs/domain/credit/entities/DOMAIN-003-entity-contrato-de-credito.md` | Mover | 3 | — |
| `docs/domain/entities/DOMAIN-004-entity-emprestimo.md` | Credit Context | `docs/domain/credit/entities/DOMAIN-004-entity-emprestimo.md` | Mover | 3 | — |
| `docs/domain/entities/DOMAIN-005-entity-parcela.md` | Credit Context | `docs/domain/credit/entities/DOMAIN-005-entity-parcela.md` | Mover | 3 | — |
| `docs/domain/entities/DOMAIN-006-entity-pagamento.md` | Credit Context | `docs/domain/credit/entities/DOMAIN-006-entity-pagamento.md` | Mover | 3 | — |
| `docs/domain/entities/DOMAIN-018-entity-usuario.md` | Platform Context | `docs/domain/platform/entities/DOMAIN-018-entity-usuario.md` | Mover | 3 | — |
| `docs/domain/value-objects/DOMAIN-007-vo-dinheiro.md` | Credit Context | `docs/domain/credit/value-objects/DOMAIN-007-vo-dinheiro.md` | Mover | 3 | — |
| `docs/domain/value-objects/DOMAIN-008-vo-periodicidade.md` | Credit Context | `docs/domain/credit/value-objects/DOMAIN-008-vo-periodicidade.md` | Mover | 3 | — |
| `docs/domain/value-objects/DOMAIN-009-vo-modalidade-de-emprestimo.md` | Credit Context | `docs/domain/credit/value-objects/DOMAIN-009-vo-modalidade-de-emprestimo.md` | Mover | 3 | — |
| `docs/domain/services/DOMAIN-010-service-motor-financeiro.md` | Credit Context | `docs/domain/credit/services/DOMAIN-010-service-motor-financeiro.md` | Mover | 3 | — |
| `docs/domain/events/DOMAIN-011-event-emprestimo-criado.md` | Credit Context | `docs/domain/credit/events/DOMAIN-011-event-emprestimo-criado.md` | Mover | 3 | — |
| `docs/domain/events/DOMAIN-012-event-pagamento-registrado.md` | Credit Context | `docs/domain/credit/events/DOMAIN-012-event-pagamento-registrado.md` | Mover | 3 | — |
| `docs/domain/events/DOMAIN-013-event-emprestimo-quitado.md` | Credit Context | `docs/domain/credit/events/DOMAIN-013-event-emprestimo-quitado.md` | Mover | 3 | — |
| `docs/domain/rules/DOMAIN-014-rule-emprestimo-deve-possuir-devedor.md` | Credit Context | `docs/domain/credit/rules/DOMAIN-014-rule-emprestimo-deve-possuir-devedor.md` | Mover | 3 | — |
| `docs/domain/rules/DOMAIN-015-rule-pagamento-nao-pode-ser-negativo.md` | Credit Context | `docs/domain/credit/rules/DOMAIN-015-rule-pagamento-nao-pode-ser-negativo.md` | Mover | 3 | — |
| `docs/domain/rules/DOMAIN-016-rule-emprestimo-quitado-nao-recebe-pagamentos.md` | Credit Context | `docs/domain/credit/rules/DOMAIN-016-rule-emprestimo-quitado-nao-recebe-pagamentos.md` | Mover | 3 | — |
| `docs/domain/rules/DOMAIN-019-rule-toda-carteira-pertence-exatamente-a-um-tenant.md` | Platform Context | `docs/domain/platform/rules/DOMAIN-019-rule-toda-carteira-pertence-exatamente-a-um-tenant.md` | Mover | 3 | — |

## 3.3 Product

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/product/capabilities/PRODUCT-001-administrar-plataforma.md` | Platform Context | `docs/product/platform/capabilities/PRODUCT-001-administrar-plataforma.md` | Mover | 3 | — |
| `docs/product/epics/EPIC-001-gerenciar-tenant.md` | Platform Context | `docs/product/platform/epics/EPIC-001-gerenciar-tenant.md` | Mover | 3 | — |
| `docs/product/features/FEATURE-001-criar-tenant.md` | Platform Context | `docs/product/platform/features/FEATURE-001-criar-tenant.md` | Mover | 3 | — |
| `docs/product/features/FEATURE-002-consultar-tenant.md` | Platform Context | `docs/product/platform/features/FEATURE-002-consultar-tenant.md` | Mover | 3 | — |
| `docs/product/features/FEATURE-003-atualizar-tenant.md` | Platform Context | `docs/product/platform/features/FEATURE-003-atualizar-tenant.md` | Mover | 3 | — |
| `docs/product/features/FEATURE-004-inativar-tenant.md` | Platform Context | `docs/product/platform/features/FEATURE-004-inativar-tenant.md` | Mover | 3 | — |
| `docs/product/user-stories/US-001-criar-tenant.md` | Platform Context | `docs/product/platform/user-stories/US-001-criar-tenant.md` | Mover | 3 | — |
| `docs/product/user-stories/US-009-consultar-tenant-por-id.md` | Platform Context | `docs/product/platform/user-stories/US-009-consultar-tenant-por-id.md` | Mover | 3 | — |
| `docs/product/user-stories/US-010-consultar-tenant-por-identificador.md` | Platform Context | `docs/product/platform/user-stories/US-010-consultar-tenant-por-identificador.md` | Mover | 3 | — |
| `docs/product/user-stories/US-011-listar-tenants.md` | Platform Context | `docs/product/platform/user-stories/US-011-listar-tenants.md` | Mover | 3 | — |
| `docs/product/user-stories/US-012-atualizar-dados-cadastrais-do-tenant.md` | Platform Context | `docs/product/platform/user-stories/US-012-atualizar-dados-cadastrais-do-tenant.md` | Mover | 3 | — |
| `docs/product/user-stories/US-013-inativar-tenant.md` | Platform Context | `docs/product/platform/user-stories/US-013-inativar-tenant.md` | Mover | 3 | — |
| `docs/product/user-stories/US-014-reativar-tenant.md` | Platform Context | `docs/product/platform/user-stories/US-014-reativar-tenant.md` | Mover | 3 | — |

## 3.4 Architecture

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/architecture/AMP-001-architecture-master-plan.md` | Camada Architecture | `docs/architecture/amp/AMP-001-architecture-master-plan.md` | Mover | 3 | Agrupar documentos estratégicos em `amp/`. |
| `docs/architecture/DOCUMENT-ARCHITECTURE-DISCOVERY.md` | Camada Architecture | `docs/architecture/amp/DOCUMENT-ARCHITECTURE-DISCOVERY.md` | Mover | 3 | — |
| `docs/architecture/DOCUMENT-ARCHITECTURE-MIGRATION-PLAN.md` | Camada Architecture | `docs/architecture/amp/DOCUMENT-ARCHITECTURE-MIGRATION-PLAN.md` | Mover | 3 | — |
| `docs/architecture/DOCUMENT-ARCHITECTURE-MANIFEST.md` | Camada Architecture | `docs/architecture/amp/DOCUMENT-ARCHITECTURE-MANIFEST.md` | Criar | 2 | Este documento. |
| `docs/decisions/ADR-001-stack-tecnologica-oficial-mvp.md` | Camada Decisions | `docs/architecture/adrs/ADR-001-stack-tecnologica-oficial-mvp.md` | Mover | 3 | ADRs fazem parte de Architecture. |
| `docs/decisions/ADR-002-auditoria-independente-da-transacao.md` | Camada Decisions | `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md` | Mover | 3 | — |

## 3.5 Implementation

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/implementation/api/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/implementation/architecture/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/implementation/database/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/implementation/testing/.gitkeep` | Placeholder vazio | — | Remover | 1 | — |
| `docs/implementation/plans/PLAN-001-feature-001-tenant-provisioning.md` | Plano técnico | `docs/implementation/plans/PLAN-001-feature-001-tenant-provisioning.md` | Manter | 2 | Caminho permanece; limpeza da pasta. |
| `docs/implementation/plans/PLAN-001-execution-backlog.md` | Backlog de execução | `docs/implementation/backlogs/PLAN-001-execution-backlog.md` | Mover | 3 | Separar plano técnico de backlog. |
| `docs/implementation/plans/PLAN-002-epic-001-tenant-management.md` | Plano técnico | `docs/implementation/plans/PLAN-002-epic-001-tenant-management.md` | Manter | 2 | Caminho permanece; limpeza da pasta. |
| `docs/implementation/plans/PLAN-002-execution-backlog.md` | Backlog de execução | `docs/implementation/backlogs/PLAN-002-execution-backlog.md` | Mover | 3 | Separar plano técnico de backlog. |
| `docs/implementation/plans/PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md` | Pedido de decisão | `docs/governance/decision-requests/PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md` | Mover | 3 | Não é plano de implementação. |
| `docs/implementation/plansPLAN-002-epic-001-tenant-management.md` | Arquivo corrompido/duplicado | — | Remover | 1 | Nome colado; duplicata de `implementation/plans/PLAN-002-epic-001-tenant-management.md`. |
| `docs/implementationplans/PLAN-002-epic-001-tenant-management.md` | Pasta duplicada/errada | — | Remover | 1 | Pasta `implementationplans` é erro de estrutura. |

## 3.6 Governance

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/handoffs/2026-08-04-handoff-sessao-epic-001-tenant-management-fechado.md` | Handoff datado | `docs/governance/handoffs/2026-08-04-handoff-sessao-epic-001-tenant-management-fechado.md` | Mover | 3 | Handoffs são artefatos de governança. |
| `docs/handoffs/HANDOFF-VIGENTE.md` | Ponteiro de máquina | `~/HANDOFF-VIGENTE.md` | Remover do repo | 1 | Estado local; não deve versionar no repo. Atualizar ponteiro externo na Fase 6. |

## 3.7 Audits & Discoveries

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/auditorias/auditoria-as-is-to-be-ecossistema.md` | Auditoria arquitetural | `docs/audits/audits/auditoria-as-is-to-be-ecossistema.md` | Mover | 3 | Classificada como auditoria formal. |
| `docs/auditorias/raio-x-arquitetural-ecossistema.md` | Raio-x arquitetural | `docs/audits/audits/raio-x-arquitetural-ecossistema.md` | Mover | 3 | — |
| `docs/auditorias/discovery-adr-003-multi-tenant.md` | Discovery de ADR | `docs/audits/discoveries/discovery-adr-003-multi-tenant.md` | Mover | 3 | É uma descoberta, não auditoria. |
| `docs/discoveries/FEATURE-002-consultar-tenant-discovery.md` | Discovery de feature | `docs/audits/discoveries/FEATURE-002-consultar-tenant-discovery.md` | Mover | 3 | — |
| `docs/discoveries/FEATURE-003-atualizar-tenant-discovery.md` | Discovery de feature | `docs/audits/discoveries/FEATURE-003-atualizar-tenant-discovery.md` | Mover | 3 | — |
| `docs/discoveries/FEATURE-004-inativar-tenant-discovery.md` | Discovery de feature | `docs/audits/discoveries/FEATURE-004-inativar-tenant-discovery.md` | Mover | 3 | — |

## 3.8 References

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/templates/adr-template.md` | Template | `docs/templates/adr-template.md` | Manter | 2 | Mantido no local atual para minimizar mudança. Evolução futura pode movê-lo para `references/`. |
| `docs/templates/aggregate-template.md` | Template | `docs/templates/aggregate-template.md` | Manter | 2 | — |
| `docs/templates/business-rule-template.md` | Template | `docs/templates/business-rule-template.md` | Manter | 2 | — |
| `docs/templates/domain-event-template.md` | Template | `docs/templates/domain-event-template.md` | Manter | 2 | — |
| `docs/templates/domain-service-template.md` | Template | `docs/templates/domain-service-template.md` | Manter | 2 | — |
| `docs/templates/entity-template.md` | Template | `docs/templates/entity-template.md` | Manter | 2 | — |
| `docs/templates/epic-template.md` | Template | `docs/templates/epic-template.md` | Manter | 2 | — |
| `docs/templates/feature-template.md` | Template | `docs/templates/feature-template.md` | Manter | 2 | — |
| `docs/templates/foundation-template.md` | Template | `docs/templates/foundation-template.md` | Manter | 2 | — |
| `docs/templates/implementation-plan-template.md` | Template | `docs/templates/implementation-plan-template.md` | Manter | 2 | Atualização de conteúdo é evolução futura. |
| `docs/templates/mermaid-template.md` | Template | `docs/templates/mermaid-template.md` | Manter | 2 | — |
| `docs/templates/user-story-template.md` | Template | `docs/templates/user-story-template.md` | Manter | 2 | — |
| `docs/templates/value-object-template.md` | Template | `docs/templates/value-object-template.md` | Manter | 2 | — |
| `docs/assets/diagrams/` | Assets | `docs/assets/diagrams/` | Manter | 2 | Manter local atual. Evolução futura pode reorganizar. |
| `docs/assets/images/` | Assets | `docs/assets/images/` | Manter | 2 | — |
| `docs/ux/wireframes/` | UX | `docs/ux/wireframes/` | Manter | 2 | — |

## 3.9 Outros artefatos

| Documento | Situação atual | Destino | Ação | Fase | Observação |
|-----------|----------------|---------|------|------|------------|
| `docs/graphify-out/` | Cache de ferramenta | Fora de `docs/` (`.gitignore`) | Remover do repo | 1 | Adicionar `/graphify-out/` e `/docs/graphify-out/` ao `.gitignore`. |
| `docs/README.md` | Não existe | `docs/README.md` | Criar | 2 | Mapa de navegação mínimo. |

---

# 4. Estrutura Alvo Mínima (resultado da migração)

```
docs/
├── README.md
├── foundation/
│   └── (8 documentos inalterados)
├── domain/
│   ├── platform/
│   │   ├── aggregates/
│   │   ├── entities/
│   │   └── rules/
│   └── credit/
│       ├── aggregates/
│       ├── entities/
│       ├── value-objects/
│       ├── services/
│       ├── events/
│       └── rules/
├── product/
│   ├── platform/
│   │   ├── capabilities/
│   │   ├── epics/
│   │   ├── features/
│   │   └── user-stories/
│   └── credit/
│       └── (vazio)
├── architecture/
│   ├── amp/
│   │   ├── AMP-001-architecture-master-plan.md
│   │   ├── DOCUMENT-ARCHITECTURE-DISCOVERY.md
│   │   ├── DOCUMENT-ARCHITECTURE-MIGRATION-PLAN.md
│   │   └── DOCUMENT-ARCHITECTURE-MANIFEST.md
│   ├── adrs/
│   │   ├── ADR-001-stack-tecnologica-oficial-mvp.md
│   │   └── ADR-002-auditoria-independente-da-transacao.md
│   └── reviews/
│       └── (vazio)
├── implementation/
│   ├── plans/
│   │   ├── PLAN-001-feature-001-tenant-provisioning.md
│   │   └── PLAN-002-epic-001-tenant-management.md
│   └── backlogs/
│       ├── PLAN-001-execution-backlog.md
│       └── PLAN-002-execution-backlog.md
├── governance/
│   ├── handoffs/
│   │   └── 2026-08-04-handoff-sessao-epic-001-tenant-management-fechado.md
│   └── decision-requests/
│       └── PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md
├── audits/
│   ├── audits/
│   │   ├── auditoria-as-is-to-be-ecossistema.md
│   │   └── raio-x-arquitetural-ecossistema.md
│   └── discoveries/
│       ├── FEATURE-002-consultar-tenant-discovery.md
│       ├── FEATURE-003-atualizar-tenant-discovery.md
│       ├── FEATURE-004-inativar-tenant-discovery.md
│       └── discovery-adr-003-multi-tenant.md
├── templates/
│   └── (13 templates inalterados)
├── assets/
│   └── (inalterado)
└── ux/
    └── (inalterado)
```

**Nota:** a separação `implementation/plans/` e `implementation/backlogs/` já existe no manifesto. A dúvida sobre os PLAN-*-execution-backlog é resolvida: eles são **backlogs de execução**, portanto vão para `implementation/backlogs/`.

---

# 5. Ações Fora do Escopo (evolução futura)

As seguintes mudanças foram removidas do plano de migração e serão tratadas em tasks/EPICs futuros:

| Mudança | Motivo |
|---------|--------|
| Criar `docs/04-engineering/` | Evolução arquitetural; requer ADRs (CI/CD, observability, security). |
| Criar `docs/08-operations/` | Evolução; requer runbooks/playbooks maduros. |
| Criar `docs/09-references/` | Evolução; `docs/templates/`, `docs/assets/`, `docs/ux/` podem migrar depois. |
| Criar `docs/architecture/context-maps/` | Evolução; context maps serão produzidos conforme bounded contexts emergirem. |
| Criar `docs/architecture/rfcs/` | Evolução; RFCs serão introduzidos quando houver propostas formais. |
| Dividir `FOUNDATION-002` | Refatoração documental, não migração física. |
| Criar `docs/glossary.md` | Refatoração; depende de decisão sobre glossário. |
| Atualizar conteúdo de templates | Refatoração; pode introduzir inconsistências. |
| Criar novos templates | Evolução; RFC, Standard, Runbook, Playbook. |
| Adicionar front matter YAML em todos os docs | Melhoria documental; task separada. |
| Criar `docs/index.json` | Depende de front matter ou parser; task separada. |
| Renumerar camadas com prefixos `00-`, `01-` | Evolução futura; manter nomes semânticos por enquanto. |

---

# 6. Fases da Migração (sintetizadas)

| Fase | Nome | Ações principais | Critério de conclusão |
|------|------|------------------|------------------------|
| 0 | Preparação | Branch, congelamento documental, validações verdes na main. | Branch criado; `docs:validate` e `pytest` passam na main. |
| 1 | Higiene | Remover duplicatas, arquivos corrompidos, `.gitkeep` vazios, `graphify-out/`, `HANDOFF-VIGENTE.md` do repo. | `docs:validate` passa; apenas remoções esperadas. |
| 2 | Estrutura mínima | Criar pastas alvo conforme manifesto; criar `docs/README.md`. | Diretórios criados; nenhum documento movido ainda. |
| 3 | Movimentação | `git mv` todos os documentos conforme manifesto. | Todos os documentos nos destinos; nenhum órfão. |
| 4 | Scripts | Atualizar `scripts/validate-docs.js` e `.gitignore`. | `docs:validate` passa na nova estrutura. |
| 5 | Validação final | `docs:validate`, `pytest`, `ruff`, `black`, `mypy`. | Todas as validações passam. |
| 6 | Merge e handoff | Merge para `main`; atualizar `~/HANDOFF-VIGENTE.md`. | `main` estável; handoff atualizado. |

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-04 | Manifesto executável da migração documental: tabela determinística de arquivos, destinos, ações e fases. |

---

**Nota de encerramento:** Este documento é puramente operacional. Nenhuma mudança foi executada. Nenhum arquivo foi movido, renomeado, alterado ou removido. Aguardando autorização para execução.
