# PLAN-002 — Plano Consolidado de Implementação do EPIC-001

**ID:** PLAN-002

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Contexto

Este plano consolida a implementação técnica do EPIC-001 — Gerenciar Tenant, cobrindo as três
Features que completam o ciclo de vida da organização:

- FEATURE-002 — Consultar Tenant (US-009, US-010, US-011);
- FEATURE-003 — Atualizar Tenant (US-012);
- FEATURE-004 — Ativar/Inativar Tenant (US-013, US-014).

A FEATURE-001 (Criar Tenant) foi entregue pelo PLAN-001, com backlog IMP-001..IMP-023
concluído e validado por 70 testes. Este plano continua a numeração a partir de IMP-024,
preservando a rastreabilidade Product → Implementation → Código.

# 2. Referências

- PLAN-001 — Plano Técnico da FEATURE-001 (AD-001 transação única, AD-002 Idempotency Key,
  AD-004 Auditoria);
- PLAN-001-EXEC — Backlog de Execução da FEATURE-001;
- ADR-001 — Arquitetura em camadas (Presentation → Application → Domain → Infrastructure);
- ADR-002 — Auditoria Independente da Transação (escrita auditada, leitura não auditada);
- EPIC-001 — Gerenciar Tenant;
- FEATURE-002 (US-009/US-010/US-011), FEATURE-003 (US-012), FEATURE-004 (US-013/US-014);
- DOMAIN-017 — Aggregate Tenant (invariantes INV-001..INV-005, estados operacionais);
- FOUNDATION-006 — Arquitetura Multi-Tenant; FOUNDATION-008 — Escopo Oficial do MVP;
- PRODUCT-001 — Capability Administrar Plataforma.

---

# 3. Situação Atual

## Já implementado (FEATURE-001) — reutilizar sem recriar

- Domain Platform: Aggregate Tenant (tenant.py) com TenantState (provisao/ativo/inativo) e
  invariantes INV-001..INV-005; entidades Usuario, Configuracao, Carteira;
  UnicidadeTenantService; metodos criar_carteira_padrao, criar_usuario_administrador,
  inicializar_configuracoes e ativar.
- Aplicação: TenantProvisioningService (provisioning.py) — transação única (AD-001),
  Idempotency-Key (AD-002) e auditoria append-only (ADR-002).
- Infraestrutura: SqlAlchemyUnitOfWork, repositorios SQLAlchemy (Tenant, Usuario,
  Configuracao, Carteira), SqlAlchemyIdempotenciaRegistro, Auditoria (audit_log).
- Presentation: routes.py (POST /platform/tenants, GET /platform/tenants/{id}), schemas.py
  (TenantCreateRequest, TenantResponse, ErroResponse), dependencies.py.
- Persistência: tabelas tenant, usuario, configuracao, carteira, idempotency_key, audit_log.

## Pendente de implementação

- FEATURE-002: GET por identificador institucional (US-010); listagem paginada com filtro de
  estado (US-011). O GET por ID (US-009) já existe (IMP-018).
- FEATURE-003: atualização cadastral do nome via PATCH (US-012).
- FEATURE-004: transições de estado inativar/reativar (US-013, US-014).

---

# 4. Decisões de Arquitetura

## DA-201 — Reuso integral da infraestrutura da FEATURE-001

Nenhum componente existente será recriado: agregado, repositorios, Unit of Work, auditoria,
idempotencia, DTOs e padrão de erros são reaproveitados. As novas operações usam a mesma
transação única do UoW (AD-001) e a mesma trilha append-only (ADR-002).

## DA-202 — Leitura sem auditoria

Consultas (FEATURE-002) não geram trilha de auditoria (ADR-002 — somente escrita é auditada).

## DA-203 — DTO único de resposta

Todas as operações respondem com TenantResponse (DA-004 da FEATURE-002), sem expor dados
internos de infraestrutura.

## DA-204 — Transições de estado exclusivas no Domain

Inativar e reativar são métodos do Aggregate Tenant, respeitando a máquina de estados
(Ativo → Inativo; Inativo → Ativo); estados divergentes geram ViolacaoInvarianteError.

## DA-205 — Contratos HTTP

- FEATURE-002: GET /platform/tenants?identificador_institucional={valor}; GET
  /platform/tenants?page=&size=&sort=&estado= (200 com lista paginada; 404 para inexistente);
- FEATURE-003: PATCH /platform/tenants/{id} (200 com TenantResponse; 404; 422);
- FEATURE-004: POST /platform/tenants/{id}/inativar e POST /platform/tenants/{id}/reativar
  (200 com TenantResponse; 404; 409 para estado divergente).

---

# 5. Modelo de Dados

Nenhuma migração é necessária: as colunas existentes (tenant.estado, tenant.nome) suportam as
três Features. O estado reutiliza a coluna existente com os valores provisao/ativo/inativo.

---

# 6. API

- GET /platform/tenants/{id} — existente (IMP-018), absorvido pela FEATURE-002;
- GET /platform/tenants?identificador_institucional={valor} — novo (US-010);
- GET /platform/tenants — lista paginada (page, size, sort, estado) — novo (US-011);
- PATCH /platform/tenants/{id} — atualiza nome (US-012);
- POST /platform/tenants/{id}/inativar — transição Ativo → Inativo (US-013);
- POST /platform/tenants/{id}/reativar — transição Inativo → Ativo (US-014).

---

# 7. Estratégia de Testes

- Unitários de domínio: atualização do nome, transições de estado (inativar/reativar),
  rejeição de estados divergentes, imutabilidade do identificador institucional;
- Integração: atualização e transições em transação única via UoW, com auditoria completa;
- API: contratos HTTP das três Features (200/201/404/409/422), serialização com DTO único;
- Regressão: suíte completa da FEATURE-001 permanece verde (70 testes + novos);
- cobertura ≥ 90% nos novos endpoints; npm run docs:validate sem novos erros.

---

# 8. Ordem de Implementação

1. FEATURE-002 — consulta (mais simples, desbloqueia as demais);
2. FEATURE-003 — atualização cadastral;
3. FEATURE-004 — transições de estado;
4. Verificação final: suíte completa, cobertura e validação da documentação.

---

# 9. Riscos

| Risco | Mitigação |
|-------|-----------|
| Recriar componentes existentes | Reuso integral (DA-201) — nada duplicado |
| Transição de estado inválida | Regra exclusiva no Domain (DA-204) + testes |
| Corrida em atualização/transição concorrente | Transação única via UoW |
| Exposição de dados internos | DTO único TenantResponse (DA-203) |
| Paginação sem ordenação determinística | Ordenação por criado_em + id |
| Auditoria incompleta | Eventos inicio/sucesso/falha em todas as escritas |

---

# 10. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 03/08/2026 | Plano Consolidado de Implementação do EPIC-001 — FEATURE-002/003/004, reutilizando a infraestrutura da FEATURE-001 com backlog continuado IMP-024+. |
