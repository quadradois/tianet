# PEDIDO DE ORIENTAÇÃO — FEATURE-004 (Inativar/Reativar Tenant) — IMP-033

**Data:** 2026-08-04
**Solicitante:** Engenharia (sessão de execução do PLAN-002 — EPIC-001)
**Destinatário:** Gestor/Head de Produto
**Status:** Aguardando orientação

---

## 1. Contexto

Estamos executando o **PLAN-002 — EPIC-001 (Gerenciar Tenant)**. O estado atual:

| ITEM | STATUS | COMMIT |
|------|--------|--------|
| FEATURE-001 (Criar Tenant) | Concluída | — |
| FEATURE-002 (Consultar Tenant) — IMP-024..028 | Concluída | até `cad4362` |
| FEATURE-003 (Atualizar Tenant) — IMP-029..032 | Concluída | até `61a78ac` |
| FEATURE-004 (Inativar/Reativar) — IMP-033 em diante | **Iniciando** | — |

A **TASK-078** chegou solicitando exclusivamente a **IMP-033** (camada Domain).

---

## 2. Divergência de escopo identificada (decisão solicitada)

### O que diz o plano (backlog)
> **IMP-033 — Implementar transições de estado no Aggregate Tenant**
> adicionar `inativar()` **e** `reativar()` ao `Tenant`.

### O que diz a TASK-078
> "Implementar exclusivamente a capacidade de **inativação**…"
> **Fora do escopo — Não implementar:** reativação, endpoint, auditoria, Application, Infrastructure.

### Pergunta ao Gestor
O plano prevê abertura de `inativar()` + `reativar()` **juntas** na IMP-033;
a tarefa escopa **somente inativação** (`ATIVO → INATIVO`) nesta rodada.

**Opção A (segue a tarefa — recomendada):** implementar agora apenas
`Tenant.inativar()`. A reativação (`INATIVO → ATIVO`) fica como IMP futura
(ex.: IMP-034/035), preservando o ciclo incremental por camada.

**Opção B (segue o backlog literal):** implementar `inativar()` + `reativar()`
na IMP-033. Acelera a FEATURE-004, porém amplia o escopo da tarefa atual.

> **Recomendação:** Opção A. Mantém consistência com o fluxo atual (camada a
> camada, revisão arquitetural por IMP) e atende literalmente a TASK-078.

---

## 3. Decisões já tomadas na execução (para ciência)

1. A TASK-078 pede **a transição reversível futuramente** — o `inativar()`
   será implementado preservando todos os dados, permitindo reativação depois.
2. `ViolacaoInvarianteError` será lançado para transições inválidas
   (ex.: `PROVISAO → INATIVO`, `INATIVO → INATIVO`), seguindo o padrão do
   `ativar()` existente.
3. Nenhum outro atributo (nome, identificador, cadastro completo) será alterado.

---

## 4. Pendências de repositório (orientação adicional)

Foram encontrados artefatos soltos no working tree, não relacionados às
Features concluídas. Peço orientação sobre o destino de cada um:

| Item | Natureza | Situação |
|------|----------|----------|
| `migrations/env.py`, `pyproject.toml` | Mudanças pré-existentes (import order / pythonpath) | Modificados, sem commit |
| `tests/__init__.py` | Provavelmente necessário para descoberta de testes | Non-tracking |
| `docs/auditorias/` (3 docs: raio-x, as-is-to-be, discovery ADR-003) | Análises de arquitetura | Non-tracking |
| `docs/graphify-out/`, `graphify-out/` | Saída da ferramenta graphify | Non-tracking |
| `docs/implementationplans/` (pasta duplicada) e `docs/implementation/plansPLAN-...md` (nome "colado") | Cópia corrompida/duplicada do PLAN-002 | Non-tracking |

**Recomendação provisória:** manter fora dos commits de Feature (como feito até
aqui), salvo decisão de incorporá-los ao repositório como documentação oficial.

---

## 5. Handoff

O ponteiro `~/HANDOFF-VIGENTE.md` apontava para um arquivo **inexistente**
(`2026-08-03-handoff-sessao-worker-loop-remediacao-fechada.md`). foi corrigido
para `docs/handoffs/HANDOFF-VIGENTE.md`, porém seu conteúdo está desatualizado
(reflete a fase de Domain Modeling, não o PLAN-002 em execução).

**Ação recomendada:** autorizar a atualização do handoff com o estado real do
projeto (FEATURES-001..004) no encerramento desta fase.

---

## 6. Decisões pedidas (síntese)

1. Escopo da IMP-033: **Opção A** (só inativar) ou **Opção B** (inativar + reativar)?
2. Destino dos artefatos soltos (seção 4): commitar, ignorar ou remover?
3. Autoriza atualizar o handoff para o estado real? (seção 5)

Aguardando retorno para prosseguir com a IMP-033.