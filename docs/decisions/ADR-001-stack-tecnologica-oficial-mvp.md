# ADR-001: Stack Tecnológica Oficial do MVP

> **Status:** Aceito
> **Data:** 2026-08-01
> **Autor(es):** Head de Produto
> **Revisor(es):** [Revisor(es)]
> **Aprovação:** Head de Produto / 2026-08-01
> **Substitui:** N/A
> **Substituído por:** N/A

---

## Contexto

O projeto inicia a implementação da FEATURE-001 (Criar Tenant) e não possuía decisão formal de stack.

O MVP será um Monólito Modular: Domain totalmente independente de frameworks, Application orquestrando casos de uso, Infrastructure implementando persistência e Presentation expondo a API.

### Fatores Relevantes

- **Técnicos:** sem código existente; decisão precisa anteceder a TASK-041; Domain não deve conhecer FastAPI nem SQLAlchemy.
- **Negócio:** escopo do MVP (FOUNDATION-008) restrito a Multi-Tenant Nível 1; sem mensageria ou microservices.
- **Organizacionais:** padronização da equipe em Python; ferramentas de qualidade definidas (Ruff, Black, Mypy, Pre-commit).
- **Temporais:** decisão congelada antes do início da implementação; sem necessidade de nova aprovação para a TASK-041.

---

## Decisão

**Decidimos que:** a stack tecnológica oficial do MVP é:

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Uvicorn;
- **Banco de Dados:** PostgreSQL 16;
- **Frontend:** React 18, TypeScript, Vite (camada futura);
- **Autenticação:** JWT (Bearer Token) + Refresh Token — implementação pertence ao EPIC-006 e não será antecipada;
- **Persistência:** Repository Pattern, Unit of Work, Dependency Injection nativa do FastAPI;
- **Arquitetura:** camadas Presentation → Application → Domain → Infrastructure; Domain independente de frameworks;
- **Testes:** Pytest, HTTPX, Factory Boy, Coverage;
- **Qualidade:** Ruff, Black, Mypy, Pre-commit;
- **Containers:** Docker + Docker Compose com serviços mínimos `api` e `postgres`; Redis fora do MVP.

### Justificativa

- Stack madura e coesa para DDD em Python, com tipagem forte (mypy) e qualidade automatizada.
- PostgreSQL 16 cobre as constraints do PLAN-001 §5 (unicidade, FKs) sem dependências externas.
- Monólito Modular atende o MVP sem o custo operacional de mensageria/microservices, mantendo portas abertas para Saga (AD-001) após separação física de contextos.

---

## Alternativas Consideradas

| Opção | Descrição | Prós | Contras | Por que não escolhida |
|-------|-----------|------|---------|----------------------|
| Python + Django/DRF | Framework full-stack | Baterias incluídas | Acoplamento ao ORM próprio; menos fino para DDD | Stack escolhida exige Domain desacoplado de framework |
| Node.js + TypeScript | Stack do tooling atual do repo (docs) | JS unificado | Sem decisão de portas; domínio rico mais verboso | Não atende requisitos de DDD rigoroso do time |
| Java + Spring Boot | DDD clássico em JVM | Ecossistema enterprise | Toolchain pesada para o MVP | Stack escolhida: leve e padronizada |
| Python + FastAPI + SQLAlchemy (Escolhida) | Stack leve, tipada e modular | Domain puro, ORM plugável, qualidade automatizada | Requer disciplina de camadas | — |

---

## Consequências

### Positivas

- Domain 100% independente de frameworks (FastAPI, SQLAlchemy), testável sem infraestrutura.
- Repository Pattern + Unit of Work suportam a transação única (AD-001) e a evolução futura para Saga.
- Qualidade automatizada (Ruff, Black, Mypy, Pre-commit) desde a primeira linha de código.

### Negativas / Riscos

- Custo inicial de setup (Alembic, Docker Compose, tooling) — *Mitigação: setup feito na TASK-041.*
- PostgreSQL exige container/ambiente para testes de integração — *Mitigação: Docker Compose com `postgres` e healthcheck.*
- Sem mensageria no MVP, eventos de domínio ainda não têm transporte — *Mitigação: eventos seguem modelados no domínio; transporte é decisão futura.*

### Neutras / Trade-offs

- Frontend (React/Vite) fica em repositório de camada própria ou separado; não afeta a Fase 1.
- Redis fora do MVP; cache/background podem entrar sem quebra de camadas.

---

## Plano de Implementação

| Etapa | Descrição | Responsável | Prazo | Status |
|-------|-----------|-------------|-------|--------|
| 1 | Registrar esta decisão (ADR-001) | Agente | 2026-08-01 | Concluído |
| 2 | Implementar TASK-041 (IMP-001..IMP-007) conforme stack | Agente | 2026-08-01 | Em andamento |
| 3 | Configurar Docker Compose (api, postgres) e qualidade | Agente | 2026-08-01 | Pendente |

---

## Métricas de Sucesso

| Métrica | Valor Alvo | Como Medir | Frequência |
|---------|------------|------------|------------|
| Camadas desacopladas | Domain sem imports de frameworks | `mypy` + revisão de imports | Por PR |
| Cobertura de testes | ≥ 80% nas camadas implementadas | Coverage | Por fase |

---

## Validação e Revisão

- **Critério de Aceitação da Decisão:** TASK-041 implementada conforme stack; testes e qualidade rodando sem regressões.
- **Data de Revisão Prevista:** 2026-08-08
- **Responsável pela Revisão:** Head de Produto

---

## Referências

- FOUNDATION-008 — Escopo Oficial do MVP;
- PLAN-001 — Plano Técnico da FEATURE-001 (AD-001/AD-002);
- PLAN-001-EXEC — Backlog de Execução da FEATURE-001.

---

## Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-01 | Registro oficial da DECISION-001 — stack tecnológica do MVP. |
