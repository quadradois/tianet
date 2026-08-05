# Auditoria As-Is / To-Be — Ecossistema TiaNet

> **Data da auditoria:** 2026-08-03
> **Escopo:** visão holística do ecossistema (documentação, código, testes, infraestrutura, tooling, processo)
> **Branch:** `master`
> **Último commit considerado:** `a08d499` (TASK-065 — ADR-002)

---

## 1. Resumo Executivo

O projeto TiaNet encontra-se em um estado **documentalmente maduro** e **tecnicamente consolidado** na camada de provisionamento de Tenant (FEATURE-001). O ciclo de vida completo do EPIC-001 está documentado (criação, consulta, atualização, inativação, reativação), a arquitetura DDD em camadas está implementada e os testes passam (70/70, ~95% de cobertura no `src/`).

O salto para o **To-Be** depende essencialmente de:

1. Implementar as Features 002, 003 e 004 (já documentadas).
2. Criar planos técnicos para essas Features.
3. Evoluir a infraestrutura de operação (CI/CD, observabilidade, healthcheck real, autenticação).
4. Fechar dívidas técnicas pontuais (formatação de migrations, materialização de US-002..008, E2E).

**Veredito geral:** o ecossistema está saudável para o estágio de MVP, com de-cisões arquiteturais claras e baixo acoplamento. O maior risco é deixar a docu-mentação muito à frente do código sem um plano de implementação explícito.

---

## 2. Escopo e Metodologia

### 2.1 Áreas auditadas

- Documentação (`docs/`)
- Código-fonte (`src/`)
- Testes (`tests/`)
- Infraestrutura local (Docker Compose, migrations, Alembic)
- Tooling de qualidade (ruff, black, mypy, pre-commit, pytest, uv)
- Processo (git, commits, handoffs, gates)

### 2.2 Ferramentas de coleta

- `git log`, `git status`, `git diff --stat`
- `uv run pytest --cov=emprestimo`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src`
- `node scripts/validate-docs.js`
- Inspeção manual de arquivos-chave

---

## 3. Inventário As-Is

### 3.1 Documentação

| Camada | Quantidade | Status |
|---|---|---|
| Foundation | 8 docs | Completa (v1.0.0/v1.1.0) |
| Domain | 19 docs | Completa (v1.0.0) |
| Product | 13 docs | Completa para EPIC-001 |
| Discoveries | 3 docs | FEATURE-002, 003, 004 |
| Decisions | 2 ADRs | ADR-001, ADR-002 |
| Plans | 2 docs | PLAN-001 + PLAN-001-EXEC |
| Templates | 11 templates | Padronizados |
| Handoffs | 1 handoff | Desatualizado |
| **Total** | **47 docs oficiais** | — |

### 3.2 Código-fonte

| Camada | Arquivos | Responsabilidade |
|---|---|---|
| Domain | `domain/platform/*`, `domain/credit/*`, `domain/common/*` | Aggregate Tenant, Entities, Value Objects, invariantes, ports |
| Application | `application/provisioning.py`, `application/ports.py`, `application/errors.py` | TenantProvisioningService, UoW, Auditoria, Idempotência |
| Infrastructure | `infrastructure/db/*`, `infrastructure/repositories/*`, `infrastructure/auditoria.py`, `infrastructure/idempotencia.py`, `infrastructure/unit_of_work.py` | SQLAlchemy, ORM, migrations, repositories |
| Presentation | `presentation/api/*` | FastAPI, rotas, schemas, dependências |

**Total:** ~30 módulos Python, ~608 LOC instrumentáveis (sem comentários/docstrings estimados).

### 3.3 Infraestrutura e Tooling

| Componente | Tecnologia | Status |
|---|---|---|
| Linguagem | Python 3.12 | ✅ Configurado via `requires-python` e `.venv` |
| Gerenciador de pacotes | `uv` 0.11.6 | ✅ `uv.lock` + `.venv` |
| Web framework | FastAPI 0.141.1 | ✅ |
| ORM | SQLAlchemy 2.0.51 | ✅ |
| Driver PostgreSQL | psycopg 3.3.4 | ✅ |
| Migrations | Alembic 1.18.5 | ✅ 3 revisions |
| Banco de dados | PostgreSQL 16 (Docker) | ✅ Container `emprestimo-postgres-1` healthy |
| Containerização | Docker + Docker Compose | ✅ `docker-compose.yml` (api + postgres) |
| Imagem prod | `Dockerfile` (python:3.12-slim) | ✅ |
| Linter | ruff 0.16.1 | ✅ src/tests limpos |
| Formatter | black 26.5.1 | ✅ src/tests limpos |
| Type checker | mypy 2.3.0 | ✅ `mypy src` passa |
| Test runner | pytest 9.1.1 | ✅ 70 pass |
| Pre-commit | ruff + black | ✅ Configurado |
| CI/CD | — | ❌ Ausente |
| Observabilidade | `/health` básico | ⚠️ Mínimo |
| Autenticação | — | ❌ Fora do MVP (EPIC-006) |

### 3.4 Testes

| Tipo | Quantidade | Cobertura |
|---|---|---|
| Unitários domain | 30 | Alta |
| Unitários aplicação | 6 | Alta |
| Integração API | 12 | Alta |
| Integração aplicação | 8 | Alta |
| Integração repositórios | 14 | Alta |
| **Total** | **70** | **~95% do `src/`** |

---

## 4. Matriz de Maturidade As-Is

| Área | As-Is | Maturidade | To-Be desejado |
|---|---|---|---|
| Product Discovery | Completo para EPIC-001 | 🟢 Alta | Manter ritmo para EPIC-002..006 |
| Domain Modeling | Completo (19 docs) | 🟢 Alta | Evoluir com novos contextos |
| Architecture Decisions | ADR-001 e ADR-002 formalizados | 🟢 Alta | Criar ADRs conforme surgirem |
| Implementation Plans | Apenas FEATURE-001 | 🟡 Média | Criar PLAN-002/003/004 |
| Código | FEATURE-001 implementada | 🟢 Alta | FEATURE-002/003/004 |
| Testes | 70 passando, 95% coverage | 🟢 Alta | Manter ≥80% |
| CI/CD | Ausente | 🔴 Baixa | GitHub Actions/GitLab CI |
| Observabilidade | Apenas `/health` | 🟡 Média | Logs estruturados, métricas, tracing |
| Segurança | Sem autenticação | 🔴 Baixa | JWT + RBAC (EPIC-006) |
| Documentação de operação | `.env.example`, docker-compose | 🟡 Média | README de operação, runbooks |
| Qualidade de dados | Constraints no banco | 🟢 Alta | Manter e evoluir |

---

## 5. Análise de Gaps (As-Is → To-Be)

### 5.1 Gaps funcionais

| ID | Gap | Impacto | Prioridade |
|---|---|---|---|
| GF-001 | FEATURE-002 não implementada (consulta/listagem) | Bloqueia operações administrativas | Alta |
| GF-002 | FEATURE-003 não implementada (atualização cadastral) | Impossibilita manutenção de dados | Média |
| GF-003 | FEATURE-004 não implementada (inativar/reativar) | Ciclo de vida incompleto | Média |
| GF-004 | `Tenant` só tem `ativar()`; falta `inativar()` e `reativar()` | Máquina de estados incompleta | Alta |
| GF-005 | APIs de consulta por identificador e listagem não existem | FEATURE-002 incompleta | Alta |
| GF-006 | IMP-023 (E2E do provisionamento) pendente | Cobertura de fluxo ponta-a-ponta | Baixa |

### 5.2 Gaps documentais

| ID | Gap | Impacto | Prioridade |
|---|---|---|---|
| GD-001 | US-002..US-008 não materializadas | Rastreabilidade incompleta em FEATURE-001 | Média |
| GD-002 | HANDOFF-VIGENTE desatualizado | Perda de contexto entre sessões | Alta |
| GD-003 | `docs/architecture/` vazia | Decisões técnicas de implementação não documentadas | Média |
| GD-004 | EPIC-002..EPIC-006 não existem | Visão de longo prazo fragmentada | Baixa |

### 5.3 Gaps técnicos / operacionais

| ID | Gap | Impacto | Prioridade |
|---|---|---|---|
| GT-001 | CI/CD ausente | Risco de regressão, deploy manual | Alta |
| GT-002 | `migrations/` com 9 erros de ruff e 4 de black | Dívida de formatação (arquivos gerados) | Baixa |
| GT-003 | `mypy src tests` acusa 52 erros pré-existentes | Dívida de tipagem nos testes | Baixa |
| GT-004 | Healthcheck apenas retorna `{"status":"ok"}` | Não verifica dependências (DB) | Média |
| GT-005 | Sem logs estruturados | Dificuldade de debug em produção | Média |
| GT-006 | Sem autenticação/autorização | Qualquer cliente pode chamar endpoints | Alta (pós-MVP) |
| GT-007 | `.venv` sem `pip` (uv-managed) | Curva de quem usa `pip` tradicional | Baixa |

### 5.4 Gaps de arquitetura

| ID | Gap | Impacto | Prioridade |
|---|---|---|---|
| GA-001 | Apenas `TenantProvisioningService` existe; sem serviço de consulta/atualização/inativação | Acúmulo de responsabilidade | Média |
| GA-002 | Repositórios usam `merge()` para INSERT/UPDATE; sem distinção explícita | Risco de comportamento inesperado em updates futuros | Média |
| GA-003 | `TenantRepository.find_all()` sem paginação | PERFORMANCE em grandes volumes | Média |
| GA-004 | `create_session()` expõe engine global singleton | Testabilidade e concorrência | Baixa |

---

## 6. Análise SWOT

### Strengths (Forças)

- Arquitetura DDD em camadas bem definida e respeitada.
- Documentação extensa e versionada (Foundation → Domain → Product).
- Testes automatizados com alta cobertura.
- Decisões arquiteturais registradas (ADR-001, ADR-002).
- Baixo acoplamento: Domain puro, ports/abstrações claras.
- Ambiente de desenvolvimento funcional (Docker + uv + pytest).

### Weaknesses (Fraquezas)

- Documentação muito à frente do código (3 Features documentadas, 1 implementada).
- HANDOFF desatualizado.
- CI/CD ausente.
- Dívidas técnicas em migrations e tipagem de testes.
- Repositórios usam `merge()` indiscriminadamente.

### Opportunities (Oportunidades)

- Reutilizar padrões da FEATURE-001 para acelerar 002/003/004.
- Adotar CI/CD simples (GitHub Actions) já no MVP.
- Criar um dashboard de healthcheck real (incluindo DB).
- Publicar eventos de domínio para evolução futura (Saga, mensageria).

### Threats (Ameaças)

- Divergência entre documentação e código se a implementação demorar.
- Ausência de autenticação pode levar a endpoints expostos em produção.
- Crescimento do `audit_log` sem política de retenção.
- Múltiplas versões de Python no host (3.11, 3.12, 3.14) podem causar confusão.

---

## 7. Roadmap Recomendado (To-Be)

### Fase 1 — Consolidação técnica (1-2 semanas)

1. Commitar/restaurar as correções da TASK-063 (`pyproject.toml`, `tests/__init__.py`).
2. Atualizar `HANDOFF-VIGENTE.md` com o estado real.
3. Criar pipeline CI/CD básica:
   - `uv run pytest`
   - `uv run ruff check src tests`
   - `uv run black --check src tests`
   - `uv run mypy src`
4. Melhorar healthcheck (`/health` verifica conexão com PostgreSQL).

### Fase 2 — Implementação das Features pendentes (2-4 semanas)

1. **FEATURE-002 — Consultar Tenant**
   - Criar `PLAN-002`.
   - Implementar `GET /platform/tenants/{id}` (já existe parcialmente).
   - Implementar `GET /platform/tenants?identificador_institucional=...`.
   - Implementar `GET /platform/tenants` com paginação/ordenação/filtro por estado.
   - Criar serviço de consulta e testes.
2. **FEATURE-003 — Atualizar Tenant**
   - Criar `PLAN-003`.
   - Implementar `PATCH /platform/tenants/{id}`.
   - Adicionar `atualizar_dados_cadastrais()` no Domain.
3. **FEATURE-004 — Inativar/Reativar Tenant**
   - Criar `PLAN-004`.
   - Adicionar `inativar()` e `reativar()` no Domain (máquina de estados).
   - Implementar `POST /platform/tenants/{id}/inativar` e `/reativar`.

### Fase 3 — Qualidade e operação (1-2 semanas)

1. Materializar US-002..US-008 ou consolidar na FEATURE-001.
2. Implementar IMP-023 (E2E).
3. Revisar uso de `merge()` nos repositórios.
4. Adicionar logs estruturados (`structlog` ou logging padrão com contexto).
5. Criar README de operação (`docs/implementation/operation/README.md`).

### Fase 4 — Fundação para próximos EPICs (pós-MVP)

1. Criar EPIC-002..EPIC-006 no Product.
2. Implementar autenticação/autorização (EPIC-006).
3. Avaliar separação física de contextos e Saga (evolução do AD-001).
4. Definir política de retenção do `audit_log`.

---

## 8. Métricas de Sucesso para o To-Be

| Métrica | Alvo | Como medir |
|---|---|---|
| Cobertura de testes | ≥ 80% nas camadas implementadas | `pytest --cov` |
| Documentação validada | 0 erros no `docs:validate` | `npm run docs:validate` |
| Build CI/CD | Verde em todo PR | Pipeline |
| Features implementadas | FEATURE-002, 003, 004 concluídas | Status de tarefas |
| Dívida técnica crítica | 0 | Issues/rastreamento |
| Tempo de setup de ambiente | ≤ 5 minutos | `docker compose up` + `uv run pytest` |

---

## 9. Recomendações Imediatas

1. **Commitar a TASK-063** (`pyproject.toml` + `tests/__init__.py`) para garantir que o ambiente de testes esteja versionado.
2. **Atualizar o HANDOFF-VIGENTE.md** com o estado atual (documentação completa, FEATURE-001 implementada, próximas Features pendentes).
3. **Não iniciar EPIC-002 antes de encerrar FEATURE-002/003/004** — evitar acúmulo de contexto.
4. **Criar CI/CD o quanto antes** — é o maior multiplicador de segurança neste estágio.
5. **Revisar o padrão `merge()` nos repositórios** quando implementar updates (FEATURE-003), pois pode causar comportamentos inesperados.

---

## 10. Conclusão

O ecossistema TiaNet é **saudável e bem estruturado** para um MVP. A maior força é a clareza arquitetural e a documentação alinhada; o maior desafio é transformar essa documentação em código sem perder qualidade. O caminho recomendado é:

> **Fechar a implementação do EPIC-001 (FEATURE-002 → 003 → 004) → atualizar HANDOFF → adotar CI/CD → só então avançar para EPIC-002..006.**

Isso mantém o ritmo, reduz risco de divergência doc/código e preserva a alta cobertura de testes conquistada na FEATURE-001.
