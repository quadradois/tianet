# ROADMAP-ALIGNMENT-001 — Alinhamento do Roadmap Product × AMP

**ID:** ROADMAP-ALIGNMENT-001

**Versão:** 1.0.0

**Status:** Aprovado como documento oficial de transição

**Data:** 2026-08-05

**Autor:** SDD + Agent Loop Arquitetural (análise para decisão)

---

# 1. Inventário de EPICs

## 1.1 Fonte Product — PRODUCT-001

O [PRODUCT-001](../product/platform/capabilities/PRODUCT-001-administrar-plataforma.md) (§6 — Épicos) enumera, dentro da Capacidade **Administrar Plataforma** (status **Aprovado**), os seguintes Épicos:

| ID | Nome | Documento |
|----|------|-----------|
| EPIC-001 | Gerenciar Tenant | [EPIC-001](../product/platform/epics/EPIC-001-gerenciar-tenant.md) (existe) |
| EPIC-002 | Gerenciar Usuários | inexistente |
| EPIC-003 | Gerenciar Perfis de Acesso | inexistente |
| EPIC-004 | Gerenciar Permissões | inexistente |
| EPIC-005 | Gerenciar Configurações da Plataforma | inexistente |
| EPIC-006 | Autenticação e Controle de Acesso | inexistente |

## 1.2 Fonte AMP — [AMP-001](./amp/AMP-001-architecture-master-plan.md)

O AMP-001 (status **Rascunho para revisão arquitetural**) distribui os Épicos por contexto/roadmap em (§3.1/§3.2, §10.1, §13.2, §14.3):

| ID | Nome | Onde aparece |
|----|------|--------------|
| EPIC-001 | Gerenciar Tenant (concluído) | §3.1 |
| EPIC-002 | Cadastro de Devedores | §3.1, §10.1 (item 2), §13.2, §14.3 |
| EPIC-003 | Comercial + Contratos | §3.1 ("iniciado") |
| EPIC-003 | Contratos | §10.1 (item 3) |
| EPIC-003 | Comercial/Propostas | §10.1 (item 2) |
| EPIC-004 | Empréstimos + Pagamentos + Motor Financeiro | §3.2, §10.1 (item 3) |
| EPIC-005 | Cobrança, Agenda, Comunicação, Relatórios | §3.2, §10.1 (item 4) |
| EPIC-006 | IAM (Autenticação, Autorização RBAC, perfis e permissões) | §3.1, §10.1 (item 1), §13.2, §14.3 |

## 1.3 Evidências de apoio (não são fonte primária)

| Documento | Menção |
|-----------|--------|
| [Raio-X arquitetural](../audits/audits/raio-x-arquitetural-ecossistema.md) | "EPIC-002 (Gerenciar Usuários) … relação primeiro usuário vs convite" |
| [FEATURE-002 discovery](../audits/discoveries/FEATURE-002-consultar-tenant-discovery.md) | "Exposição de Usuários, Carteiras ou Configurações do Tenant (EPIC-002, EPIC-003, EPIC-005)" |
| [FEATURE-003 discovery](../audits/discoveries/FEATURE-003-atualizar-tenant-discovery.md) | "Gerenciamento de Usuários (EPIC-002), Carteiras (EPIC-003) e Configurações (EPIC-005)" |
| [FEATURE-004 discovery](../audits/discoveries/FEATURE-004-inativar-tenant-discovery.md) | "Gerenciamento de Usuários (EPIC-002), Carteiras (EPIC-003) e Configurações (EPIC-005)" |
| [Handoff vigente](../governance/handoffs/2026-08-04-handoff-sessao-epic-001-tenant-management-fechado.md) | "EPIC-002 (Cadastro de Devedores) pode ser iniciado" |
| [DOCUMENT-ARCHITECTURE-DISCOVERY](./amp/DOCUMENT-ARCHITECTURE-DISCOVERY.md) | Associa EPIC-002 ao contexto de Cadastro |
| [DOCUMENT-ARCHITECTURE-MIGRATION-PLAN](./amp/DOCUMENT-ARCHITECTURE-MIGRATION-PLAN.md) | "Iniciar Cadastro de Devedores sem a estrutura documental correta" |
| [Auditoria AS-IS/TO-BE](../audits/audits/auditoria-as-is-to-be-ecossistema.md) | "Criar EPIC-002..EPIC-006", "EPIC-002..EPIC-006 não existem" |

> Resultado: **existe uma terceira numeração** na história (discoveries usaram EPIC-002 = Usuários, EPIC-003 = Carteiras, EPIC-005 = Configurações). Isso reforça que a numeração nunca foi única nem estável.

---

# 2. Tabela comparativa

| ID do Épico | Product (PRODUCT-001) | AMP-001 | Observação |
|--------------|-----------------------|---------|------------|
| EPIC-001 | Gerenciar Tenant | Gerenciar Tenant | ✅ **Alinhados** — concluído. |
| EPIC-002 | Gerenciar Usuários | **Cadastro de Devedores** | ⚠️ **Conflito de nome e contexto**. |
| EPIC-003 | Gerenciar Perfis de Acesso | Comercial/Propostas **e** Contratos (ambíguo no próprio AMP) | ⚠️ **Conflito** + inconsistência interna do AMP. |
| EPIC-004 | Gerenciar Permissões | Empréstimos + Pagamentos + Motor Financeiro | ⚠️ **Conflito**. |
| EPIC-005 | Gerenciar Configurações da Plataforma | Cobrança, Agenda, Comunicação, Relatórios | ⚠️ **Conflito** + colisão terminológica ("Configurações"). |
| EPIC-006 | Autenticação e Controle de Acesso | IAM (Autenticação, Autorização RBAC, perfis e permissões) | ⚠️ Parciais — mesmo ID e tema (IAM), mas Product estreita a Autenticação e exclui gestão de usuários/perfis/permissões. |

---

# 3. Conflitos identificados

1. **EPIC-002** — Produto: "Gerenciar Usuários"; AMP: "Cadastro de Devedores".
2. **EPIC-003** — Produto: "Perfis de Acesso"; AMP: "Comercial/Propostas" (§10.1 item 2) e "Contratos" (§10.1 item 3) — o próprio AMP usa EPIC-003 para dois conteúdos.
3. **EPIC-004** — Produto: "Permissões"; AMP: "Empréstimos + Pagamentos + Motor Financeiro".
4. **EPIC-005** — Produto: "Configurações da Plataforma"; AMP: "Cobrança, Agenda, Comunicação, Relatórios".
5. **Escopo do IAM** — Produto limita o EPIC-006 a "Autenticação e Controle de Acesso" (Usuários/Perfis/Permissões ficam fora); AMP centra no EPIC-006 *toda* a gestão de Usuários, Perfis e Permissões (RBAC).
6. **Prioridade / ordem de execução** — Produto ordena capacidade Plataforma (Usuários → Perfis → Permissões → Configurações → IAM); AMP prioriza IAM, depois Cadastro, depois Comercial/Financeiro.
7. **Nível de numeração** — Produto numera Épicos **localmente por capacidade** (6 EPICs da "Administrar Plataforma"); AMP numera **globalmente por contexto evolutivo** (todos os contextos). A colisão numérica decorre desse desnível.
8. **"Configurações" ambíguo** — Product "Configurações **da Plataforma**" vs AMP contexto "Configurações" (§4.2, §4.4: taxas, modalidades, calendário financeiro) — significados distintos sob o mesmo termo.
9. **Comercial fora do Product Map** — AMP prevê contexto Comercial (Propostas/Simulações), mas ele não existe como capacidade no [FOUNDATION-007](../foundation/FOUNDATION-007-product-map.md) (Aprovado) — violaria "toda funcionalidade pertence a uma capacidade" se implementado sem mapeamento.
10. **Terceira numeração histórica** — discoveries usam EPIC-003 = Carteiras, divergindo até do próprio PRODUCT-001.

---

# 4. Classificação dos conflitos

| Conflito | Nomenclatura/Numeração | Prioridade/Ordem | Contexto | Responsabilidade |
|----------|:---:|:---:|:---:|:---:|
| CP-002 (Usuários vs Devedores) | ● | ● | ● | ● |
| CP-003 (Perfis vs Comercial/Contratos) | ● | ● | ● | ● |
| CP-004 (Permissões vs Empréstimos/Motor) | ● | ● | ● | ● |
| CP-005 (Config. Plataforma vs Operação Diária) | ● | ● | ● | ● |
| CP-006 (escopo IAM) | ● | | ● | ● |
| CP-007 (nível de numeração) | ● | | ● | ● |
| CP-008 ("Configurações" ambíguo) | ● | | ● | |
| CP-009 (Comercial fora do Product Map) | | ● | ● | ● |
| CP-010 (terceira numeração) | ● | | | |

---

# 5. Sequência oficial proposta (referência — sem alterar documentos)

Proposta única, em dois níveis:

## 5.1 Princípio de numeração

**Um Épico é um pacote de entrega; a numeração EPIC-n é global e estável**, vinculada a uma **capacidade** (FOUNDATION-007, Princípio 03) e reflexo da evolução por contexto. Numeração por capacidade local (como a de PRODUCT‑001) deve ser abolida para evitar colisão de IDs.

## 5.2 Sequência global proposta

| Ordem | ID | Épico | Capacidade (FOUNDATION-007) | Contexto | Estado |
|-------|----|-------|------------------------------|----------|--------|
| 1 | EPIC-001 | Gerenciar Tenant | Administrar Plataforma | Platform | Concluído |
| 2 | EPIC-006 | Controle de Acesso (IAM): Usuários, Perfis, Permissões, Autenticação e Autorização | Administrar Plataforma | Platform/IAM | Urgente — pré-requisito de segurança |
| 3 | EPIC-002 | Cadastro de Devedores | Administrar Cadastro | Cadastro | Próximo bloco de construção |
| 4 | EPIC-003 | Comercial (Propostas/Simulação) | a definir (nova capacidade, ver CP-009) | Comercial | Após Cadastro |
| 5 | EPIC-004 | Contratos de Crédito | (Operações de Crédito) | Contratos | Após Comercial |
| 6 | EPIC-005 | Empréstimos, Pagamentos e Motor Financeiro | Operações de Crédito | Motor Financeiro (Core) | Após Contratos |
| 7 | EPIC-007 | Operação Diária (Cobrança, Agenda, Comunicação, Relatórios) | Cobrança/Agenda/Comunicação/Relatórios | Cobrança/Agenda/Comunicação/Relatórios | Após Motor |

Notas:

- A **ordem recomendada de execução** segue o AMP (§10.1): IAM primeiro (segurança), depois Cadastro e transações comerciais/financeiras. O IAM pode rodar em **paralelo** com o Cadastro (AMP §13.2).
- **EPIC-002 = Cadastro de Devedores** (como já estabelecido no então handoff vigente e na migração documental), **não** "Gerenciar Usuários". Usuários/Perfis/Permissões integram o **EPIC-006 (IAM)**.
- "Configurações" desambiguado: **"Configurações da Plataforma"** = capacidade de Plataforma; **"Configurações Financeiras"** (taxas, modalidades, calendário) = contexto Configurações do AMP. Não compartilham EPIC.
- Comercial/Propostas e Contratos devem ser **Épicos separados** (conforme §4.2 do AMP, dois contextos distintos), resolvendo a ambiguidade interna do AMP em EPIC-003.

---

# 6. Documentos que precisarão de atualização (se proposta e aprovada)

> Referência: nenhum destes deve ser alterado agora. Listar apenas o impacto futuro.

| Documento | Ação necessária |
|-----------|-----------------|
| [PRODUCT-001](../product/platform/capabilities/PRODUCT-001-administrar-plataforma.md) | Revisar §6 — remover Usuários/Perfis/Permissões/Configurações (EPIC-002..005) como Épicos independentes; manter "Autenticação e Controle de Acesso" (EPIC-006) e referenciar IAM. |
| [EPIC-001](../product/platform/epics/EPIC-001-gerenciar-tenant.md) | Sem mudança (não conflita). |
| [FOUNDATION-007](../foundation/FOUNDATION-007-product-map.md) | Avaliar inclusão de nova capacidade "Administrar Comercial" (Resolução CP-009) — decisão de produto. |
| [AMP-001](./amp/AMP-001-architecture-master-plan.md) | Corrigir inconsistência interna EPIC-003 (Comercial/Propostas vs Contratos); consolidar numeração nova e status. |
| [Raio-X arquitetural](../audits/audits/raio-x-arquitetural-ecossistema.md) | Atualizar referência "EPIC-002 (Gerenciar Usuários)" → EPIC-006 (IAM). |
| [FEATURE-002 discovery](../audits/discoveries/FEATURE-002-consultar-tenant-discovery.md) | Atualizar referências EPIC-002/003/005 para o novo roadmap. |
| [FEATURE-003 discovery](../audits/discoveries/FEATURE-003-atualizar-tenant-discovery.md) | Idem. |
| [FEATURE-004 discovery](../audits/discoveries/FEATURE-004-inativar-tenant-discovery.md) | Idem. |
| [Auditoria AS-IS/TO-BE](../audits/audits/auditoria-as-is-to-be-ecossistema.md) | Ajustar ação "Criar EPIC-002..EPIC-006" para a sequência nova. |
| Handoff vigente + futuro Product Layer | Criar PRODUCT-002 (Capacidade Administrar Cadastro) que inaugura o EPIC-002. |

> **Não-alterar:** FOUNDATION-001..008, DOMAIN-*, ADR-*, planos já executados (PLAN-001/002), US/FEATURES fechadas do EPIC-001.

---

# 7. Impactos na rastreabilidade

- **Vínculo Product → implementação** — US/Features do EPIC-001 referem-se apenas a EPIC-001; não quebraria.
- **User Stories e features futuras** — precisarão referenciar o novo número (ex.: features de devedor → EPIC-002/Cadastro; features de usuário → EPIC-006/IAM).
- **Discoveries (FEATURE-002/003/004)** contêm referência a "EPIC-002 (Usuários)". Sem atualização, tornam-se evidência contraditória e geram falsos positivos em análises de rastreabilidade.
- **Raio-X arquitetural** usa "EPIC-002 (Gerenciar Usuários)"; correção necessária para não ensejar interpretação equivocada futura.
- **Link cross-layer** — o ROADMAP-ALIGNMENT (novo) passa a ser o **ponto único** que explica a convergência `Product × AMP`; todo arco de rastreabilidade novo passa a ser "Product → EPIC → Feature → US → implementation → audits", com a EPIC viva em nível global.
- **Retrofit (dados históricos)**: alterações de ID em documentos aprovados (raio-x, discoveries) devem ser tratadas como **erratas versionadas** (novo "Histórico de Versões"), nunca como edição silenciosa.

---

# 8. Impactos no SDD — especificação-flow

Novo fluxo documental (já padrão): **Produto → Discovery → SDD → Agent Loop → Implementação → Review → Merge**.

O modelo EPIC tratado aqui tem os seguintes efeitos:

1. **Discovery escopo** — o próximo Discovery será do **EPIC-002 (Cadastro de Devedores)** (contexto Credit/Cadastro), não da gestão de usuários. "Gerenciar Usuários" permanece até o EPIC-006 (IAM), com data futura.
2. **SDD recortado por capacidade/contexto** — cada EPIC terá Product Doc de capacidade (PRODUCT-002 Administrar Cadastro, PRODUCT-003 Comercial etc.) + Domain entities do contexto. A numeração local-duplicada (6 EPICs só na plataforma) deixa de existir.
3. **Criação de novos IDs** — serão criados Product (capacidade), nova capability, novas US/Features, e DOMAIN/ENT/VO/DSVC/EVT/BR para o contexto Cadastro, evitando atrito com IDs de Platform.
4. **SDD depende de decisão prévia** — o EPIC-002 (Cadastro) só é formalizado em Product depois da aprovação do ROADMAP-ALIGNMENT; o documento continua com status Rascunho até lá.
5. **Épicos vs Contextos** — a correspondência número/contexto (bounded context) passa a ser: cada EPIC = uma capacidade + um contexto primário; feature de IAM compartilhada via conformist/ACL (sem reutilização dupla de IDs).

---

# 9. Recomendação

**Criar nova versão do Product e consolidar um único roadmap global — não manter as duas numerações simultaneamente.**

| Opção | Veredito | Justificativa técnica |
|--------|----------|------------------------|
| **Manter Product como fonte** | 🔴 | PRODUCT-001 numera por capacidade e representa o **estágio inicial (Plataforma)**, antes da descoberta dos Contextos de Negócio. Não explica o Cadastro como nova entrada que o Product Map (FOUNDATION-007) já afirma ser a evolução do produto. |
| **Manter AMP como fonte** | 🟢 (base) | AMP-001 é **mais novo** (2026-08-04) e faz uma **reavaliação estratégica completa** do produto como sistema de crédito por Contextos — alinhado ao Product Map (FOUNDATION-007) e ao novo fluxo documental. É a única fonte que organiza Usuários/Perfis/Permissões dentro do IAM e inaugura o contexto Cadastro/Financeiro. |
| **Nova versão do Product** | 🟢 **Recomendada** | Editar PRODUCT-001 (v2.0) para a numeração global, criando também as capacidades novas (Cadastro, Comercial etc.) com seus próximos documentos de Product (PRODUCT-002+). Preserva a cadeia "Product → EPIC → Feature" e coloca o Product alinhado ao AMP. |
| **Nova versão do AMP** | 🟢 Complemento | Corrigir inconsistência interna do AMP (EPIC-003 Comercial/Contratos) e consolidar a numeração nova com EPIC-006 e EPIC-007. Não substitui a necessidade de revisão do Product. |

**Conclusão da recomendação:**

1. Manter **AMP-001 como fonte oficial do roadmap** (com suas inconsistências internas corrigidas em nova versão).
2. **Revisar PRODUCT-001** (nova versão) alinhando a lista de Épicos à numeração global única — e criar as novas capacidades (PRODUCT-002 "Administrar Cadastro" que lança o EPIC-002) quando os EPICs forem iniciados.
3. Iniciar o **Discovery do EPIC-002 — Cadastro de Devedores** (contexto Cadastro/Credit), mantendo "Gerenciar Usuários" para o EPIC-006 (IAM), que pode ser tratado em paralelo (segurança).
4. Publicar como **pacote** a partir da aprovação (SDD: Foundation → Domain → Product → Plan → Execution Backlog) — **sem implementação antes da aprovação** do ROADMAP-ALIGNMENT e do PRODUCT revisto.

> Esta recomendação é precisa porque o conflito não é de conteúdo, mas de **nível** (capacidade-local vs roadmap-global). Unificar no nível global, com Usuários/Perfis/Permissões dentro do IAM, resolve a colisão sem perder a rastreabilidade Product → Feature existente do EPIC‑001.

---

# 10. Decisão Arquitetural — Aprovada com Ajustes (2026-08-05)

> Registro oficial da decisão. Este documento passa a ser **documento oficial de transição**.

## 10.1 Aprovado

- **AMP-001 como roadmap estratégico** do produto.
- **Eliminar a dupla numeração** de EPICs (capacidade-local × roadmap-global) — a sequência única segue a proposta da §5.2 com os ajustes abaixo.
- **Usuários/Perfis/Permissões integrados ao IAM** (EPIC-006), não como EPICs independentes de Platform.
- **EPIC-002 = Cadastro de Devedores**.
- **Corrigir PRODUCT-001 futuramente** (nova versão, após FOUNDATION-009), e **não** criar PRODUCT‑002/003/004 agora.
- Tratar este ROADMAP-ALIGNMENT como **documento oficial de transição** até a publicação do FOUNDATION-009.

## 10.2 Ajustes (não aprovado integralmente o item 5.2)

- **EPIC ≠ Bounded Context.** Um Bounded Context é uma **fronteira do domínio**; um EPIC é um **pacote de entrega**. Eles usualmente coincidem, mas um contexto pode possuir múltiplos EPICs.
- Hierarquia oficial congelada:

```
Capability
   ↓
Bounded Context
   ↓
EPIC
   ↓
Feature
   ↓
User Story
```

- Exemplo de representação: `Administrar Cadastro (Capability) → Cadastro (Contexto) → EPIC-002 (Gerenciar Cadastro de Devedores)`.

## 10.3 Não aprovado

- **Criar imediatamente PRODUCT-002 / PRODUCT-003 / PRODUCT-004.** A definição arquitetural das demais capacidades só nasce do FOUNDATION-009 (Capability Map) e, ainda assim, os documentos de Product são criados "quando houver necessidade real".

## 10.4 Próxima etapa (não de implementação)

```
FOUNDATION-009 (Capability Map)
   ↓
Revisão do PRODUCT-001
   ↓
Criação do PRODUCT-002 (quando houver necessidade real)
   ↓
Discovery do EPIC-002
   ↓
SDD
   ↓
Agent Loop
   ↓
Implementação
```

---

# 11. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-05 | Análise inicial do conflito de numeração de EPICs entre PRODUCT-001 (Aprovado) e AMP-001 (Rascunho), com proposta de alinhamento para decisão arquitetural. |
| 1.1.0 | 2026-08-05 | Registro da decisão arquitetural aprovada com ajustes (status formalizado como documento oficial de transição; seção 10 adicionada). |