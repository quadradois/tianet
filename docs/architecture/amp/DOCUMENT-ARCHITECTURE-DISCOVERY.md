# DOCUMENT-ARCHITECTURE-DISCOVERY — Descoberta da Arquitetura Documental

**ID:** DOCUMENT-ARCHITECTURE-DISCOVERY

**Versão:** 1.0.0

**Status:** Rascunho para revisão

**Data:** 2026-08-04

**Autor:** Principal Software Architect / Documentation Architect / CTO / Software Knowledge Engineer

---

# 1. Resumo Executivo

A base documental da TiaNet atingiu um nível de maturidade que já não é mais suportado naturalmente pela estrutura física atual. O EPIC-001 foi entregue com 70+ documentos distribuídos entre Foundation, Domain, Product, Discoveries, Decisions, Implementation, Handoffs, Auditorias e Architecture. A qualidade dos conteúdos é alta, mas a arquitetura da documentação apresenta sinais de estresse: duplicações físicas, categorias misturadas, ausência de camadas de governança, engineering e operations, e dependências documentais que dificultarão a navegação de múltiplos times, bounded contexts e agentes.

## Posição do Documentation Architect

A estrutura atual **suporta o próximo EPIC**, mas **não suporta cinco anos de crescimento** sem reestruturação. A taxonomia `Foundation → Domain → Product → Implementation → Handoff` é correta para o ciclo de entrega, mas é insuficiente para uma plataforma de ecossistema. Precisamos evoluir para uma arquitetura documental com camadas de **Architecture, Engineering, Governance, Audits, Standards, Operations e References**, organizadas por bounded context e produto, com metadados claros e validação automática.

---

# 2. Inventário da Documentação

## 2.1 Estrutura física atual

```
docs/
├── architecture/
│   └── AMP-001-architecture-master-plan.md
├── assets/
│   ├── diagrams/
│   └── images/
├── auditorias/
│   ├── auditoria-as-is-to-be-ecossistema.md
│   ├── discovery-adr-003-multi-tenant.md
│   └── raio-x-arquitetural-ecossistema.md
├── decisions/
│   ├── ADR-001-stack-tecnologica-oficial-mvp.md
│   └── ADR-002-auditoria-independente-da-transacao.md
├── discoveries/
│   ├── FEATURE-002-consultar-tenant-discovery.md
│   ├── FEATURE-003-atualizar-tenant-discovery.md
│   └── FEATURE-004-inativar-tenant-discovery.md
├── domain/
│   ├── aggregates/
│   ├── entities/
│   ├── events/
│   ├── glossary/
│   ├── rules/
│   ├── services/
│   └── value-objects/
├── foundation/
│   ├── FOUNDATION-001-product-vision.md
│   ├── FOUNDATION-002-modelo-de-dominio-e-linguagem-ubiqua.md
│   ├── FOUNDATION-003-mapa-do-dominio.md
│   ├── FOUNDATION-004-core-domain.md
│   ├── FOUNDATION-005-inventario-do-dominio.md
│   ├── FOUNDATION-006-arquitetura-multi-tenant.md
│   ├── FOUNDATION-007-product-map.md
│   └── FOUNDATION-008-mvp-scope.md
├── handoffs/
│   ├── 2026-08-04-handoff-sessao-epic-001-tenant-management-fechado.md
│   └── HANDOFF-VIGENTE.md
├── implementation/
│   ├── api/
│   ├── architecture/
│   ├── database/
│   ├── plans/
│   │   ├── PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md
│   │   ├── PLAN-001-execution-backlog.md
│   │   ├── PLAN-001-feature-001-tenant-provisioning.md
│   │   ├── PLAN-002-epic-001-tenant-management.md
│   │   ├── PLAN-002-execution-backlog.md
│   │   └── plansPLAN-002-epic-001-tenant-management.md
│   ├── plansPLAN-002-epic-001-tenant-management.md
│   └── testing/
├── implementationplans/
│   └── PLAN-002-epic-001-tenant-management.md
├── product/
│   ├── capabilities/
│   ├── epics/
│   ├── features/
│   └── user-stories/
├── templates/
│   ├── adr-template.md
│   ├── aggregate-template.md
│   ├── business-rule-template.md
│   ├── domain-event-template.md
│   ├── domain-service-template.md
│   ├── entity-template.md
│   ├── epic-template.md
│   ├── feature-template.md
│   ├── foundation-template.md
│   ├── implementation-plan-template.md
│   ├── mermaid-template.md
│   ├── user-story-template.md
│   └── value-object-template.md
├── graphify-out/
└── ux/
    └── wireframes/
```

## 2.2 Contagem por camada

| Camada | Documentos úteis | Templates/placeholder | Observação |
|--------|------------------|----------------------|------------|
| Foundation | 8 | — | Fonte de verdade estratégica. |
| Domain | 18 | 6 `.gitkeep` | Modelagem DDD completa. |
| Product | 13 | — | Capabilities, épicos, features, user stories. |
| Decisions | 2 | — | ADRs oficiais. |
| Implementation | 5 | 4 `.gitkeep` | Planos técnicos e backlogs. |
| Discoveries | 3 | — | Descobertas de features. |
| Auditorias | 3 | — | Auditorias e uma discovery. |
| Handoffs | 2 | — | Ponteiro + handoff datado. |
| Architecture | 1 | — | AMP-001. |
| Templates | 13 | — | Padrões de documentos. |
| Assets/UX | — | — | Diagramas e wireframes. |
| graphify-out | — | — | Cache de ferramenta. |

**Total de documentos markdown com conteúdo:** ~57.

---

# 3. Mapa das Responsabilidades

## 3.1 Responsabilidades por camada

| Camada | Responsabilidade | Audiência principal |
|--------|------------------|---------------------|
| **Foundation** | Por que o produto existe, quem serve, princípios, escopo, linguagem ubíqua, mapa de domínio, core domain. | Executivo, Product, CTO, novos membros. |
| **Domain** | O que o sistema é — modelos DDD, invariantes, regras, eventos, value objects. | Domain Experts, Engenharia, Agentes. |
| **Product** | O que entregar — capabilities, épicos, features, user stories, critérios de aceitação. | Product, Designers, QA, Engenharia. |
| **Architecture** | Como evoluir — AMP, ADRs, context maps, RFCs, visão de longo prazo. | Architects, CTO, Tech Leads. |
| **Implementation** | Como executar — planos técnicos, backlogs, sequência de implementação, riscos. | Engenharia, Agentes. |
| **Decisions** | Decisões arquiteturais aprovadas. | Todos. |
| **Discoveries** | Hipóteses, descobertas, análises de viabilidade. | Architects, Product, Analysts. |
| **Auditorias** | Revisões, raio-x, as-is/to-be. | Architects, CTO, Governance. |
| **Handoffs** | Estado do projeto entre sessões. | Engenharia, Agentes. |
| **Templates** | Padrões de documentos. | Todos. |

## 3.2 Documentos com responsabilidade excessiva

| Documento | Problema | Justificativa |
|-----------|----------|---------------|
| `FOUNDATION-002-modelo-de-dominio-e-linguagem-ubiqua.md` | 260 linhas; mistura definições de linguagem ubíqua com termos de todos os contextos. | Deveria ser acompanhado de um glossário operacional por contexto. |
| `FOUNDATION-005-inventario-do-dominio.md` | Tabela global de conceitos. | Sobreposição parcial com FOUNDATION-002; deveria ser gerado a partir do Domain ou viver como glossary. |
| `PLAN-002-epic-001-tenant-management.md` | Plano técnico + situação atual + decisões de arquitetura + API + riscos. | Conteúdo válido, mas camadas estão condensadas. A separação com PLAN-002-EXEC é um bom início. |
| `docs/auditorias/raio-x-arquitetural-ecossistema.md` | Arquitetura review + as-is/to-be + recomendações. | Natureza arquitetural, não de auditoria operacional. |
| `docs/auditorias/discovery-adr-003-multi-tenant.md` | Discovery de decisão arquitetural. | Está na pasta errada; deveria estar em `discoveries/` ou `decisions/`. |

---

# 4. Mapa de Dependências

## 4.1 Dependências diretas observadas

```
Foundation
    │
    ├──→ Domain (terminologia, contextos, core domain)
    │
    ├──→ Product (product map, escopo do MVP)
    │
    └──→ Architecture (AMP usa Foundation como fonte)

Domain
    │
    ├──→ Product (features/US dependem de modelos de domínio)
    │
    └──→ Implementation (planos usam DOMAIN-XXX)

Product
    │
    └──→ Implementation (PLANs implementam EPICs/FEATUREs)

Implementation
    │
    ├──→ Decisions (ADRs)
    │
    └──→ Handoffs (estado de entrega)

Auditorias / Discoveries
    │
    └──→ Todos (analisam Foundation, Domain, Product, Implementation, Code)

Architecture (AMP-001)
    │
    └──→ Todos (sintetiza visão de longo prazo)
```

## 4.2 Dependências perigosas

| Dependência | Risco | Por quê |
|-------------|-------|---------|
| Implementation → Foundation/Domain direto | Acoplamento de execução à estratégia | Mudanças em Foundation/Domain forçam retrabalho em planos. |
| Auditorias/Discoveries → todos os níveis | Análises ficam obsoletas rapidamente | Sem versionamento claro, auditorias antigas viram "verdade atrasada". |
| Handoffs como ponteiro físico | `HANDOFF-VIGENTE.md` mistura conteúdo com estado de máquina | Documento de repo apontando para outro documento cria circularidade. |
| Discoveries dentro de `auditorias/` | Categoria errada | Dificulta descoberta e validação documental. |
| Planos de decisão em `implementation/plans/` | `PEDIDO-ORIENTACAO-IMP-033` é um pedido de decisão, não um plano | Polui a camada de implementação com artefatos de governança. |

---

# 5. Resposta às 15 Perguntas Obrigatórias

## 5.1 A organização atual da pasta `docs/` continua adequada?

**Não para cinco anos.**

A estrutura atual é adequada para um único produto, poucos bounded contexts e um único time. No entanto, ela já apresenta estresse com apenas um EPIC concluído:

- Pastas de `implementation` contêm planos, backlogs e um pedido de orientação misturados.
- `auditorias/` contém uma discovery.
- Existem duplicações físicas (`implementationplans/`, `implementation/plansPLAN-...`).
- `graphify-out/` é um artefato de ferramenta, não documentação.
- `ux/` e `assets/` estão subutilizados e sem integração clara.

A organização precisa evoluir para uma estrutura namespaceada por contexto/produto e por camada documental.

## 5.2 Existe excesso de camadas? Existe falta de camadas?

**Excesso:** não. As camadas existentes são todas justificadas.

**Falta:** sim. Faltam camadas obrigatórias para uma plataforma em crescimento:

- **Engineering** — CI/CD, observability, infraestrutura, logs, métricas.
- **Governance** — processos, aprovações, decision requests, RFCs, handoffs.
- **Standards** — padrões de API, código, testes, documentação, commits.
- **Security** — ameaças, controles, políticas de segurança.
- **Operations** — runbooks, playbooks, SOPs, incident response.
- **References** — templates, glossary, assets, UX, bibliografia.
- **Integrations** — mapa de integrações, adapters, contratos externos.

## 5.3 Existem documentos duplicando responsabilidades? Quais? Por quê?

**Sim.**

| Documentos | Natureza da duplicação | Por quê |
|------------|------------------------|---------|
| `FOUNDATION-002` e `FOUNDATION-005` | Linguagem ubíqua × inventário de conceitos | Ambos definem conceitos. FOUNDATION-005 é uma tabela de mapeamento; poderia ser `references/glossary.md` ou gerado a partir do Domain. |
| `PLAN-002-epic-001` e `PLAN-002-execution-backlog` | Plano técnico × backlog | A separação é válida, mas ambos contêm repetições de escopo, API e riscos. |
| `docs/implementation/plans/PLAN-002-epic-001-tenant-management.md` e `docs/implementationplans/PLAN-002-epic-001-tenant-management.md` | **Duplicação física real** | Pasta `implementationplans/` é um erro de nome; arquivo idêntico. |
| `docs/implementation/plansPLAN-002-epic-001-tenant-management.md` | **Arquivo corrompido** | Nome colado com `plansPLAN-...`; provavelmente cópia acidental. |
| `docs/auditorias/discovery-adr-003-multi-tenant.md` e `docs/discoveries/*` | Discovery em pasta errada | Deveria estar em `discoveries/` ou `decisions/` (como descoberta de ADR). |

## 5.4 Quais documentos deveriam ser promovidos?

| Documento | De | Para | Motivo |
|-----------|----|------|--------|
| `AMP-001` | `architecture/` | `architecture/` (já está) | Confirmar como documento de referência estratégica. |
| `auditoria-as-is-to-be-ecossistema.md` | `auditorias/` | `architecture/reviews/` ou `governance/audits/` | É uma arquitetura review, não auditoria operacional. |
| `raio-x-arquitetural-ecossistema.md` | `auditorias/` | `architecture/reviews/` | É um raio-x arquitetural. |
| `discovery-adr-003-multi-tenant.md` | `auditorias/` | `discoveries/` ou `decisions/discoveries/` | É uma descoberta, não uma auditoria. |
| `PEDIDO-ORIENTACAO-IMP-033` | `implementation/plans/` | `governance/decision-requests/` | É um artefato de governança, não de implementação. |
| `HANDOFF-VIGENTE.md` | `docs/handoffs/` | `~/HANDOFF-VIGENTE.md` (fora do repo) | É um ponteiro de máquina/local; não deveria versionar estado da sessão. |

## 5.5 Existe alguma categoria documental que inevitavelmente surgirá?

**Sim. As seguintes categorias são inevitáveis:**

- **Standards** — padrões de código, API, documentação, testes, commits.
- **Engineering** — CI/CD, observability, infraestrutura, pipelines.
- **Governance** — processos, aprovações, decision requests, RFCs, handoffs.
- **Security** — ameaças, controles, políticas, compliance.
- **Operations** — runbooks, playbooks, SOPs, incident response.
- **Integrations** — adapters, contratos externos, mapeamento de integrações.
- **AI** — diretrizes de uso de agentes/IA, prompt engineering, governança de IA.
- **RFC** — propostas de mudança arquitetural.
- **References** — glossary, templates, assets, UX, bibliografia.

## 5.6 O fluxo Foundation → Domain → Product → Implementation → Handoff continua suficiente?

**Não.**

Esse fluxo é suficiente para o ciclo de entrega de uma feature, mas insuficiente para uma plataforma. Faltam camadas de feedback, governança e arquitetura:

```
Foundation
    ↓
Domain
    ↓
Product
    ↓
Architecture
    ↓
Engineering
    ↓
Implementation
    ↓
Governance
    ↓
Audits
    ↓
Operations
    ↓
Handoffs (estado)
```

Além disso, o fluxo atual é linear. A realidade é cíclica: auditorias e handoffs alimentam Foundation e Architecture.

## 5.7 A documentação suporta naturalmente múltiplos produtos, bounded contexts, times e agentes?

**Não naturalmente.**

A estrutura atual usa IDs globais (DOMAIN-NNN, FEATURE-NNN, US-NNN) sem namespace por contexto. Com múltiplos bounded contexts, a numeração global se torna rígida e difícil de navegar.

Para suportar múltiplos contextos, times e agentes, a documentação precisa de:

- **Namespace por contexto/produto** (ex.: `domain/credit/`, `domain/platform/`, `domain/cobranca/`).
- **Metadados estruturados** (front matter YAML) em cada documento.
- **Índice machine-readable** (`docs-index.json` ou similar) para agentes.
- **Templates por categoria**, não apenas por tipo de documento DDD/Product.
- **Cross-references validadas** (já existe parcialmente via `docs:validate`).

## 5.8 Quais documentos possuem responsabilidade excessiva?

1. `FOUNDATION-002` — linguagem ubíqua de toda a plataforma em um único arquivo.
2. `FOUNDATION-005` — inventário global de conceitos.
3. `PLAN-002-epic-001` — plano técnico + decisões + API + riscos.
4. `auditoria-as-is-to-be-ecossistema.md` — auditoria + arquitetura review + roadmap.
5. `raio-x-arquitetural-ecossistema.md` — análise profunda + recomendações + descobertas.

## 5.9 Quais documentos deveriam ser divididos?

1. `FOUNDATION-002` — separar em:
   - `FOUNDATION-002` — Linguagem Ubíqua (princípios e diretrizes)
   - `references/glossary.md` — Glossário operacional por contexto
2. `PLAN-002-epic-001` — separar em:
   - `PLAN-002` — Plano técnico consolidado
   - `PLAN-002-EXEC` — Backlog de execução (já existe)
   - `architecture/adr-candidates/DA-201-205.md` — Decisões de arquitetura (DA-201 a DA-205)
3. `auditoria-as-is-to-be-ecossistema.md` — separar em:
   - `architecture/reviews/as-is.md`
   - `architecture/reviews/to-be.md`
   - `governance/audits/findings.md`
4. `raio-x-arquitetural-ecossistema.md` — separar em:
   - `architecture/reviews/raio-x-arquitetural.md`
   - `architecture/reviews/recommendations.md`

## 5.10 Quais documentos poderiam desaparecer?

1. `docs/implementationplans/` — pasta duplicada/errada.
2. `docs/implementation/plansPLAN-002-epic-001-tenant-management.md` — arquivo corrompido.
3. `docs/auditorias/discovery-adr-003-multi-tenant.md` — mover para categoria correta.
4. `docs/handoffs/HANDOFF-VIGENTE.md` — mover para fora do repo (ponteiro local).
5. `docs/graphify-out/` — cache de ferramenta; deve ser ignorado ou movido para fora de `docs/`.
6. `docs/implementation/api/.gitkeep`, `architecture/.gitkeep`, `database/.gitkeep`, `testing/.gitkeep` — placeholders sem função clara.
7. `docs/domain/glossary/.gitkeep` — a pasta `glossary` está vazia; se não for usada, remover.

## 5.11 Existe uma ordem melhor para navegação da documentação? Propor uma árvore.

**Proposta de arquitetura documental alvo (ordenada por camada):**

```
docs/
├── 00-foundation/              # Visão, escopo, princípios, linguagem ubíqua
│   ├── product-vision.md
│   ├── domain-model-and-ubiquitous-language.md
│   ├── domain-map.md
│   ├── core-domain.md
│   ├── domain-inventory.md
│   ├── multi-tenant-architecture.md
│   ├── product-map.md
│   └── mvp-scope.md
├── 01-domain/                  # DDD por bounded context
│   ├── platform/
│   │   ├── aggregates/
│   │   ├── entities/
│   │   ├── value-objects/
│   │   ├── services/
│   │   ├── rules/
│   │   └── events/
│   ├── credit/
│   │   ├── aggregates/
│   │   ├── entities/
│   │   ├── value-objects/
│   │   ├── services/
│   │   ├── rules/
│   │   └── events/
│   └── shared-kernel/
│       └── common/
├── 02-product/                 # Product por capability/contexto
│   ├── capabilities/
│   ├── epics/
│   ├── features/
│   └── user-stories/
├── 03-architecture/            # AMP, ADRs, context maps, RFCs, reviews
│   ├── amp-001.md
│   ├── adrs/
│   ├── context-maps/
│   ├── rfcs/
│   └── reviews/
├── 04-engineering/             # CI/CD, observability, infra, security
│   ├── standards/
│   ├── ci-cd/
│   ├── observability/
│   └── security/
├── 05-implementation/          # Planos e backlogs de execução
│   ├── plans/
│   └── execution-backlogs/
├── 06-governance/              # Processos, aprovações, decision requests, handoffs
│   ├── processes/
│   ├── decision-requests/
│   └── handoffs/
├── 07-audits-and-discoveries/  # Auditorias, descobertas, análises
│   ├── audits/
│   └── discoveries/
├── 08-operations/              # Runbooks, playbooks, SOPs
│   ├── runbooks/
│   └── playbooks/
├── 09-references/              # Templates, glossary, assets, UX
│   ├── templates/
│   ├── glossary/
│   ├── assets/
│   └── ux/
└── README.md                   # Índice, mapa de navegação, metadados
```

**Observação:** a numeração garante ordem de navegação, mas os IDs internos dos documentos (FOUNDATION-001, DOMAIN-017, etc.) devem ser preservados para rastreabilidade.

## 5.12 Quais dependências documentais são perigosas?

1. **Implementation depende diretamente de Foundation/Domain.** Se Foundation mudar, todos os planos técnicos podem ficar desatualizados.
2. **Auditorias referenciam todos os níveis sem versionamento.** Auditorias antigas podem ser interpretadas como verdade atual.
3. **Handoffs apontam para documentos versionados.** O ponteiro `HANDOFF-VIGENTE.md` dentro do repo cria risco de circularidade.
4. **Discoveries em `auditorias/`** dificultam a validação automática e a navegação.
5. **Templates não possuem metadados de categoria.** O validador atual reconhece camadas por nome de pasta, não por metadados.

## 5.13 Existe acoplamento documental? Onde?

**Sim, nos seguintes pontos:**

1. **Implementation/Plans misturado com Governance.** `PEDIDO-ORIENTACAO-IMP-033` em `implementation/plans/` cria acoplamento entre execução e decisão.
2. **Auditorias misturadas com Discoveries.** `discovery-adr-003-multi-tenant.md` em `auditorias/` cria acoplamento entre análise e descoberta.
3. **Foundation-002 vs Foundation-005.** Dois documentos de referência terminológica com responsabilidades sobrepostas.
4. **Handoff datado e ponteiro no mesmo diretório.** `HANDOFF-VIGENTE.md` e `2026-08-04-...` compartilham a pasta, mas têm naturezas diferentes.
5. **AMP-001 e Auditorias.** AMP-001 sintetiza auditorias, mas não há link explícito de dependência.

## 5.14 Como seria a arquitetura documental ideal daqui a cinco anos?

A documentação se torna uma **Documentação como Plataforma (Docs-as-Code)**:

- **Camadas bem definidas:** Foundation, Domain, Product, Architecture, Engineering, Implementation, Governance, Audits, Operations, References.
- **Namespace por produto/bounded context:** cada contexto tem sua própria árvore de Domain/Product/Implementation.
- **Metadados estruturados:** cada documento possui front matter YAML com ID, status, versão, autor, tags, contexto, dependências.
- **Índice machine-readable:** `docs-index.json` gerado automaticamente para agentes e ferramentas.
- **Validação contínua:** `docs:validate` verifica IDs, dependências, templates, links, status e categorias.
- **Templates por categoria:** standards, engineering, governance, operations, rfc — além dos atuais DDD/Product.
- **Handoffs fora do repo:** `HANDOFF-VIGENTE.md` vive em `$HOME` e aponta para handoffs versionados em `docs/governance/handoffs/`.
- **Artefatos de ferramentas fora de docs/:** `graphify-out/`, caches e logs de agentes vivem em `.tools/` ou fora do repo.
- **Glossário vinculado ao Domain:** o glossário é gerado a partir dos documentos de Domain, evitando duplicação com Foundation.
- **Revisão cíclica:** Foundation → Domain → Product → Architecture → Engineering → Implementation → Governance → Audits → Foundation.

## 5.15 Produzir um Roadmap de Evolução Documental.

Ver seção 8.

---

# 6. Problemas Encontrados

## 6.1 Problemas críticos

1. **Duplicação física de planos.** `implementationplans/` e `implementation/plansPLAN-...` são cópias/erros.
2. **Categoria errada de documentos.** `discovery-adr-003` em `auditorias/` e `PEDIDO-ORIENTACAO` em `implementation/plans/`.
3. **Ponteiro de máquina versionado no repo.** `HANDOFF-VIGENTE.md` é estado local, não documentação.
4. **Cache de ferramenta versionado.** `docs/graphify-out/` não é documentação.
5. **Ausência de `docs/README.md`.** Não há mapa de navegação ou guia de contribuição.

## 6.2 Problemas importantes

6. **Falta de camadas de Engineering, Governance, Standards, Security, Operations.**
7. **Responsabilidade excessiva em FOUNDATION-002, FOUNDATION-005 e PLAN-002.**
8. **Template de plano usa `IMPL-XXX`, mas planos reais usam `PLAN-XXX`.** Inconsistência de taxonomia.
9. **Pastas vazias com `.gitkeep` sem propósito claro.** (`implementation/api/`, `architecture/`, `database/`, `testing/`, `domain/glossary/`).
10. **Documentos de auditoria contêm arquitetura reviews.** Categorização imprecisa.

## 6.3 Problemas menores

11. `ux/wireframes/` está vazio.
12. `assets/diagrams/` e `assets/images/` sem indexação clara.
13. Não há metadados estruturados (front matter YAML) nos documentos.
14. Não há `glossary.md` operacional.
15. Não há documentação de onboarding para novos times/agentes.

---

# 7. Oportunidades

1. **Reestruturar agora, antes do EPIC-002.** A base documental ainda é pequena o suficiente para ser reorganizada sem trauma.
2. **Adotar metadados estruturados.** Facilita validação automática e navegação por agentes.
3. **Criar camadas de Governance e Engineering.** Permite decisões de CI/CD, observability, segurança e processos.
4. **Separar Discovery de Audit.** Melhora a validação e a clareza.
5. **Mover handoffs para Governança.** Torna o processo de handoff oficial e rastreável.
6. **Criar `docs/README.md` como mapa de navegação.** Acelera onboarding.
7. **Aproveitar `docs:validate`.** Expandir o validador para checar categorias, metadados e dependências.

---

# 8. Proposta de Arquitetura Documental Alvo

## 8.1 Camadas documentais

| Camada | ID Pattern | Template | Responsabilidade |
|--------|------------|----------|------------------|
| Foundation | `FOUNDATION-NNN` | foundation-template.md | Visão, escopo, princípios, linguagem ubíqua. |
| Domain | `DOMAIN-NNN` | aggregate/entity/... | Modelos DDD, invariantes, regras, eventos. |
| Product | `PRODUCT-NNN`, `EPIC-NNN`, `FEATURE-NNN`, `US-NNN` | product templates | Capabilities, épicos, features, user stories. |
| Architecture | `AMP-NNN`, `ADR-NNN`, `RFC-NNN` | adr-template, custom | AMP, ADRs, RFCs, context maps, reviews. |
| Engineering | `ENG-NNN`, `STD-NNN` | novos | CI/CD, observability, infra, padrões. |
| Implementation | `PLAN-NNN`, `BACKLOG-NNN`, `IMPL-NNN` | implementation-plan-template | Planos técnicos, backlogs de execução. |
| Governance | `GOV-NNN`, `DECISION-NNN` | novos | Processos, aprovações, decision requests, handoffs. |
| Audits & Discoveries | `AUDIT-NNN`, `DISCOVERY-NNN` | novos | Auditorias, descobertas, análises. |
| Operations | `RUNBOOK-NNN`, `PLAYBOOK-NNN` | novos | Procedimentos operacionais. |
| References | — | templates, glossary | Templates, glossário, assets, UX. |

## 8.2 Estrutura alvo por bounded context

Para múltiplos contextos, a estrutura deve ser namespaceada:

```
docs/
├── 01-domain/
│   ├── platform/
│   │   ├── aggregates/DOMAIN-017-aggregate-tenant.md
│   │   ├── entities/DOMAIN-018-entity-usuario.md
│   │   └── ...
│   ├── credit/
│   │   ├── aggregates/DOMAIN-001-aggregate-carteira.md
│   │   ├── entities/DOMAIN-002-entity-pessoa.md
│   │   └── ...
│   └── shared-kernel/
│       └── ...
├── 02-product/
│   ├── platform/
│   │   ├── capabilities/PRODUCT-001-administrar-plataforma.md
│   │   ├── epics/EPIC-001-gerenciar-tenant.md
│   │   └── ...
│   └── credit/
│       └── ...
```

## 8.3 Metadados obrigatórios

Cada documento deve conter front matter:

```yaml
---
id: FOUNDATION-001
version: 1.0.0
status: Aprovado
category: foundation
context: platform
created: 2026-08-01
updated: 2026-08-04
authors: [Head de Produto]
reviewers: [CTO]
dependencies: [FOUNDATION-002, DOMAIN-017]
---
```

## 8.4 Validação documental

Expandir `scripts/validate-docs.js` para:

- Validar `category` e `context` no front matter.
- Verificar duplicatas de IDs globalmente.
- Verificar dependências cíclicas.
- Validar que `discoveries/` não contenham auditorias e vice-versa.
- Validar que `HANDOFF-VIGENTE.md` não exista em `docs/handoffs/`.
- Verificar arquivos órfãos (não referenciados).

---

# 9. Roadmap de Evolução Documental

## 9.1 Fase 1 — Higiene (agora, antes do EPIC-002)

**Objetivo:** remover duplicações e categorias erradas.

- [ ] Remover `docs/implementationplans/` (pasta duplicada/errada).
- [ ] Remover `docs/implementation/plansPLAN-002-epic-001-tenant-management.md` (arquivo corrompido).
- [ ] Mover `docs/auditorias/discovery-adr-003-multi-tenant.md` para `docs/discoveries/`.
- [ ] Mover `docs/implementation/plans/PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md` para `docs/governance/decision-requests/` (ou criar camada `governance/`).
- [ ] Mover `docs/handoffs/HANDOFF-VIGENTE.md` para `~/HANDOFF-VIGENTE.md` (fora do repo).
- [ ] Mover `docs/auditorias/raio-x-arquitetural-ecossistema.md` e `auditoria-as-is-to-be-ecossistema.md` para `docs/architecture/reviews/` (ou `docs/governance/audits/`).
- [ ] Mover `docs/graphify-out/` para fora de `docs/` (ex.: `.graphify-out/` na raiz) ou adicionar a `.gitignore`.
- [ ] Remover pastas vazias sem propósito: `implementation/api/`, `implementation/architecture/`, `implementation/database/`, `implementation/testing/`, `domain/glossary/` (ou populá-las).
- [ ] Criar `docs/README.md` com mapa de navegação.

## 9.2 Fase 2 — Estrutura (durante o EPIC-002)

**Objetivo:** criar camadas faltantes e reestruturar por contexto.

- [ ] Criar `docs/04-engineering/` com subpastas `standards/`, `ci-cd/`, `observability/`, `security/`.
- [ ] Criar `docs/06-governance/` com subpastas `processes/`, `decision-requests/`, `handoffs/`.
- [ ] Criar `docs/07-audits-and-discoveries/` com `audits/` e `discoveries/`.
- [ ] Criar `docs/08-operations/` com `runbooks/` e `playbooks/`.
- [ ] Criar `docs/09-references/glossary/`.
- [ ] Reorganizar `docs/domain/` e `docs/product/` por bounded context (`platform/`, `credit/`, etc.).
- [ ] Dividir `FOUNDATION-002` em linguagem ubíqua + glossário operacional.
- [ ] Atualizar `implementation-plan-template.md` para usar `PLAN-XXX` (ou `IMPL-XXX` consistentemente).

## 9.3 Fase 3 — Metadados e Automação (após o EPIC-002)

**Objetivo:** tornar a documentação navegável por humanos e agentes.

- [ ] Adicionar front matter YAML em todos os documentos.
- [ ] Criar `docs-index.json` gerado automaticamente.
- [ ] Expandir `scripts/validate-docs.js` para validar metadados, categorias e dependências.
- [ ] Criar templates para `RFC`, `Standard`, `Runbook`, `Playbook`, `Security Policy`, `Decision Request`.
- [ ] Integrar validação documental ao CI/CD.

## 9.4 Fase 4 — Escala (após o EPIC-005)

**Objetivo:** suportar múltiplos produtos, times e agentes.

- [ ] Namespacear documentos por produto/contexto.
- [ ] Criar `docs/00-foundation/PRODUCT-002/` se houver segundo produto.
- [ ] Criar processo de arquivamento de documentos obsoletos.
- [ ] Criar `docs/operations/incident-response/`.
- [ ] Criar `docs/ai/` para governança de agentes/IA.
- [ ] Avaliar ferramenta de publicação de documentação (ex.: MkDocs, Docusaurus) para navegação interna.

---

# 10. Recomendações

1. **Não iniciar EPIC-002 sem a Fase 1 de higiene.** Documentos duplicados e categorias erradas criarão confusão.
2. **Aprovar a arquitetura documental alvo antes de criar novos documentos.** Evita acumular dívida documental.
3. **Criar `docs/README.md` imediatamente.** Onboarding de novos times e agentes depende disso.
4. **Mover `HANDOFF-VIGENTE.md` para fora do repo.** Ele é estado de máquina, não documentação.
5. **Separar Discoveries de Auditorias.** Validação automática e navegação dependem de categorias claras.
6. **Adotar front matter YAML.** É o pré-requisito para machine-readable docs.
7. **Expandir `docs:validate` para metadados e categorias.** Previne regressões documentais.
8. **Criar templates de Governance, Engineering e Operations.** Padroniza novas camadas.
9. **Reorganizar Domain/Product por bounded context.** Prepara para Cobrança, Agenda, Comunicação, etc.
10. **Manter IDs globais, mas organizar por namespace.** Rastreabilidade + navegabilidade.

---

# 11. Conclusão do CTO

## 11.1 A arquitetura documental atual suporta a evolução pelos próximos anos?

**Não sem evolução.**

A TiaNet tem documentação de alta qualidade, mas a arquitetura documental foi construída para um único EPIC e um único contexto. Com a entrada do EPIC-002 e dos contextos de Cadastro, Comercial, Contratos e Motor Financeiro, a estrutura atual começará a sufocar. A reorganização proposta é preventiva e de baixo custo agora.

## 11.2 Qual é o risco de não agir?

- Documentos duplicados e mal categorizados se multiplicarão.
- Agentes e novos times não conseguirão navegar na base documental.
- Auditorias e descobertas serão confundidas com fontes de verdade.
- A validação documental falhará à medida que novas categorias surgirem.
- A arquitetura de código evoluirá mais rápido que a arquitetura da documentação, criando divergência.

## 11.3 Qual é a decisão recomendada?

Aprovar a **Fase 1 de higiene documental** como pré-requisito do EPIC-002, e a **Fase 2 de estrutura** como parte do EPIC-002. A **Fase 3 de metadados e automação** deve ser um EPIC de infraestrutura documental separado.

---

# 12. Lista de Mudanças Recomendadas (não executadas)

## 12.1 Remover / Consolidar

1. Remover `docs/implementationplans/`.
2. Remover `docs/implementation/plansPLAN-002-epic-001-tenant-management.md`.
3. Remover `.gitkeep` vazios sem propósito.
4. Mover `docs/graphify-out/` para fora de `docs/`.

## 12.2 Mover / Reclassificar

5. Mover `docs/auditorias/discovery-adr-003-multi-tenant.md` → `docs/discoveries/`.
6. Mover `docs/implementation/plans/PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md` → `docs/governance/decision-requests/`.
7. Mover `docs/handoffs/HANDOFF-VIGENTE.md` → `~/HANDOFF-VIGENTE.md`.
8. Mover `docs/auditorias/raio-x-arquitetural-ecossistema.md` → `docs/architecture/reviews/`.
9. Mover `docs/auditorias/auditoria-as-is-to-be-ecossistema.md` → `docs/architecture/reviews/` ou `docs/governance/audits/`.

## 12.3 Criar

10. Criar `docs/README.md`.
11. Criar `docs/04-engineering/`.
12. Criar `docs/06-governance/`.
13. Criar `docs/07-audits-and-discoveries/`.
14. Criar `docs/08-operations/`.
15. Criar `docs/09-references/glossary/`.
16. Criar templates para Governance, Engineering, Operations, RFC.

## 12.4 Refatorar

17. Dividir `FOUNDATION-002` em linguagem ubíqua + glossário.
18. Atualizar `implementation-plan-template.md` para refletir `PLAN-XXX`.
19. Adicionar front matter YAML em todos os documentos.
20. Expandir `scripts/validate-docs.js` para metadados e categorias.

---

# 13. Referências

- AMP-001 — Architecture Master Plan.
- PLAN-001, PLAN-002 — Planos de implementação.
- ADR-001, ADR-002 — Decisões arquiteturais.
- Handoff 2026-08-04 — Estado do EPIC-001.
- Auditorias e Discoveries existentes.

---

# 14. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-04 | Descoberta da arquitetura documental: inventário, mapas, problemas, oportunidades, proposta alvo e roadmap de evolução. |

---

**Nota de encerramento:** Este documento é uma análise puramente documental. Nenhum arquivo existente foi alterado, movido, renomeado ou removido. Nenhum código foi implementado. Nenhuma ADR, Foundation, Product ou Feature foi criada. Aguardando revisão e autorização para executar as mudanças recomendadas.
