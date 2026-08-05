# 2026-08-04 — Handoff: EPIC-001 (Tenant Management) encerrado — FEATURE-001..004 concluídas

**Período coberto:** 2026-08-01 → 2026-08-04
**Status:** 🟢 EPIC-001 ENCERRADO (documental + código)
**Commits finais:** IMP-024..IMP-033 (sessões anteriores) + IMP-034..IMP-041 (esta sessão)

---

## Estado Atual

O **PLAN-002 (EPIC-001 — Gerenciar Tenant)** está **integralmente implementado**:

| Feature | Escopo | IMPs | Status |
|---------|--------|------|--------|
| FEATURE-001 | Criar Tenant (provisionamento) | IMP-001..023 (PLAN-001-EXEC) | Concluída |
| FEATURE-002 | Consultar Tenant (por ID, identificador, listagem) | IMP-024..028 | Concluída |
| FEATURE-003 | Atualizar Tenant (nome, PATCH) | IMP-029..032 | Concluída |
| FEATURE-004 | Inativar/Reativar Tenant | IMP-033..036 | Concluída |
| Testes/GATE | IMP-037..041 | — | Concluída |

**Suíte de testes:** 178 passed (PostgreSQL real, Docker Compose) · ruff clean · mypy clean (33 arquivos) · black clean · `docs:validate` 42 OK / 16 avisos / 0 erros · cobertura módulos FEATURE-004: estado.py 100%, routes.py 100%, main.py 94%, dependencies.py 92% (TOTAL 97%).

---

## Código entregue (camadas)

### Domain
- `src/emprestimo/domain/platform/tenant.py` — Aggregate Tenant: `ativar()`, `atualizar_nome()` (IMP-029), `inativar()` e `reativar()` (IMP-033). Máquina de estados PROVISAO → ATIVO → INATIVO; transições inválidas lançam `ViolacaoInvarianteError` (DOMAIN-017).

### Application
- `src/emprestimo/application/estado.py` — `TenantEstadoService` (IMP-034/035): `inativar(tenant_id)` e `reativar(tenant_id)` atômicos via UoW; retorna `Tenant | None`; traduz violação do Aggregate em `TransicaoEstadoInvalidaError` (409); trilha `inativar.inicio/sucesso/falha` e `reativar.inicio/sucesso/falha` (ADR-002).
- `src/emprestimo/application/atualizacao.py` — `TenantAtualizacaoService` (IMP-030/031).
- `src/emprestimo/application/errors.py` — `IdempotenciaConflitoError` (existente) + `TransicaoEstadoInvalidaError` (novo, 409).

### Presentation
- `src/emprestimo/presentation/api/routes.py` — POST `/platform/tenants/{id}/inativar` e `/reativar` (IMP-036); GET `/platform/tenants` (consulta/listagem, IMP-026/027); PATCH `/platform/tenants/{id}` (IMP-032); GET `/platform/tenants/{id}`.
- `src/emprestimo/presentation/api/main.py` — handler `TransicaoEstadoInvalidaError` → 409 `conflito_estado`; mapeamento completo: 400 payload_invalido / 404 tenant_nao_encontrado / 409 tenant_ja_existe, conflito_idempotencia, conflito_estado / 422 regra_violada / 500.
- `src/emprestimo/presentation/api/dependencies.py` — provider `get_tenant_estado_service`.
- `src/emprestimo/presentation/api/schemas.py` — `TenantCreateRequest`, `TenantResponse`, `TenantListagemParams/Response`, `TenantUpdateRequest`.

### Infrastructure (reutilizada, sem alterações na FEATURE-004)
- `SqlAlchemyUnitOfWork`, `SqlAlchemyTenantRepository`, `SqlAlchemyAuditoriaRegistro` (append-only, ADR-002), ORM/Session/Alembic.

---

## Decisões tomadas nesta sessão (FEATURE-004)

1. **Opção A mantida (TASK-078):** IMP-033 entregou `inativar()`; **`reativar()` adicionado no ciclo de slice arquitetural** (exigido pelo plano IMP-033 e pelas US-014) — domínio completo antes da Application.
2. **409 para estado divergente (IMP-036):** `ViolacaoInvarianteError` (422) do Aggregate é traduzida pela Application em `TransicaoEstadoInvalidaError` → handler no main.py responde 409 `conflito_estado`. Regra de negócio permanece no Domain; Application apenas re-enquadra o erro; Presentation mapeia HTTP.
3. **DTO único:** endpoints de estado retornam `TenantResponse` (RA-012), construído na Presentation a partir do Aggregate retornado pelo serviço (padrão idêntico ao PATCH/IMP-032).
4. **Sem corpo de request** nos endpoints de transição (POST vazio).
5. **Sem idempotência nova:** transições de estado têm idempotência natural (repetição → 409 conflito_estado), conforme IMP-036.

---

## Pendências (não bloqueiam EPIC-001)

1. **`migrations/env.py` e `pyproject.toml`** (import order / pythonpath `[".", "src"]`) — mudanças pré-existentes no working tree, nunca commitadas; revisar intenção.
2. **`tests/__init__.py`** — non-tracking; provavelmente necessário para descoberta de testes.
3. **Artefatos soltos não-rastreados:** `docs/auditorias/` (3 docs), `docs/graphify-out/`, `graphify-out/` (saída da ferramenta), `docs/implementationplans/` e `docs/implementation/plansPLAN-002-epic-001-tenant-management.md` (cópias duplicadas/corrompidas do PLAN-002) — decidir commit/ignore/remoção.
4. **Ponteiro `~/HANDOFF-VIGENTE.md` quebrado** apontava para handoff inexistente; corrigido para este documento.
5. **PEDIDO-ORIENTACAO-IMP-033-FEATURE-004.md** (docs/implementation/plans/) — pendente de resposta do Gestor sobre Opção A/B, destino dos artefatos soltos e autorização do handoff; não gera bloqueio (Opção A executada).
6. **Auditoria:** sem política de retenção/arquivamento de `audit_log` (dívida técnica registrada no ADR-002; fora do MVP).

---

## Migração da Arquitetura Documental

A arquitetura documental foi migrada para a estrutura alvo mínima aprovada:

- `docs/foundation/` — 8 documentos inalterados.
- `docs/domain/platform/` e `docs/domain/credit/` — 19 documentos DDD reorganizados por bounded context.
- `docs/product/platform/` — 14 documentos de product reorganizados por bounded context.
- `docs/architecture/amp/` — AMP, DISCOVERY, MIGRATION-PLAN e MANIFEST.
- `docs/architecture/adrs/` — ADR-001 e ADR-002.
- `docs/implementation/plans/` e `docs/implementation/backlogs/` — planos técnicos e backlogs separados.
- `docs/governance/handoffs/` e `docs/governance/decision-requests/` — handoff e pedido de orientação.
- `docs/audits/audits/` e `docs/audits/discoveries/` — auditorias e descobertas.
- `docs/templates/`, `docs/assets/`, `docs/ux/` — mantidos no local atual.

**Removidos:** duplicatas, arquivos corrompidos, `.gitkeep` vazios, `docs/graphify-out/` e `docs/handoffs/HANDOFF-VIGENTE.md` do repo.

**Validações após migração:**

| Validação | Resultado |
|-----------|-----------|
| `npm run docs:validate` | 58 OK / 31 avisos / 0 erros |
| `uv run pytest` | 178 passed |
| `uv run ruff check src tests` | All checks passed |
| `uv run black --check src tests` | 51 files unchanged |
| `uv run mypy src` | Success: no issues found |

Branch: `docs/migration-2026-08-04` — pronto para PR.

## Próximo passo

EPIC-002 (Cadastro de Devedores) pode ser iniciado sobre a nova estrutura documental. Nenhuma outra mudança arquitetural documental está prevista até que surja uma necessidade real.

---

## Histórico de Atualizações

| Data | Autor | Resumo da Atualização |
|------|-------|-----------------------|
| 2026-08-04 | Agente (sessão) | Encerramento do EPIC-001: FEATURE-004 implementada (IMP-033..036 + testes IMP-037..040 + GATE IMP-041). 178 testes verdes. Handoff substitui o anterior (fase Domain Modeling). |
