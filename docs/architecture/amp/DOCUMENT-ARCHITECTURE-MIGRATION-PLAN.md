# DOCUMENT-ARCHITECTURE-MIGRATION-PLAN — Plano de Migração da Arquitetura Documental

**ID:** DOCUMENT-ARCHITECTURE-MIGRATION-PLAN

**Versão:** 1.1.0

**Status:** Rascunho para revisão

**Data:** 2026-08-04

**Autor:** Principal Software Architect / Documentation Architect / CTO / Migration Architect

---

# 1. Resumo Executivo

A `DOCUMENT-ARCHITECTURE-DISCOVERY` identificou problemas de estrutura, duplicação e categorização na documentação da TiaNet. Este plano define **como migrar** da arquitetura documental atual para a arquitetura alvo mínima **sem perder rastreabilidade**, **sem quebrar `docs:validate`**, **sem perder histórico Git** e **sem interromper os agentes SDD**.

## Decisão do Arquiteto

A migração deve ocorrer **em fases, em um branch isolado, antes do início do EPIC-002**. Não deve ser executada durante a implementação de um EPIC. O momento ideal é **agora**, entre o encerramento do EPIC-001 e o início do EPIC-002, pois a base documental ainda é pequena o suficiente para ser reorganizada com baixo risco.

## Princípios diretores

1. **IDs são imutáveis.** Os conteúdos dos documentos (incluindo IDs) não serão alterados.
2. **Caminhos de arquivos são a única coisa que muda.** Nomes de arquivos `.md` não serão alterados, salvo para eliminar duplicatas/corrompidos.
3. **`git mv` obrigatório.** Preserva histórico de alterações.
4. **`docs:validate` nunca deve falhar por mais de uma fase.** Cada fase deve manter o validador passando (antigo ou transicional).
5. **Congelamento documental durante a migração.** Nenhum outro agente deve alterar `docs/` no branch de migração.
6. **Rollback por fase.** Cada fase possui estratégia de reversão independente.
7. **Migração mínima.** A arquitetura alvo contém apenas as camadas necessárias hoje. Evoluções futuras (engineering, operations, references, context-maps, rfcs, front matter YAML, `index.json`) são explicitamente fora do escopo.

---

# 2. Arquitetura Documental Alvo Mínima

A migração produzirá a seguinte estrutura. Camadas entre parênteses indicam futura evolução, **não** criadas nesta migração.

```
docs/
├── README.md
├── foundation/                          # Visão, escopo, princípios, linguagem ubíqua
│   ├── FOUNDATION-001-product-vision.md
│   ├── FOUNDATION-002-modelo-de-dominio-e-linguagem-ubiqua.md
│   ├── FOUNDATION-003-mapa-do-dominio.md
│   ├── FOUNDATION-004-core-domain.md
│   ├── FOUNDATION-005-inventario-do-dominio.md
│   ├── FOUNDATION-006-arquitetura-multi-tenant.md
│   ├── FOUNDATION-007-product-map.md
│   └── FOUNDATION-008-mvp-scope.md
├── domain/                              # DDD por bounded context
│   ├── platform/
│   │   ├── aggregates/
│   │   │   └── DOMAIN-017-aggregate-tenant.md
│   │   ├── entities/
│   │   │   └── DOMAIN-018-entity-usuario.md
│   │   └── rules/
│   │       └── DOMAIN-019-rule-toda-carteira-pertence-exatamente-a-um-tenant.md
│   └── credit/
│       ├── aggregates/
│       │   └── DOMAIN-001-aggregate-carteira.md
│       ├── entities/
│       │   ├── DOMAIN-002-entity-pessoa.md
│       │   ├── DOMAIN-003-entity-contrato-de-credito.md
│       │   ├── DOMAIN-004-entity-emprestimo.md
│       │   ├── DOMAIN-005-entity-parcela.md
│       │   └── DOMAIN-006-entity-pagamento.md
│       ├── value-objects/
│       │   ├── DOMAIN-007-vo-dinheiro.md
│       │   ├── DOMAIN-008-vo-periodicidade.md
│       │   └── DOMAIN-009-vo-modalidade-de-emprestimo.md
│       ├── services/
│       │   └── DOMAIN-010-service-motor-financeiro.md
│       ├── events/
│       │   ├── DOMAIN-011-event-emprestimo-criado.md
│       │   ├── DOMAIN-012-event-pagamento-registrado.md
│       │   └── DOMAIN-013-event-emprestimo-quitado.md
│       └── rules/
│           ├── DOMAIN-014-rule-emprestimo-deve-possuir-devedor.md
│           ├── DOMAIN-015-rule-pagamento-nao-pode-ser-negativo.md
│           └── DOMAIN-016-rule-emprestimo-quitado-nao-recebe-pagamentos.md
├── product/                             # Product por bounded context
│   ├── platform/
│   │   ├── capabilities/
│   │   │   └── PRODUCT-001-administrar-plataforma.md
│   │   ├── epics/
│   │   │   └── EPIC-001-gerenciar-tenant.md
│   │   ├── features/
│   │   │   ├── FEATURE-001-criar-tenant.md
│   │   │   ├── FEATURE-002-consultar-tenant.md
│   │   │   ├── FEATURE-003-atualizar-tenant.md
│   │   │   └── FEATURE-004-inativar-tenant.md
│   │   └── user-stories/
│   │       ├── US-001-criar-tenant.md
│   │       ├── US-009-consultar-tenant-por-id.md
│   │       ├── US-010-consultar-tenant-por-identificador.md
│   │       ├── US-011-listar-tenants.md
│   │       ├── US-012-atualizar-dados-cadastrais-do-tenant.md
│   │       ├── US-013-inativar-tenant.md
│   │       └── US-014-reativar-tenant.md
│   └── credit/
│       └── (vazio até o EPIC-002)
├── architecture/                        # AMP, ADRs, reviews
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
├── implementation/                      # Planos técnicos e backlogs
│   ├── plans/
│   │   ├── PLAN-001-feature-001-tenant-provisioning.md
│   │   └── PLAN-002-epic-001-tenant-management.md
│   └── backlogs/
│       ├── PLAN-001-execution-backlog.md
│       └── PLAN-002-execution-backlog.md
├── governance/                          # Handoffs e decision requests
│   ├── handoffs/
│   │   └── 2026-08-04-handoff-sessao-epic-001-tenant-management-fechado.md
│   └── decision-requests/
│       └── PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md
├── audits/                              # Auditorias e descobertas
│   ├── audits/
│   │   ├── auditoria-as-is-to-be-ecossistema.md
│   │   └── raio-x-arquitetural-ecossistema.md
│   └── discoveries/
│       ├── FEATURE-002-consultar-tenant-discovery.md
│       ├── FEATURE-003-atualizar-tenant-discovery.md
│       ├── FEATURE-004-inativar-tenant-discovery.md
│       └── discovery-adr-003-multi-tenant.md
├── templates/                           # Mantidos no local atual
│   └── (13 templates inalterados)
├── assets/                              # Mantidos no local atual
│   ├── diagrams/
│   └── images/
└── ux/                                  # Mantidos no local atual
    └── wireframes/
```

### Camadas não criadas nesta migração (evolução futura)

- `engineering/` (CI/CD, standards, security)
- `operations/` (runbooks, playbooks)
- `references/` (templates, assets, ux podem migrar para cá no futuro)
- `architecture/context-maps/`
- `architecture/rfcs/`
- `governance/processes/` (processos maduros)
- `index.json`
- Front matter YAML em massa

---

# 3. Pastas a Criar

| Pasta | Caminho | Motivo |
|-------|---------|--------|
| `docs/README.md` | `docs/README.md` | Mapa de navegação e onboarding. |
| `domain/platform/` | `docs/domain/platform/` | Namespace para bounded context Platform. |
| `domain/platform/aggregates/` | `docs/domain/platform/aggregates/` | Subcategoria DDD. |
| `domain/platform/entities/` | `docs/domain/platform/entities/` | Subcategoria DDD. |
| `domain/platform/rules/` | `docs/domain/platform/rules/` | Subcategoria DDD. |
| `domain/credit/` | `docs/domain/credit/` | Namespace para bounded context Credit. |
| `domain/credit/aggregates/` | `docs/domain/credit/aggregates/` | Subcategoria DDD. |
| `domain/credit/entities/` | `docs/domain/credit/entities/` | Subcategoria DDD. |
| `domain/credit/value-objects/` | `docs/domain/credit/value-objects/` | Subcategoria DDD. |
| `domain/credit/services/` | `docs/domain/credit/services/` | Subcategoria DDD. |
| `domain/credit/events/` | `docs/domain/credit/events/` | Subcategoria DDD. |
| `domain/credit/rules/` | `docs/domain/credit/rules/` | Subcategoria DDD. |
| `product/platform/` | `docs/product/platform/` | Namespace product Platform. |
| `product/platform/capabilities/` | `docs/product/platform/capabilities/` | Capabilities. |
| `product/platform/epics/` | `docs/product/platform/epics/` | Épicos. |
| `product/platform/features/` | `docs/product/platform/features/` | Features. |
| `product/platform/user-stories/` | `docs/product/platform/user-stories/` | User stories. |
| `product/credit/` | `docs/product/credit/` | Namespace product Credit (vazio). |
| `architecture/amp/` | `docs/architecture/amp/` | AMP e documentações estratégicas. |
| `architecture/adrs/` | `docs/architecture/adrs/` | Decisões arquiteturais aprovadas. |
| `architecture/reviews/` | `docs/architecture/reviews/` | Reviews e auditorias arquiteturais. |
| `implementation/backlogs/` | `docs/implementation/backlogs/` | Backlogs de execução. |
| `governance/handoffs/` | `docs/governance/handoffs/` | Handoffs datados. |
| `governance/decision-requests/` | `docs/governance/decision-requests/` | Pedidos de orientação/decisão. |
| `audits/audits/` | `docs/audits/audits/` | Auditorias formais. |
| `audits/discoveries/` | `docs/audits/discoveries/` | Descobertas e análises. |

---

# 4. Pastas que Desaparecerão

| Pasta Atual | Destino | Motivo |
|-------------|---------|--------|
| `docs/auditorias/` | `docs/audits/` | Separação entre auditorias e descobertas. |
| `docs/decisions/` | `docs/architecture/adrs/` | ADRs são arquitetura. |
| `docs/discoveries/` | `docs/audits/discoveries/` | Descobertas unificadas em `audits/`. |
| `docs/domain/` | `docs/domain/<context>/` | Reorganização por bounded context. |
| `docs/foundation/` | `docs/foundation/` | Camada permanece sem renomeação numérica. |
| `docs/handoffs/` | `docs/governance/handoffs/` | Handoffs são governança. |
| `docs/implementation/` | `docs/implementation/` | Limpeza e separação `plans/`/`backlogs/`. |
| `docs/implementationplans/` | Removida | Pasta duplicada/errada. |
| `docs/product/` | `docs/product/<context>/` | Reorganização por bounded context. |
| `docs/graphify-out/` | Fora de `docs/` | Cache de ferramenta, não documentação. |

---

# 5. Documentos que Permanecerão Exatamente Onde Estão

Nenhum documento markdown com conteúdo permanece no caminho atual. **Todos** serão movidos. Os **nomes dos arquivos .md permanecem inalterados** (exceto duplicatas/corrompidos), preservando a identidade visual e a rastreabilidade por ID.

### Exceção: templates, assets e UX

- `docs/templates/*` permanecem no caminho atual (não vão para `references/`).
- `docs/assets/*` permanecem no caminho atual.
- `docs/ux/*` permanecem no caminho atual.

Essa decisão minimiza o escopo da migração. A reorganização dessas pastas é evolução futura.

---

# 6. Documentos que Serão Movidos

A tabela completa de movimentações está em `docs/architecture/amp/DOCUMENT-ARCHITECTURE-MANIFEST.md`. Abaixo, o resumo por camada.

| Camada | Documentos | Destino |
|--------|------------|---------|
| Foundation | 8 documentos | `docs/foundation/` (caminho inalterado) |
| Domain | 19 documentos | `docs/domain/platform/` ou `docs/domain/credit/` |
| Product | 14 documentos | `docs/product/platform/` |
| Architecture | AMP, DISCOVERY, MIGRATION-PLAN, MANIFEST | `docs/architecture/amp/` |
| ADRs | 2 documentos | `docs/architecture/adrs/` |
| Implementation | 2 planos técnicos | `docs/implementation/plans/` |
| Backlogs | 2 documentos | `docs/implementation/backlogs/` |
| Decision Request | 1 documento | `docs/governance/decision-requests/` |
| Handoff | 1 documento | `docs/governance/handoffs/` |
| Audits | 2 documentos | `docs/audits/audits/` |
| Discoveries | 4 documentos | `docs/audits/discoveries/` |

### Documentos que serão removidos

| Documento | Motivo |
|-----------|--------|
| `docs/implementationplans/` | Pasta duplicada/errada. |
| `docs/implementation/plansPLAN-002-epic-001-tenant-management.md` | Nome colado; duplicata. |
| `docs/handoffs/HANDOFF-VIGENTE.md` | Ponteiro de máquina; não deve versionar no repo. |
| `docs/graphify-out/` | Cache de ferramenta; adicionar a `.gitignore`. |
| `.gitkeep` desnecessários | Placeholders vazios. |

---

# 7. Preservação de Rastreabilidade

## 7.1 IDs

- **Estratégia:** IDs (`FOUNDATION-001`, `DOMAIN-017`, `AMP-001`, etc.) permanecem **inalterados** no conteúdo dos documentos.
- **Validação:** executar `rg '^#\s+(FOUNDATION|DOMAIN|PRODUCT|EPIC|FEATURE|US|ADR|AMP)-\d+' docs/` e garantir que todos os IDs ainda são encontráveis.
- **Impacto:** nenhum. A referência cruzada por ID continua válida.

## 7.2 Links

- **Estratégia:** identificar todos os links Markdown relativos entre documentos antes da migração.
- **Comando:** `rg '\]\([^#)]' docs/ --type md` (regex simplificada; ajustar conforme necessário).
- **Se houver links:** atualizar para novos caminhos relativos.
- **Se não houver links:** nenhuma ação necessária.
- **Risco:** baixo. A documentação atual usa principalmente referências por ID textual, não links relativos.

## 7.3 Referências Cruzadas

- **Estratégia:** referências por ID (ex.: "ver DOMAIN-017") permanecem válidas porque os IDs não mudam.
- **Validação:** executar `npm run docs:validate` (ou `node scripts/validate-docs.js`) e garantir que nenhuma referência cruzada para ID desconhecido seja introduzida.
- **Impacto:** mínimo. Os avisos de referência para IDs futuros (EPIC-002, etc.) continuarão existindo e são aceitáveis.

## 7.4 docs:validate

- **Estratégia:** não permitir que `docs:validate` falhe por mais de uma fase.
- **Fase 0:** atualizar `scripts/validate-docs.js` para suportar **tanto a estrutura antiga quanto a nova** (modo transicional).
- **Fase 4:** remover suporte à estrutura antiga e validar apenas a nova.
- **Critério:** `npm run docs:validate` deve retornar 0 erros ao final de cada fase.

## 7.5 Histórico Git

- **Estratégia:** usar `git mv` para todos os movimentos.
- **Preservação:** `git log --follow <novo-caminho>` continua mostrando histórico completo.
- **Ação:** nunca usar `mv` seguido de `git add`/`git rm` separados; isso quebra o `follow`.
- **Rollback:** `git revert` ou `git checkout` por fase.

---

# 8. Scripts a Atualizar

## 8.1 `scripts/validate-docs.js`

**Mudanças necessárias:**

1. Atualizar `LAYERS` para reconhecer os novos caminhos sem prefixos numéricos (`foundation`, `domain`, `product`, `architecture`, `implementation`, `governance`, `audits`).
2. Suportar subdiretórios por bounded context (`domain/platform/aggregates/`, `domain/credit/entities/`, etc.).
3. Mapear tipos de documento (aggregate, entity, rule, etc.) para a nova estrutura.
4. Validar que `docs/handoffs/HANDOFF-VIGENTE.md` não existe mais.
5. Validar que `docs/implementationplans/` e arquivos corrompidos não existem.
6. Manter compatibilidade com estrutura antiga durante a Fase 0-2 (modo transicional).
7. Não exigir camadas de evolução futura (`engineering`, `operations`, `references`, `context-maps`, `rfcs`, `index.json`).

## 8.2 `package.json`

**Mudanças necessárias:**

- Nenhuma, se `docs:validate` continuar apontando para `scripts/validate-docs.js`.
- Índice automático (`docs:index`) é evolução futura.

## 8.3 `.gitignore`

**Mudanças necessárias:**

- Adicionar `/graphify-out/` e `/docs/graphify-out/`.

---

# 9. A Migração Pode Ocorrer em Uma Única Etapa?

**Não.**

A migração envolve dezenas de documentos, reestruturação de camadas, atualização de scripts e validação. Executar em uma única etapa:

- Aumenta o risco de erros silenciosos.
- Dificulta o rollback.
- Pode deixar `docs:validate` quebrado por tempo indeterminado.
- Aumenta a chance de conflitos com outros agentes.

A migração deve ocorrer em **fases bem definidas**, com critérios de conclusão e rollback independentes.

---

# 10. Fases da Migração

## Fase 0 — Preparação

**Objetivo:** criar ambiente isolado e seguro para a migração.

**Documentos afetados:** nenhum (apenas infraestrutura do repo).

**Ações:**

1. Garantir que todos os commits do EPIC-001 e do AMP/DISCOVERY/MANIFEST estejam na `main`.
2. Criar branch `docs/migration-2026-08-04` a partir de `main`.
3. Comunicar congelamento documental: nenhum agente deve modificar `docs/` neste branch até a conclusão.
4. Executar `npm run docs:validate` e `uv run pytest` na `main` e confirmar que estão verdes.
5. Identificar links relativos entre documentos: `rg '\]\([^#)]' docs/ --type md`.
6. Criar backup local: `git clone . /tmp/emprestimo-backup` (opcional, mas recomendado).

**Risco:** baixo.

**Rollback:** deletar o branch e recriar.

**Critério de conclusão:** branch criado, validações verdes na main, congelamento comunicado.

---

## Fase 1 — Higiene (remoção de duplicatas e artefatos)

**Objetivo:** remover documentos/artefatos que não devem existir na arquitetura alvo.

**Documentos afetados:**

- `docs/implementationplans/` (pasta inteira)
- `docs/implementation/plansPLAN-002-epic-001-tenant-management.md`
- `docs/handoffs/HANDOFF-VIGENTE.md`
- `docs/graphify-out/` (pasta inteira)
- `.gitkeep` desnecessários

**Ações:**

1. `git rm -r docs/implementationplans/`
2. `git rm docs/implementation/plansPLAN-002-epic-001-tenant-management.md`
3. `git rm docs/handoffs/HANDOFF-VIGENTE.md`
4. Mover `docs/graphify-out/` para fora do repo (ex.: `.graphify-out/` na raiz) ou `git rm -r docs/graphify-out/` e adicionar a `.gitignore`.
5. Remover `.gitkeep` desnecessários:
   - `docs/implementation/api/.gitkeep`
   - `docs/implementation/architecture/.gitkeep`
   - `docs/implementation/database/.gitkeep`
   - `docs/implementation/testing/.gitkeep`
   - `docs/domain/aggregates/.gitkeep`
   - `docs/domain/entities/.gitkeep`
   - `docs/domain/events/.gitkeep`
   - `docs/domain/glossary/.gitkeep`
   - `docs/domain/rules/.gitkeep`
   - `docs/domain/services/.gitkeep`
   - `docs/domain/value-objects/.gitkeep`
6. Commit: `git commit -m "Fase 1: higiene — remover duplicatas, artefatos e ponteiros de máquina"`

**Risco:** médio. Remover o ponteiro `HANDOFF-VIGENTE.md` pode quebrar scripts/agents que dependem dele. Verificar se `~/HANDOFF-VIGENTE.md` já aponta para o handoff datado.

**Rollback:** `git revert <commit-da-fase-1>`.

**Critério de conclusão:** `docs:validate` ainda passa (sem erros); `git status` mostra apenas remoções esperadas.

---

## Fase 2 — Criação da Nova Estrutura

**Objetivo:** criar a árvore de diretórios da arquitetura alvo mínima e o `docs/README.md`.

**Documentos afetados:** nenhum (apenas diretórios vazios e `docs/README.md`).

**Ações:**

1. Criar todas as pastas listadas na seção 3.
2. Criar `docs/README.md` com mapa de navegação mínimo.
3. Opcionalmente adicionar `.gitkeep` nas pastas que ainda não terão documentos.
4. Commit: `git commit -m "Fase 2: criar estrutura alvo mínima da arquitetura documental"`

**Risco:** baixo.

**Rollback:** `git revert <commit-da-fase-2>`.

**Critério de conclusão:** `git status` mostra apenas novos diretórios e `README.md`; nenhum documento movido ainda.

---

## Fase 3 — Movimentação Física (git mv)

**Objetivo:** mover todos os documentos para a nova estrutura.

**Documentos afetados:** todos os documentos markdown com conteúdo (exceto templates/assets/ux, que permanecem no local atual).

**Ações:**

1. Executar as movimentações listadas em `docs/architecture/amp/DOCUMENT-ARCHITECTURE-MANIFEST.md`.
2. Mover Foundation: `git mv docs/foundation/*.md docs/foundation/` (caminho inalterado, apenas ajuste se necessário).
3. Mover Domain por contexto: `git mv docs/domain/aggregates/DOMAIN-001-aggregate-carteira.md docs/domain/credit/aggregates/`, etc.
4. Mover Product por contexto: `git mv docs/product/capabilities/*.md docs/product/platform/capabilities/`, etc.
5. Mover Architecture: `git mv docs/decisions/*.md docs/architecture/adrs/`, etc.
6. Mover Implementation: `git mv docs/implementation/plans/PLAN-001-*.md docs/implementation/plans/`; `git mv docs/implementation/plans/PLAN-002-execution-backlog.md docs/implementation/backlogs/`; `git mv docs/implementation/plans/PEDIDO-ORIENTACAO-*.md docs/governance/decision-requests/`.
7. Mover Governance: handoffs.
8. Mover Auditorias/Discoveries: `docs/auditorias/` → `docs/audits/audits/`; `docs/discoveries/` → `docs/audits/discoveries/`.
9. Commit: `git commit -m "Fase 3: mover documentos para arquitetura alvo (git mv)"`

**Risco:** alto. Qualquer caminho errado pode quebrar a migração.

**Rollback:** `git revert <commit-da-fase-3>` ou `git checkout HEAD~1 -- docs/`.

**Critério de conclusão:** todos os documentos úteis estão nos novos locais; `git status` não mostra documentos não-rastreados em `docs/`. Nenhuma duplicata.

---

## Fase 4 — Atualização de Scripts

**Objetivo:** atualizar `scripts/validate-docs.js` e `.gitignore` para a nova estrutura.

**Documentos afetados:** `scripts/validate-docs.js`, `.gitignore`.

**Ações:**

1. Atualizar `LAYERS` e mapeamento de templates para reconhecer os novos caminhos.
2. Garantir que `docs:validate` passe na nova estrutura.
3. Adicionar `/graphify-out/` e `/docs/graphify-out/` a `.gitignore`.
4. Commit: `git commit -m "Fase 4: atualizar scripts/validate-docs.js para nova estrutura"`

**Risco:** médio. Erros no validador podem ser difíceis de diagnosticar.

**Rollback:** `git revert <commit-da-fase-4>`.

**Critério de conclusão:** `npm run docs:validate` retorna 0 erros. Os avisos existentes (referências a IDs futuros) permanecem aceitáveis.

---

## Fase 5 — Validação Final

**Objetivo:** garantir que todo o sistema (documentação + código) está íntegro.

**Documentos afetados:** todos.

**Ações:**

1. Executar `npm run docs:validate`.
2. Executar `uv run pytest`.
3. Executar `uv run ruff check src tests`.
4. Executar `uv run black --check src tests`.
5. Executar `uv run mypy src`.
6. Verificar que `git status` está limpo (apenas commits planejados).
7. Commit: `git commit -m "Fase 5: validação final da migração documental"` (se houver ajustes).

**Risco:** baixo.

**Rollback:** `git revert <commit-da-fase-5>`.

**Critério de conclusão:** todas as validações passam; nenhum documento órfão; nenhum link quebrado.

---

## Fase 6 — Merge, Congelamento e Handoff

**Objetivo:** integrar a migração na `main` e comunicar o novo estado.

**Documentos afetados:** `docs/governance/handoffs/2026-08-04-handoff-sessao-epic-001-tenant-management-fechado.md` (atualização).

**Ações:**

1. Atualizar o handoff com a informação de que a migração documental foi concluída.
2. Criar PR/MR para `main` (se houver fluxo de PR) ou merge direto.
3. Atualizar `~/HANDOFF-VIGENTE.md` para apontar para o novo handoff.
4. Commit: `git commit -m "Fase 6: concluir migração da arquitetura documental"`

**Risco:** médio. Merge pode gerar conflitos se outros agentes ignorarem o congelamento.

**Rollback:** `git revert` ou `git reset --hard HEAD~N` no branch; reverter merge na `main` se necessário.

**Critério de conclusão:** `main` contém a nova estrutura; `docs:validate` passa; `uv run pytest` passa.

---

# 11. Mudanças que NÃO Devem Ser Feitas Agora

| Mudança | Por que não agora | Quando |
|---------|-------------------|--------|
| Renomear IDs dos documentos | Quebraria rastreabilidade. | Nunca, salvo exceção formal. |
| Alterar conteúdo dos documentos | Migração é sobre estrutura, não conteúdo. | Após migração, em tasks separadas. |
| Criar documentos novos | Congelamento documental. | Após migração. |
| Introduzir front matter YAML em todos os docs | Melhoria documental; amplia o escopo. | Task separada. |
| Criar `docs/index.json` | Depende de front matter ou parsing. | Task separada. |
| Reorganizar `src/` | Fora do escopo documental. | Task separada. |
| Mover `tests/` | Fora do escopo. | Task separada. |
| Decidir ADR-003 (Multi-tenant) | Decisão arquitetural, não migração física. | Architecture Review separada. |
| Criar camadas `engineering/`, `operations/`, `references/` | Evolução arquitetural; requer ADRs. | Após migração. |
| Criar `architecture/context-maps/` / `rfcs/` | Evolução; requer propostas formais. | Após migração. |
| Dividir `FOUNDATION-002` | Refatoração de conteúdo; não é migração física. | Task separada. |
| Criar `glossary.md` | Refatoração; depende de decisão sobre glossário. | Task separada. |
| Atualizar conteúdo de templates | Refatoração; pode introduzir inconsistências. | Task separada. |
| Criar novos templates (RFC, Standard, Runbook, Playbook) | Evolução. | Task separada. |
| Mover `templates/`, `assets/`, `ux/` para `references/` | Evolução futura. | Task separada. |

---

# 12. Mudanças que Exigem Nova ADR vs. Não Exigem

## Não exigem nova ADR

- Reorganização física de arquivos em `docs/`.
- Separação de planos e backlogs.
- Mudança de categoria de auditorias/reviews.
- Remoção de duplicatas e arquivos corrompidos.
- Movimentação de templates, assets e UX (mantidos no local atual).

## Exigem nova ADR (quando forem implementadas)

- Introdução de camadas de **Security** com decisões de controles.
- Decisão de **CI/CD** e deployment strategy.
- Decisão de **Observability** e logging.
- Decisão de **Multi-tenant nível 2/3** (ADR-003).
- Decisão de **Event Bus / Mensageria**.
- Decisão de **API Pública**.
- Decisão de **Read Models / Caching**.
- Decisão de **AI / Agentes** na documentação.

**Nota:** a migração documental em si **não cria ADRs**. Ela apenas prepara o terreno para que futuras ADRs vivam em `docs/architecture/adrs/`.

---

# 13. Risco para os Agentes SDD e Mitigação

## Riscos

1. **Leitura de documentos em locais antigos.** Agentes podem tentar acessar `docs/domain/...` e falhar.
2. **Handoff quebrado.** Se `~/HANDOFF-VIGENTE.md` não for atualizado, o agente não encontra o handoff vigente.
3. **Validador falhando.** Se `docs:validate` não for atualizado, a migração fica bloqueada.
4. **Templates ausentes.** Se templates forem movidos mas a referência no validador não for atualizada, documentos novos podem não validar.
5. **Conflitos de branch.** Outro agente pode modificar `docs/` na `main` durante a migração.

## Mitigações

1. **Congelamento documental.** Comunicar explicitamente que nenhum agente deve alterar `docs/` durante a migração.
2. **Branch isolado.** Trabalhar exclusivamente em `docs/migration-2026-08-04`.
3. **Criar `docs/README.md` na Fase 2.** Fornece mapa de navegação para agentes.
4. **Atualizar `~/HANDOFF-VIGENTE.md` na Fase 6.** Garante que o ponteiro aponte para o handoff correto.
5. **Manter `docs:validate` passando.** Não deixar o validador quebrado por mais de uma fase.
6. **Testar com agente leitor.** Após a migração, simular consulta por um agente para garantir que todos os documentos são encontráveis.

---

# 14. Fluxo do Agent Loop Após a Reorganização

```
EPIC concluído
        │
        ▼
Architecture Review
        │
        ▼
Architecture Master Plan (AMP)
        │
        ▼
Document Architecture Discovery
        │
        ▼
Document Architecture Migration Plan
        │
        ▼
Document Architecture Manifest
        │
        ▼
Autorização
        │
        ▼
Execução da Migração Documental (branch isolado)
        │
        ▼
Congelamento da nova arquitetura documental
        │
        ▼
Atualização da Governança
        │
        ▼
Novo EPIC
        │
        ▼
SDD + Agent Loop
```

## Novo fluxo do agente durante execução

1. **Início da sessão:**
   - Verificar `~/HANDOFF-VIGENTE.md` para estado do projeto.
   - Ler `docs/README.md` para navegação.

2. **Leitura de fontes oficiais:**
   - `docs/foundation/` → visão, escopo, princípios.
   - `docs/domain/<context>/` → modelos DDD.
   - `docs/product/<context>/` → capabilities, épicos, features, US.
   - `docs/architecture/` → AMP, ADRs, reviews.
   - `docs/implementation/` → planos e backlogs.
   - `docs/governance/` → decision requests, handoffs.
   - `docs/audits/` → auditorias e descobertas.

3. **Validação:**
   - Executar `npm run docs:validate` antes de qualquer commit.

4. **Escrita:**
   - Criar novos documentos no local correto segundo a categoria.
   - Usar templates em `docs/templates/`.

5. **Handoff:**
   - Atualizar `docs/governance/handoffs/<data>-handoff-...md`.
   - Atualizar `~/HANDOFF-VIGENTE.md` para apontar ao novo handoff.

---

# 15. Cronograma Executivo

| Fase | Duração estimada | Dependências | Responsável sugerido |
|------|------------------|--------------|----------------------|
| Fase 0 — Preparação | 1h | AMP-001, DISCOVERY, MANIFEST aprovados | Migration Architect |
| Fase 1 — Higiene | 1h | Fase 0 | Migration Architect |
| Fase 2 — Criar estrutura | 30min | Fase 1 | Migration Architect |
| Fase 3 — Mover documentos | 2-3h | Fase 2 | Migration Architect |
| Fase 4 — Atualizar scripts | 2-4h | Fase 3 | Migration Architect + Engenharia |
| Fase 5 — Validação final | 1h | Fase 4 | Migration Architect |
| Fase 6 — Merge e handoff | 1h | Fase 5 | Migration Architect |

**Total estimado:** 1 a 2 dias de trabalho focado.

**Melhor momento:** imediatamente após aprovação deste plano, **antes do início do EPIC-002**.

---

# 16. Decisão do Arquiteto sobre o Momento Ideal

## Recomendação

**Iniciar a migração imediatamente após a aprovação deste plano e do MANIFEST.**

## Justificativa

1. **A base documental ainda é pequena.** ~50 documentos com conteúdo são gerenciáveis.
2. **Não há EPIC em andamento.** O congelamento documental não bloqueia nenhuma entrega funcional.
3. **O EPIC-002 depende da documentação.** Iniciar Cadastro de Devedores sem a estrutura documental correta acumularia dívida.
4. **O risco de esperar aumenta.** Novos documentos (ADRs, discoveries, auditorias) continuarão sendo criados na estrutura antiga, aumentando o custo da migração.
5. **A migração é reversível.** Cada fase possui rollback claro.

## Condições para NÃO iniciar

- Se houver um EPIC funcional em andamento.
- Se o time de Engenharia não puder dedicar tempo para atualizar `scripts/validate-docs.js`.
- Se a aprovação deste plano e do MANIFEST não forem obtidas.

## Condição para autorização

Aprovar este plano **e** o MANIFEST **e** garantir que nenhum agente modifique `docs/` durante a execução.

---

# 17. Lista de Ações Detalhadas para Execução

## Fase 0

1. `git checkout main`
2. `git pull`
3. `git status` deve estar limpo.
4. `npm run docs:validate` → confirmar 0 erros.
5. `uv run pytest` → confirmar pass.
6. `git checkout -b docs/migration-2026-08-04`
7. `rg '\]\([^#)]' docs/ --type md` → salvar lista de links relativos.
8. Comunicar congelamento documental.

## Fase 1

1. `git rm -r docs/implementationplans/`
2. `git rm docs/implementation/plansPLAN-002-epic-001-tenant-management.md`
3. `git rm docs/handoffs/HANDOFF-VIGENTE.md`
4. `git rm -r docs/graphify-out/`
5. `git rm docs/implementation/api/.gitkeep`
6. `git rm docs/implementation/architecture/.gitkeep`
7. `git rm docs/implementation/database/.gitkeep`
8. `git rm docs/implementation/testing/.gitkeep`
9. `git rm docs/domain/aggregates/.gitkeep`
10. `git rm docs/domain/entities/.gitkeep`
11. `git rm docs/domain/events/.gitkeep`
12. `git rm docs/domain/glossary/.gitkeep`
13. `git rm docs/domain/rules/.gitkeep`
14. `git rm docs/domain/services/.gitkeep`
15. `git rm docs/domain/value-objects/.gitkeep`
16. `git commit -m "Fase 1: higiene da documentação"`
17. `npm run docs:validate` → confirmar 0 erros.

## Fase 2

1. Criar diretórios listados na seção 3.
2. Criar `docs/README.md`.
3. `git add docs/`
4. `git commit -m "Fase 2: criar estrutura alvo mínima da documentação"`

## Fase 3

1. Mover todos os documentos conforme tabela do MANIFEST usando `git mv`.
2. Verificar que não há documentos órfãos em `docs/`.
3. `git status` para conferir.
4. `git commit -m "Fase 3: mover documentos para estrutura alvo"`

## Fase 4

1. Atualizar `scripts/validate-docs.js`:
   - Mapear `foundation`, `domain`, `product`, `architecture`, `implementation`, `governance`, `audits`.
   - Mapear subdiretórios por contexto (`platform`, `credit`).
   - Mapear tipos de documento (`aggregates`, `entities`, `rules`, etc.).
   - Validar ausência de `docs/handoffs/HANDOFF-VIGENTE.md`.
   - Validar ausência de `docs/implementationplans/`.
   - Validar ausência de arquivos corrompidos.
2. Atualizar `.gitignore`:
   - `/graphify-out/`
   - `/docs/graphify-out/`
3. `git add scripts/validate-docs.js .gitignore`
4. `git commit -m "Fase 4: atualizar validador para nova estrutura"`
5. `npm run docs:validate` → confirmar 0 erros.

## Fase 5

1. `npm run docs:validate`
2. `uv run pytest`
3. `uv run ruff check src tests`
4. `uv run black --check src tests`
5. `uv run mypy src`
6. Corrigir eventuais problemas.
7. Commit.

## Fase 6

1. Atualizar handoff com informação da migração.
2. `git add docs/governance/handoffs/...`
3. `git commit -m "Fase 6: handoff da migração documental"`
4. `git checkout main`
5. `git merge docs/migration-2026-08-04` (ou abrir PR/MR).
6. Atualizar `~/HANDOFF-VIGENTE.md`.
7. Deletar branch antigo após merge.

---

# 18. Referências

- `DOCUMENT-ARCHITECTURE-DISCOVERY.md`
- `DOCUMENT-ARCHITECTURE-MANIFEST.md`
- `AMP-001-architecture-master-plan.md`
- `PLAN-001`, `PLAN-002`
- `ADR-001`, `ADR-002`
- Estrutura física atual de `docs/`

---

# 19. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-04 | Plano de migração da arquitetura documental com fases, riscos, rollback e cronograma. |
| 1.1.0 | 2026-08-04 | Revisão arquitetural: arquitetura alvo mínima; remoção da Fase 5 (refatoração de conteúdo); separação de migração e evolução; templates/assets/ux mantidos no local atual; camadas sem prefixos numéricos; criação do MANIFEST. |

---

**Nota de encerramento:** Este documento é um plano de execução. Nenhuma mudança foi realizada. Nenhum arquivo foi movido, renomeado, alterado ou removido. Nenhum código foi implementado. Nenhuma ADR, Foundation, Product ou Feature foi criada. Aguardando autorização para executar a migração.
