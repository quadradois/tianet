# Relatório de Alinhamento Arquitetural — PRODUCT-001 × FOUNDATION-009

**Versão:** 1.0.0

**Status:** Rascunho para revisão arquitetural

**Data:** 2026-08-05

**Autor:** Principal Software Architect / Product Architect / Domain Architect / CTO

---

# 1. Resumo Executivo

O [FOUNDATION-009](../foundation/FOUNDATION-009-capability-map.md) (v1.0.0, Aprovado) congelou a hierarquia oficial **Capability → Bounded Context → EPIC → Feature → User Story**, a regra **EPIC ≠ Bounded Context**, a numeração global de EPICs e a criação tardia de PRODUCT-N. O [ROADMAP-ALIGNMENT-001](./ROADMAP-ALIGNMENT-PRODUCT-AMP.md) (Aprovado como documento de transição) registrou a decisão de alinhar o [PRODUCT-001](../product/platform/capabilities/PRODUCT-001-administrar-plataforma.md) a essa governança.

Este relatório analisa o PRODUCT-001 (v1.0.0) contra o FOUNDATION-009, o ROADMAP-ALIGNMENT-001 e o [AMP-001](./amp/AMP-001-architecture-master-plan.md). Foram identificadas **7 divergências** (3 arquiteturais, 2 estruturais, 2 editoriais) e **nenhuma decisão arquitetural nova** é necessária.

**Parecer do arquiteto:** o PRODUCT-001 precisa de **nova versão (v2.0.0)** — não de revisão in-place — concentrada na reescrita da §6 (Épicos) e em ajustes de §5/§7/§8. A Capability *Administrar Plataforma* permanece válida e correta em escopo. Nenhuma ADR nova é necessária. Nenhum Discovery novo é necessário. **Risco da atualização: baixo.**

---

# 2. Compatibilidade do PRODUCT-001 com o FOUNDATION-009

| Critério do FOUNDATION-009 | Situação no PRODUCT-001 | Veredito |
|----------------------------|--------------------------|----------|
| Hierarquia oficial (BR-001) | Não referencia a hierarquia Capability → Contexto → EPIC → Feature → US | ❌ Divergente |
| EPIC ≠ Bounded Context (BR-002) | Trata EPIC como sinônimo de capacidade/área da plataforma | ❌ Divergente |
| Numeração global única (BR-003) | Enumera EPIC-001..006 **localmente** por capacidade | ❌ Divergente |
| Capacidade como raiz (BR-004) | É uma capacidade válida do FOUNDATION-007 §3.1 | ✅ Compatível |
| Vínculo EPIC → contexto primário (BR-005) | Não declara contexto; EPICs sem vínculo explícito | ❌ Divergente |
| Criação tardia de PRODUCT-N (BR-006) | Documento existe (legítimo) — os EPICs internos é que são antecipados | ⚠️ Parcial |
| Core Domain exclusivo (BR-007) | §4 Limites respeita a exclusividade do Motor Financeiro | ✅ Compatível |
| Ordem de nascimento (BR-008) | EPICs planejados sem Discovery (Usuários/Perfis/Permissões/Configurações) | ⚠️ Parcial |
| Conceitos diferenciados (§3 FOUNDATION-009) | Não diferencia Capability, Contexto e EPIC | ❌ Divergente |
| Critérios de nova Capability (CC-001..CC-005) | Não se aplica (capacidade já existe) | — |

**Conclusão de compatibilidade:** a capacidade em si é compatível; a **estrutura interna de Épicos não é**.

---

# 3. Pontos de Divergência

| ID | Divergência | Localização |
|----|-------------|-------------|
| D-01 | Numeração local EPIC-002..006 em vez de numeração global | PRODUCT-001 §6 |
| D-02 | EPIC-002 = "Gerenciar Usuários" colide com EPIC-002 global = Cadastro de Devedores | PRODUCT-001 §6 |
| D-03 | EPIC-003 = "Gerenciar Perfis de Acesso" colide com EPIC-003 global (Comercial/Propostas) | PRODUCT-001 §6 |
| D-04 | EPIC-004 = "Gerenciar Permissões" colide com EPIC-004 global (Contratos) | PRODUCT-001 §6 |
| D-05 | EPIC-005 = "Gerenciar Configurações da Plataforma" colide com EPIC-005 global (Empréstimos/Motor) + colisão terminológica "Configurações" | PRODUCT-001 §6 |
| D-06 | EPIC-006 = "Autenticação e Controle de Acesso" com escopo estreito; global EPIC-006 = IAM completo (Usuários, Perfis, Permissões, AuthN/AuthZ) | PRODUCT-001 §6 |
| D-07 | Ausência de referência ao FOUNDATION-009 e de declaração de Bounded Context | PRODUCT-001 §1/§5 |

Divergências relacionadas, de redação (tratadas na §4/§5 como editoriais): §4 Limites (colisão terminológica "Configurações") e §7 Critérios de Aprovação (referência a "todos os Épicos").

---

# 4. Detalhamento por Divergência

## D-01 — Numeração local por capacidade

- **Localização:** PRODUCT-001 §6 (lista de Épicos).
- **Impacto:** colisão direta com a numeração global aprovada (BR-003 do FOUNDATION-009; decisão ROADMAP-ALIGNMENT-001 §10.1). Cada novo documento de outro contexto (ex.: EPIC-002 Cadastro) duplicaria IDs.
- **Severidade:** 🔴 Alta.
- **Recomendação:** reescrever §6 para referenciar **apenas os EPICs globais** da capacidade (*Administrar Plataforma* = Platform Context: **EPIC-001** concluído e **EPIC-006 IAM** emergente), sem re-atribuir números. Proibir numeração local.

## D-02 — EPIC-002 "Gerenciar Usuários"

- **Localização:** PRODUCT-001 §6, item EPIC-002.
- **Impacto:** conflito de identidade com EPIC-002 global (Cadastro de Devedores), já registrado no handoff vigente, na migração documental e no AMP-001 §10.1/§13.2. Usuários pertencem ao IAM (EPIC-006) por decisão aprovada.
- **Severidade:** 🔴 Alta.
- **Recomendação:** remover "Gerenciar Usuários" como EPIC-002. Gestão de usuários passa a ser **parte do EPIC-006 (IAM)**.

## D-03 — EPIC-003 "Gerenciar Perfis de Acesso"

- **Localização:** PRODUCT-001 §6, item EPIC-003.
- **Impacto:** colisão com EPIC-003 global (Comercial/Propostas, ROADMAP-ALIGNMENT §5.2). Perfis são responsabilidade do contexto IAM.
- **Severidade:** 🔴 Alta.
- **Recomendação:** remover como EPIC independente; integrar ao **EPIC-006 (IAM)**.

## D-04 — EPIC-004 "Gerenciar Permissões"

- **Localização:** PRODUCT-001 §6, item EPIC-004.
- **Impacto:** colisão com EPIC-004 global (Contratos). Permissões são responsabilidade do contexto IAM.
- **Severidade:** 🔴 Alta.
- **Recomendação:** remover como EPIC independente; integrar ao **EPIC-006 (IAM)**.

## D-05 — EPIC-005 "Gerenciar Configurações da Plataforma"

- **Localização:** PRODUCT-001 §6, item EPIC-005; §4 Limites.
- **Impacto:** colisão com EPIC-005 global (Empréstimos/Pagamentos/Motor) e ambiguidade terminológica: "Configurações da Plataforma" (capacidade Plataforma) ≠ "Configurações Financeiras" (contexto Configurações do AMP — taxas, modalidades, calendário).
- **Severidade:** 🟡 Média.
- **Recomendação:** remover como EPIC-005 independente. Registrar em §3/§4 a distinção explícita: **Configurações da Plataforma** permanece responsabilidade da capacidade (sem EPIC atribuído até haver Discovery — BR-006); **Configurações Financeiras** pertence ao contexto Configurações, fora desta capacidade.

## D-06 — EPIC-006 "Autenticação e Controle de Acesso"

- **Localização:** PRODUCT-001 §6, item EPIC-006.
- **Impacto:** o ID global EPIC-006 = IAM está parcialmente alinhado (mesmo tema), mas o escopo descrito é estreito — exclui Usuários, Perfis e Permissões, contrariando AMP-001 §3.1 ("autenticação JWT, autorização RBAC, perfis e permissões") e a decisão aprovada (ROADMAP-ALIGNMENT §10.1).
- **Severidade:** 🟡 Média.
- **Recomendação:** manter **EPIC-006 (IAM)** como Épico global da capacidade, renomeando para **"IAM — Autenticação, Usuários, Perfis e Permissões"**, absorvendo o escopo de D-02/D-03/D-04.

## D-07 — Ausência de governança/hierarquia

- **Localização:** PRODUCT-001 §1 (Objetivo) e §5 (Dependências).
- **Impacto:** o documento não declara a hierarquia oficial nem o Bounded Context (Platform/IAM), deixando a capacidade órfã de âncora e repetindo o padrão que causou o conflito PRODUCT-001 × AMP-001.
- **Severidade:** 🟡 Média.
- **Recomendação:** adicionar em §1 a referência à hierarquia oficial (FOUNDATION-009 §1/§3) e em §5 a dependência do **FOUNDATION-009**; declarar o contexto primário **Platform** (e IAM como contexto de autorização).

---

# 5. Classificação das Alterações

| Alteração | Tipo | Justificativa |
|-----------|------|---------------|
| D-01 — reescrita da numeração §6 | **Arquitetural** | Muda a semântica de identificação de Épicos (local → global). |
| D-02 — Usuários → IAM | **Arquitetural** | Redefine o dono da responsabilidade de gestão de usuários. |
| D-03 — Perfis → IAM | **Arquitetural** | Redefine o dono da responsabilidade de perfis. |
| D-04 — Permissões → IAM | **Arquitetural** | Redefine o dono da responsabilidade de permissões. |
| D-05 — Configurações sem EPIC + desambiguação | **Estrutural** | Não muda regra de negócio; reorganiza escopo e nomenclatura. |
| D-06 — Escopo do IAM ampliado | **Estrutural** | Amplia descrição de Épico já existente; sem nova decisão arquitetural. |
| D-07 — Referências a FOUNDATION-009/hierarquia | **Editorial** | Atualização de dependências e contexto sem efeito em regras. |
| §4 Limites — esclarecer "Configurações Financeiras" | **Editorial** | Redação para eliminar ambiguidade terminológica. |
| §7 Critérios — alinhar "todos os Épicos" à numeração global | **Editorial** | Redação; sem efeito em escopo. |

**Totais:** 4 arquiteturais · 2 estruturais · 3 editoriais.

---

# 6. Seções do PRODUCT-001 que Precisarão de Atualização

> Referência: nenhuma alteração será executada neste relatório. Lista para execução posterior.

| Seção | Ação necessária | Tipo |
|-------|-----------------|------|
| §1 Objetivo | Citar a hierarquia oficial e o FOUNDATION-009 como raiz da camada Product | Editorial |
| §3 Responsabilidades | Manter; organizar itens de Usuários/Perfis/Permissões sob IAM | Estrutural |
| §4 Limites | Adicionar explícito: Configurações Financeiras (taxas, modalidades) fora da capacidade | Editorial |
| §5 Dependências | Adicionar FOUNDATION-009; manter FOUNDATION-001/006/007/008 e DOMAIN-017/018/019 | Editorial |
| §6 Épicos | **Reescrita completa**: EPIC-001 (concluído) + EPIC-006 (IAM) apenas; sem numeração local | Arquitetural |
| §7 Critérios de Aprovação | Alinhar redação à numeração global (Épicos da capacidade, não "todos os Épicos") | Editorial |
| §8 Histórico de Versões | Adicionar entrada da nova versão (v2.0.0) com erratas registradas | Obrigatório |

**Sem alteração:** EPIC-001 (documento), FEATURE-001..004, US-001..014, demais camadas.

---

# 7. Validação da Capability "Administrar Plataforma"

**Veredito: ✅ permanece correta.**

- A capacidade é reconhecida pelo [FOUNDATION-007](../foundation/FOUNDATION-007-product-map.md) §3.1 (Tenant, Usuários, Autenticação, Perfis, Permissões, Configurações) e pelo [FOUNDATION-008](../foundation/FOUNDATION-008-mvp-scope.md) (MVP).
- O escopo declarado no PRODUCT-001 §3/§4 está alinhado: administra infraestrutura organizacional, isolamento, autorização e auditoria; **não** administra devedores, contratos, empréstimos, motor financeiro, cobranças ou relatórios financeiros (Core Domain exclusivo — BR-007).
- Mapeamento contexto: **Platform** (contexto primário) + **IAM** (autorização) — ambos listados no FOUNDATION-009 §5.
- O que precisa mudar é apenas a **estrutura interna de Épicos**, não a capacidade.

**Justificativa se houvesse reprovação (não é o caso):** a capacidade seria questionada apenas se "Usuários/Perfis/Permissões" saíssem do seu escopo — o que não ocorre: eles permanecem na capacidade, entregues via EPIC-006 (IAM), como prevê o AMP-001 §4.2 (IAM = Usuários, perfis e permissões do Platform Context).

---

# 8. Validação da Sequência de EPICs

**Veredito: ✅ consistente após o alinhamento.**

Sequência global oficial (ROADMAP-ALIGNMENT-001 §5.2 + decisão §10):

| Ordem | EPIC | Conteúdo | Contexto | Estado |
|-------|------|----------|----------|--------|
| 1 | EPIC-001 | Gerenciar Tenant | Platform | Concluído |
| 2 | EPIC-006 | IAM (Usuários, Perfis, Permissões, AuthN/AuthZ) | Platform/IAM | Emergente — urgente |
| 3 | EPIC-002 | Cadastro de Devedores | Cadastro | Próximo bloco |
| 4 | EPIC-003 | Comercial/Propostas | Comercial | Futuro |
| 5 | EPIC-004 | Contratos | Contratos | Futuro |
| 6 | EPIC-005 | Empréstimos, Pagamentos, Motor | Motor Financeiro | Futuro |
| 7 | EPIC-007 | Operação Diária (Cobrança, Agenda, Comunicação, Relatórios) | Cobrança/Agenda/Comunicação/Relatórios | Futuro |

- A numeração é **global e sequencial por entrega**, não por capacidade.
- O PRODUCT-001 alinhado referenciará **EPIC-001 e EPIC-006** como seus Épicos (única capacidade que os contém), sem criar sequência própria.
- Nenhum número é alterado; nenhum EPIC novo é criado (restrição da tarefa respeitada).

---

# 9. Validação da Rastreabilidade

## 9.1 Cadeia atual (íntegra)

```
FOUNDATION-007 §3.1 (Administrar Plataforma)
   → PRODUCT-001 (Capability Administrar Plataforma)
      → EPIC-001 (Gerenciar Tenant) — concluído
         → FEATURE-001 (criar), FEATURE-002 (consultar),
           FEATURE-003 (atualizar), FEATURE-004 (inativar)
            → US-001..US-014
               → PLAN-001 / PLAN-002 / PLAN-001-EXEC / PLAN-002-EXEC
                  → Implementação (src/) → Auditorias/Discoveries
```

**Veredito:** ✅ a cadeia existente do EPIC-001 está íntegra e **não será afetada** pela atualização do PRODUCT-001 (Feature/US/EPIC-001 não mudam).

## 9.2 Lacunas de rastreabilidade identificadas

| Lacuna | Situação | Ação |
|--------|----------|------|
| PRODUCT-001 sem vínculo ao FOUNDATION-009 | A raiz da camada Product não é citada | Incluir na §5 (D-07) |
| EPIC-006 (IAM) sem Features/US | Correto — EPIC emergente; Discovery futuro (BR-008) | Nenhuma; aguarda Discovery |
| EPIC-002/003/004/005 "locais" fantasmas | Referem-se a IDs que não existem globalmente | Eliminar na §6 (D-01..D-05) |
| Raio-X e discoveries FEATURE-002/003/004 citam "EPIC-002 (Usuários)" | Evidência histórica contraditória | Erratas versionadas futuras (já previstas no ROADMAP-ALIGNMENT §7) |

**Veredito geral:** ✅ rastreabilidade preservada; as lacunas são de **referência**, não de implementação.

---

# 10. Parecer Final

| Questão | Resposta | Justificativa técnica |
|---------|----------|----------------------|
| PRODUCT-001 pode ser corrigido apenas por revisão? | **Não — nova versão (v2.0.0)** | As mudanças tocam a semântica de identificação de Épicos (D-01..D-06). Nova versão preserva a trilha de decisões e o histórico do v1.0.0 (governança de erratas versionadas), evitando edição silenciosa de um documento Aprovado. |
| Precisa de nova ADR? | **Não** | Nenhuma decisão arquitetural nova: todas as diretrizes já estão aprovadas no FOUNDATION-009 (BR-001..BR-008) e no ROADMAP-ALIGNMENT-001 §10. Nova ADR seria redundância. |
| Precisa de novo Discovery? | **Não** | A capacidade já está mapeada e o EPIC-001 fechado. O Discovery do EPIC-006 (IAM) e do EPIC-002 (Cadastro) ocorrerão quando entrarem em desenvolvimento, conforme BR-006/BR-008. |
| Estimativa de risco da atualização | **Baixo** | Escopo restrito a PRODUCT-001 (§5/§6/§7/§8 + edições leves em §1/§3/§4); nenhuma Feature/US/EPIC-001 afetado; validação `docs:validate` garante consistência estrutural; o risco de *não* atualizar é maior (duplo padrão documental permanente). |

**Recomendação do arquiteto:** aprovar este relatório e, em seguida, executar a atualização do PRODUCT-001 para **v2.0.0** com as alterações das §4/§5/§6/§7/§8 (reescrita da §6 concentrando EPIC-001 + EPIC-006/IAM; referência ao FOUNDATION-009; desambiguação de Configurações; critérios de aprovação alinhados; histórico atualizado). Nenhum outro documento oficial deve ser alterado nesta rodada.

---

# 11. Histórico de Versões

| Versão | Data | Autor | Descrição |
|--------|------|-------|-----------|
| 1.0.0 | 2026-08-05 | Principal Software Architect / Product Architect / Domain Architect / CTO | Relatório de alinhamento do PRODUCT-001 ao FOUNDATION-009 — 7 divergências identificadas, classificação por tipo, seções impactadas, validação de capacidade/sequência/rastreabilidade e parecer final (nova versão v2.0.0, sem ADR, sem Discovery). |
