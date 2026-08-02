# FEATURE-002 — Consultar Tenant

**ID:** FEATURE-002

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Disponibilizar ao Administrador da Plataforma a capacidade de consultar as
informações institucionais dos Tenants da TiaNet, incluindo o estado
operacional de cada organização, garantindo visibilidade e governança sobre
o ciclo de vida das organizações provisionadas (EPIC-001 §3 — "consulta de
Tenant" e "consulta das informações institucionais").

A consulta serve de suporte à confirmação do provisionamento (UC-007 da
FEATURE-001) e à operação administrativa diária da plataforma.

---

# 2. Valor de Negócio

- O Administrador da Plataforma obtém, sob demanda, a situação atual de uma
  organização (identidade, estado operacional e data de criação);
- A consulta por lista permite visualizar o conjunto de organizações
  provisionadas, com paginação e filtro por estado;
- A consulta por identificador institucional permite integrar sistemas
  externos e confirmar a existência de uma organização por um dado humano e
  estável (não dependente de ID interno);
- Sem esta Feature, não há como verificar o que foi provisionado nem
  acompanhar a evolução do estado dos Tenants — comprometendo a governança
  exigida por PRODUCT-001 §3.

---

# 3. Escopo

- Consultar Tenant por ID (UUID) — endpoint já existente (IMP-018), absorvido
  como responsabilidade funcional desta Feature (DA-001);
- Consultar Tenant por identificador institucional — endpoint específico
  (DA-002);
- Listar Tenants com paginação, ordenação determinística e filtro por estado
  operacional (DA-003);
- Retornar apenas dados institucionais e de estado operacional via DTO mínimo
  (id, identificador_institucional, nome, estado, criado_em) — sem expor
  dados internos de infraestrutura (DA-004);
- Suporte ao fluxo de confirmação da criação (FEATURE-001, UC-007).

---

# 4. Fora do Escopo

- Atualização de dados cadastrais (FEATURE-003);
- Ativação/inativação de Tenant (FEATURE-004);
- Exposição de Usuários, Carteiras ou Configurações do Tenant (EPIC-002,
  EPIC-003, EPIC-005);
- Autenticação e autorização (EPIC-006);
- Auditoria de consulta (apenas escrita é auditada — ADR-002);
- Qualquer operação de escrita no Tenant.

---

# 5. User Stories

- US-009 — Consultar Tenant por ID (UC-001): obter dados institucionais,
  estado atual e data de criação de um Tenant conhecido;
- US-010 — Consultar Tenant por identificador institucional (UC-002):
  obter o Tenant a partir do dado estável da organização;
- US-011 — Listar Tenants (UC-003): relação paginada, ordenada e filtrável
  por estado operacional.

Critérios de aceitação transversais:

- leitura sem efeitos colaterais e sem exposição de dados internos (RA-012);
- 404 para Tenant inexistente;
- listagem paginada com ordenação determinística;
- consistência com o DTO único de resposta.

---

# 6. Dependências

- FEATURE-001 — Criar Tenant (produz os dados consultados; GET por ID já
  parcialmente exposto via IMP-018);
- EPIC-001 — Gerenciar Tenant (guarda o escopo da Feature);
- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant (isolamento);
- DOMAIN-017 — Aggregate Tenant (estado operacional e invariantes);
- DECISION-001 / ADR-001 — stack e arquitetura (camadas Presentation →
  Application → Domain → Infrastructure);
- ADR-002 — Auditoria Independente da Transação (define que consultas de
  leitura não geram trilha de auditoria nesta Feature).

---

# 7. Critérios de Aprovação

Esta Feature será considerada aprovada quando:

- US-009, US-010 e US-011 estiverem implementadas e testadas;
- os endpoints respeitarem o contrato HTTP definido:
  - `GET /platform/tenants/{id}` — 200 com DTO TenantResponse; 404 para
    inexistente;
  - `GET /platform/tenants?identificador_institucional={id}` — 200 com
    DTO TenantResponse; 404 para inexistente;
  - `GET /platform/tenants` — 200 com lista paginada; parâmetros:
    `page`, `size`, `sort`, `estado`;
- o DTO de resposta for único (TenantResponse) e não expuser dados
  internos (DA-004);
- a listagem for paginada, ordenada de forma determinística e aceitar
  filtro por estado operacional (DA-003);
- a consulta por identificador institucional estiver disponível via endpoint
  dedicado (DA-002);
- o endpoint `GET /platform/tenants/{id}` existente (IMP-018) for absorvido
  como responsabilidade desta Feature, sem reimplementação (DA-001);
- a autorização permanecer dependente de EPIC-006, utilizando o mecanismo
  provisório do MVP até lá (DA-005);
- não houver regras de negócio na camada Presentation;
- cobertura de testes ≥ 90% para os novos endpoints;
- `npm run docs:validate` executado sem novos erros.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 0.1.0 | 2026-08-02 | Estrutura inicial (rascunho) |
| 1.0.0 | 2026-08-02 | Materialização oficial da FEATURE-002 baseada no Discovery aprovado (AG-007) |

---