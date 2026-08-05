# PLAN-002-EXEC — Backlog de Execução do EPIC-001 (Tenant Management)

**ID:** PLAN-002-EXEC

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Contexto

Este documento decompõe o PLAN-002 em um backlog técnico executável para o EPIC-001 —
Gerenciar Tenant, cobrindo a FEATURE-002 (Consultar Tenant), a FEATURE-003 (Atualizar
Tenant) e a FEATURE-004 (Ativar/Inativar Tenant).

A numeração continua a sequência do PLAN-001-EXEC: inicia em IMP-024.

É a fonte oficial para execução: a implementação deverá ocorrer na ordem definida aqui,
permitindo rastreabilidade entre Product → Implementation → Código.

---

# 2. Referências

- PLAN-002 — Plano Consolidado de Implementação do EPIC-001;
- PLAN-001 — Plano Técnico da FEATURE-001;
- PLAN-001-EXEC — Backlog de Execução da FEATURE-001 (IMP-001..IMP-023);
- FEATURE-002, FEATURE-003, FEATURE-004;
- US-009, US-010, US-011, US-012, US-013, US-014;
- EPIC-001, PRODUCT-001, FOUNDATION-006, DOMAIN-017;
- ADR-001, ADR-002.

---

# 3. Infraestrutura — FEATURE-002 (Consultar Tenant)

## IMP-024 — Expor consulta por identificador institucional no Repositório

- **Objetivo:** implementar `find_by_identificador_institucional` no `TenantRepository`
  (SQLAlchemy) — consulta exata por índice único existente.
- **Componentes afetados:** `TenantRepository` (ports.py), `SqlAlchemyTenantRepository`.
- **Dependências:** IMP-004 (Repositório Tenant).
- **Critério de conclusão:** método retorna `Tenant | None` por identificador; consulta
  usa índice único da tabela `tenant`.

## IMP-025 — Implementar listagem paginada no Repositório

- **Objetivo:** adicionar `find_all_paginated(page, size, sort, estado)` ao `TenantRepository`
  com ordenação determinística e filtro por estado operacional.
- **Componentes afetados:** `TenantRepository` (ports.py), `SqlAlchemyTenantRepository`.
- **Dependências:** IMP-024.
- **Critério de conclusão:** retorna tupla `(items: list[Tenant], total: int)`; ordenação
  padrão `criado_em ASC, id ASC`; filtro `estado` opcional (`provisao` | `ativo` |
  `inativo`).

## IMP-026 — Endpoint GET /platform/tenants?identificador_institucional={valor}

- **Objetivo:** expor consulta por identificador institucional (US-010, DA-002).
- **Componentes afetados:** `routes.py`, `schemas.py` (query param), `dependencies.py`.
- **Dependências:** IMP-024.
- **Critério de conclusão:** responde 200 com `TenantResponse` ou 404; reutiliza DTO
  único; sem auditoria (ADR-002).

## IMP-027 — Endpoint GET /platform/tenants (listagem paginada)

- **Objetivo:** expor listagem com paginação, ordenação e filtro por estado (US-011,
  DA-003).
- **Componentes afetados:** `routes.py`, `schemas.py` (query params), `dependencies.py`.
- **Dependências:** IMP-025.
- **Critério de conclusão:** parâmetros `page` (default 1), `size` (default 20, max 100),
  `sort` (campo+dir, default `criado_em:asc`), `estado` (opcional); resposta 200 com
  envelope `{items, total, page, size, pages}`; `TenantResponse` por item.

## IMP-028 — Absorver GET /platform/tenants/{id} como responsabilidade da FEATURE-002

- **Objetivo:** documentar e manter endpoint existente (IMP-018) sob escopo desta
  Feature (DA-001) — sem alteração de código.
- **Componentes afetados:** `routes.py` (comentário/atribuição).
- **Dependências:** IMP-018 (concluído no PLAN-001).
- **Critério de conclusão:** endpoint ativo, responsivo, usando `TenantResponse`;
  nenhuma regra de negócio na Presentation.

---

# 4. Domínio — FEATURE-003 (Atualizar Tenant)

## IMP-029 — Implementar método de atualização cadastral no Aggregate Tenant

- **Objetivo:** adicionar `atualizar_nome(novo_nome: str)` ao `Tenant` (domain); valida
  não vazio, ≤ 200 chars; imutabilidade do `identificador_institucional`, `id`,
  `criado_em`, `estado`.
- **Componentes afetados:** `tenant.py` (Aggregate Tenant).
- **Dependências:** IMP-001 (Aggregate Tenant).
- **Critério de conclusão:** método atualiza apenas `nome`; lança `ViolacaoInvarianteError`
  se nome inválido; não altera outros campos.

---

# 5. Aplicação — FEATURE-003

## IMP-030 — Implementar TenantAtualizacaoService

- **Objetivo:** orquestrar atualização (buscar → atualizar domínio → persistir →
  auditar) em transação única via UoW.
- **Componentes afetados:** novo `application/atualizacao.py`, `application/ports.py`
  (novas interfaces se necessárias).
- **Dependências:** IMP-029.
- **Critério de conclusão:** fluxo atômico; retorna `TenantResponse`; eventos de
  auditoria `atualizar.inicio`, `atualizar.sucesso`, `atualizar.falha`.

## IMP-031 — Auditoria da atualização cadastral

- **Objetivo:** registrar trilha append-only da escrita (ADR-002).
- **Componentes afetados:** `AuditoriaRegistro` (infra), `TenantAtualizacaoService`.
- **Dependências:** IMP-030.
- **Critério de conclusão:** eventos `atualizar.inicio`, `atualizar.sucesso`,
  `atualizar.falha` gravados em `audit_log` na mesma transação; rollback propaga
  falha sem deixar resíduos.

---

# 6. API — FEATURE-003

## IMP-032 — Endpoint PATCH /platform/tenants/{id}

- **Objetivo:** expor atualização parcial do nome (US-012, DA-205).
- **Componentes afetados:** `routes.py`, `schemas.py` (novo `TenantUpdateRequest`),
  `dependencies.py` (inj. `TenantAtualizacaoService`).
- **Dependências:** IMP-030, IMP-031.
- **Critério de conclusão:** 200 com `TenantResponse`; 404 inexistente; 422 payload
  inválido (nome vazio ou >200); sem `Idempotency-Key` (idempotência natural).

---

# 7. Domínio — FEATURE-004 (Inativar/Reativar Tenant)

## IMP-033 — Implementar transições de estado no Aggregate Tenant

- **Objetivo:** adicionar `inativar()` e `reativar()` ao `Tenant` (domain).
  - `inativar()`: apenas se `estado == ATIVO`; transição `ATIVO → INATIVO`.
  - `reativar()`: apenas se `estado == INATIVO`; transição `INATIVO → ATIVO`.
  - Bloqueia transições inválidas (ex.: `PROVISAO → INATIVO`, `ATIVO → ATIVO`).
- **Componentes afetados:** `tenant.py` (Aggregate Tenant), `TenantState`.
- **Dependências:** IMP-001 (Aggregate Tenant), `ativar()` existente.
- **Critério de conclusão:** transições válidas mudam estado; inválidas lançam
  `ViolacaoInvarianteError` com código claro; nenhuma alteração em outros campos.

---

# 8. Aplicação — FEATURE-004

## IMP-034 — Implementar TenantEstadoService

- **Objetivo:** orquestrar transição de estado (buscar → transição domínio → persistir →
  auditar) em transação única via UoW.
- **Componentes afetados:** novo `application/estado.py`.
- **Dependências:** IMP-033.
- **Critério de conclusão:** `inativar(tenant_id)` e `reativar(tenant_id)` atômicos;
  retorna `TenantResponse`; eventos `inativar.inicio/sucesso/falha`,
  `reativar.inicio/sucesso/falha`.

## IMP-035 — Auditoria das transições de estado

- **Objetivo:** registrar trilha append-only (ADR-002).
- **Componentes afetados:** `AuditoriaRegistro`, `TenantEstadoService`.
- **Dependências:** IMP-034.
- **Critério de conclusão:** eventos de início/sucesso/falha para inativar e reativar
  gravados em `audit_log`; rollback preserva eventos de falha.

---

# 9. API — FEATURE-004

## IMP-036 — Endpoints POST /platform/tenants/{id}/inativar e /reativar

- **Objetivo:** expor transições via endpoints dedicados (DA-205).
- **Componentes afetados:** `routes.py`, `dependencies.py` (inj. `TenantEstadoService`).
- **Dependências:** IMP-034, IMP-035.
- **Critério de conclusão:** ambos respondem 200 com `TenantResponse` atualizado; 404
  inexistente; 409 se estado divergente (ex.: inativar Tenant já inativo); sem corpo
  de request.

---

# 10. Testes

## IMP-037 — Testes unitários de domínio (atualização e estado)

- **Objetivo:** cobrir `atualizar_nome`, `inativar`, `reativar`, imutabilidade de
  identificador, rejeição de estados inválidos.
- **Componentes afetados:** `tests/unit/domain/test_tenant.py` (novo/estende).
- **Dependências:** IMP-029, IMP-033.
- **Critério de conclusão:** invariantes e máquina de estados cobertas; falhas
  intencionais verificam `ViolacaoInvarianteError`.

## IMP-038 — Testes de integração (UoW, auditoria, persistência)

- **Objetivo:** validar fluxos completos de atualização e transições em transação
  única, com auditoria e rollback.
- **Componentes afetados:** `tests/integration/application/test_atualizacao.py`,
  `tests/integration/application/test_estado.py` (novos).
- **Dependências:** IMP-030, IMP-034.
- **Critério de conclusão:** atomicidade verificada; eventos de auditoria corretos
  em sucesso e falha; sem dados parciais após rollback.

## IMP-039 — Testes de API (contratos HTTP)

- **Objetivo:** validar endpoints das três Features (200/404/409/422), serialização
  com `TenantResponse` único, paginação determinística.
- **Componentes afetados:** `tests/integration/api/test_api.py` (estende), novos
  módulos se necessário.
- **Dependências:** IMP-026, IMP-027, IMP-032, IMP-036.
- **Critério de conclusão:** todos os contratos cobertos; paginação ordenada
  `criado_em,id`; filtro `estado` funcional; DTO único sem vazamento.

## IMP-040 — Testes de regressão (suíte completa)

- **Objetivo:** executar suíte total (FEATURE-001 + 002 + 003 + 004) garantindo 70+
  testes verdes sem regressão.
- **Componentes afetados:** `pytest.ini`, CI config.
- **Dependências:** IMP-037..IMP-039.
- **Critério de conclusão:** `uv run pytest` 100% pass; cobertura ≥ 90% nos novos
  endpoints; `npm run docs:validate` sem erros novos.

---

# 11. Consolidação e Encerramento

## IMP-041 — GATE técnico e atualização do HANDOFF

- **Objetivo:** validar critérios de aprovação do EPIC-001 (todas as Features
  implementadas, ciclo operacional, isolamento, aderência ao MVP); atualizar
  `docs/handoffs/HANDOFF-VIGENTE.md` com ponteiro ao novo handoff.
- **Componentes afetados:** `docs/handoffs/`, `docs/implementation/plans/`.
- **Dependências:** IMP-040.
- **Critério de conclusão:** parecer 🟢 EPIC-001 ENCERRADO (documental + código);
  HANDOFF atualizado; commit final realizado.

---

# 12. Ordem de Execução

A implementação segue a sequência IMP-024 → IMP-041, consistente com a ordem do
PLAN-002 §8 (Consulta → Atualização → Estado → Consolidação).

Cada tarefa só inicia com todas as suas dependências concluídas.

---

# 13. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 03/08/2026 | Backlog de Execução do PLAN-002 — EPIC-001, IMP-024..IMP-041. |