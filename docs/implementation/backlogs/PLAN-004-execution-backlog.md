# PLAN-004-EXEC - Backlog de Execucao do Plano Prioritario do Backend

**ID:** PLAN-004-EXEC

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. Contexto

Este backlog transforma o `PLAN-004` em uma sequencia executavel para recuperar,
recertificar e preparar o backend para o EPIC-006/IAM.

A numeracao continua a sequencia do PLAN-003-EXEC, que encerrou em IMP-064.
Este backlog inicia em IMP-065.

---

# 2. Ordem Executavel

## P0 - Recuperacao tecnica imediata

### IMP-065 - Corrigir sintaxe de `Devedor.remover_contato`

- **Objetivo:** restaurar importacao do modulo `domain/credit/devedor.py`.
- **Componentes afetados:** `src/emprestimo/domain/credit/devedor.py`.
- **Criterios de conclusao:** corpo de `remover_contato` ativo; `python -m py_compile` ou teste unitario de Devedor sem erro de sintaxe.
- **Suite minima:** `uv run pytest tests/unit/domain/test_devedor.py`.

### IMP-066 - Recoletar a suite e classificar falhas reais

- **Objetivo:** separar falhas de comportamento de falhas de sintaxe.
- **Componentes afetados:** nenhum codigo obrigatorio; diagnostico da suite.
- **Criterios de conclusao:** `uv run pytest` coleta a suite; falhas restantes listadas por camada.
- **Suite minima:** `uv run pytest`.

### IMP-067 - Restaurar gate estatico minimo

- **Objetivo:** permitir que `ruff` e `mypy` executem analise real.
- **Componentes afetados:** arquivos apontados por `ruff`/`mypy` apos IMP-065.
- **Criterios de conclusao:** `uv run mypy src` roda alem da sintaxe; `ruff` tem lista final tratavel.
- **Suite minima:** `uv run mypy src`; `uv run ruff check src tests`.

## P1 - Persistencia de soft-delete de Contato

### IMP-068 - Criar migration aditiva para `contato.removido_em`

- **Objetivo:** alinhar Alembic ao ORM atual.
- **Componentes afetados:** nova migration `migrations/versions/0006_contato_removido_em.py`.
- **Criterios de conclusao:** coluna nullable criada no upgrade e removida no downgrade.
- **Suite minima:** novo teste de migration ou ciclo manual documentado.

### IMP-069 - Cobrir soft-delete em repositorio

- **Objetivo:** provar persistencia e releitura de `removido_em`.
- **Componentes afetados:** `tests/integration/repositories/test_devedor_repository.py`.
- **Criterios de conclusao:** contato removido e gravado com `removido_em`; leitura preserva historico quando necessario.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_devedor_repository.py`.

### IMP-070 - Cobrir soft-delete em Application e API

- **Objetivo:** provar que atualizacao de contatos substitui a colecao publica sem perder trilha.
- **Componentes afetados:** `tests/integration/application/test_devedor_application.py`, `tests/integration/api/test_api_devedores.py`.
- **Criterios de conclusao:** contato removido nao aparece no DTO publico, mas permanece rastreavel no historico/estado persistido conforme regra.
- **Suite minima:** testes de application e API de Devedor.

## P2 - Recertificacao do EPIC-002

### IMP-071 - Revalidar idempotencia por escopo

- **Objetivo:** provar que `(chave, escopo)` e a identidade real da Idempotency-Key.
- **Componentes afetados:** testes de application/repository existentes ou novos.
- **Criterios de conclusao:** mesma chave em escopos distintos e aceita; mesma chave no mesmo escopo conflita; replay retorna resultado original.
- **Suite minima:** testes unitarios e integracao de cadastro, atualizacao e estado de Devedor.

### IMP-072 - Revalidar auditoria e historico cadastral

- **Objetivo:** provar inicio/sucesso/falha nas escritas e leitura de historico sem nova escrita.
- **Componentes afetados:** `tests/integration/application/test_devedor_application.py`, `tests/unit/application/test_historico_devedor.py`.
- **Criterios de conclusao:** eventos esperados na trilha append-only; consulta de historico pura.
- **Suite minima:** testes de application e historico.

### IMP-073 - Regressao completa EPIC-001 + EPIC-002

- **Objetivo:** garantir que Tenant e Devedor estao verdes juntos.
- **Componentes afetados:** suites existentes.
- **Criterios de conclusao:** `uv run pytest` verde.
- **Suite minima:** suite completa.

### IMP-074 - Recertificar quality gate

- **Objetivo:** atualizar a evidencia de qualidade.
- **Componentes afetados:** documentacao de gate/handoff futura.
- **Criterios de conclusao:** `pytest`, `ruff`, `black`, `mypy`, `docs:validate` e `docs:test` verdes ou baseline formal aprovado.
- **Suite minima:** todos os comandos de gate.

## P3 - EPIC-006/IAM

### IMP-075 - Criar plano tecnico detalhado do EPIC-006

- **Objetivo:** decompor FEATURE-009..012 em backlog tecnico.
- **Componentes afetados:** novo plano/backlog especifico de IAM, se aprovado.
- **Criterios de conclusao:** escopo, migrations, APIs, dominio, aplicacao e suites definidos.
- **Suite minima:** `npm run docs:validate`.

### IMP-076 - Criar suites de dominio IAM

- **Objetivo:** preparar testes para Credencial, Sessao, Perfil e Permissao antes da implementacao.
- **Componentes afetados:** novos testes unitarios em `tests/unit/domain`.
- **Criterios de conclusao:** testes cobrindo invariantes de seguranca, inicialmente falhando se aplicavel.
- **Suites novas:** `test_credencial.py`, `test_sessao.py`, `test_perfil.py`, `test_permissao.py`.

### IMP-077 - Criar suites de API de autenticacao

- **Objetivo:** cobrir login, refresh, logout e recusas uniformes.
- **Componentes afetados:** novo `tests/integration/api/test_api_auth.py`.
- **Criterios de conclusao:** contratos 200/401 e ausencia de vazamento sobre usuario inexistente.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_auth.py`.

### IMP-078 - Criar suites de autorizacao e protecao de endpoints

- **Objetivo:** provar 401 sem token, 403 sem permissao e 404 cross-tenant.
- **Componentes afetados:** novos testes de API/autorizacao.
- **Criterios de conclusao:** 13 endpoints protegidos; `/health` publico.
- **Suites novas:** `test_api_authorization.py`, `test_api_protected_endpoints.py`, `test_cross_tenant_isolation.py`.

## P4 - Operacao e automacao

### IMP-079 - Criar pipeline de qualidade

- **Objetivo:** tornar os gates repetiveis fora da maquina local.
- **Componentes afetados:** configuracao de CI futura.
- **Criterios de conclusao:** pipeline executa `pytest`, `ruff`, `black`, `mypy`, `docs:validate`, `docs:test`.
- **Suite minima:** execucao do pipeline ou simulacao local.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `.github/workflows/quality.yml` executa suite Python,
  Ruff, Black, Mypy e gates documentais com PostgreSQL service container.

### IMP-080 - Criar rotina de validacao de migrations

- **Objetivo:** evitar divergencia ORM x Alembic.
- **Componentes afetados:** script ou documentacao operacional.
- **Criterios de conclusao:** ciclo upgrade/downgrade/upgrade reproduzivel.
- **Suite minima:** teste/script de migration.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `scripts/validate_migrations.py` e
  `docs/operations/quality-gates-and-migrations.md`.

## P5 - Preparacao do proximo ciclo de credito

### IMP-081 - Definir plano tecnico do proximo ciclo pos-IAM/P4

- **Objetivo:** preparar o proximo pacote depois de IAM e P4 sem pular a ordem
  oficial do roadmap.
- **Componentes afetados:** novo plano futuro para o Discovery/SDD do
  Epico 003 Comercial, com Contratos e Motor Financeiro explicitamente fora do
  primeiro ciclo.
- **Criterios de conclusao:** plano tecnico registra ordem, fronteiras, suites
  previstas e guardrails antes da implementacao.
- **Suite minima:** `npm run docs:validate`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `docs/implementation/plans/PLAN-008-proximo-ciclo-pos-iam-p4.md`.

---

# 3. Suites Novas Consolidadas

| Suite | Prioridade | Tarefa |
|---|---|---|
| `tests/integration/migrations/test_contato_removido_em.py` | Alta | IMP-068 |
| Smoke import da API | Alta | IMP-065/066 |
| `tests/integration/api/test_api_auth.py` | Alta | IMP-077 |
| `tests/integration/api/test_api_authorization.py` | Alta | IMP-078 |
| `tests/integration/api/test_api_protected_endpoints.py` | Alta | IMP-078 |
| `tests/integration/api/test_cross_tenant_isolation.py` | Alta | IMP-078 |
| `tests/unit/domain/test_credencial.py` | Media | IMP-076 |
| `tests/unit/domain/test_sessao.py` | Media | IMP-076 |
| `tests/unit/domain/test_perfil.py` | Media | IMP-076 |
| `tests/unit/domain/test_permissao.py` | Media | IMP-076 |
| `tests/integration/application/test_iam.py` | Media | plano IAM detalhado |

---

# 4. Historico de Versoes

| Versao | Data | Descricao |
|---------|------|-----------|
| 1.2.0 | 2026-08-09 | IMP-081 concluido com plano tecnico do proximo ciclo pos-IAM/P4, priorizando Discovery/SDD do Epico 003 Comercial. |
| 1.1.0 | 2026-08-09 | IMP-079 e IMP-080 concluidos com workflow de qualidade, rotina destrutiva de migrations e runbook operacional. |
| 1.0.0 | 2026-08-08 | Backlog inicial do PLAN-004, com IMP-065..IMP-081 e suites de teste ausentes. |
