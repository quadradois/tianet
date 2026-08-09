# PLAN-007 - Relatorio de Recertificacao PLAN-005/EPIC-006 - 2026-08-09

**ID:** PLAN-007

**Plano recertificado:** PLAN-005

**Versao:** 1.7.0

**Status:** Concluido

## Resultado

O EPIC-006/IAM foi recertificado novamente em 2026-08-09 apos uma segunda
auditoria adversarial refutar a primeira conclusao integral. O backend deixou de depender de
acesso anonimo nos endpoints de negocio e passou a cobrir credenciais,
autenticacao, refresh token, perfis, permissoes, Principal autenticado,
autorizacao RBAC, isolamento cross-tenant, ativacao descartavel, gestao operacional
de Perfis/Permissoes, auditoria persistida das recusas 401/403/404 e bootstrap
operacional seguro do primeiro Administrador da Plataforma. O contrato publico
OpenAPI agora explicita os corpos de erro `ErroResponse` para autenticacao,
autorizacao e recursos ocultos por isolamento. A suite completa de endpoints
protegidos tambem foi recertificada apos validar o PostgreSQL local do compose.
Com o Postgres saudavel, a recertificacao global do backend passou novamente.
O EPIC-006/IAM esta formalmente encerrado no produto, no plano tecnico e no
backlog de execucao.

## Escopo Recertificado

| IMP | Resultado | Evidencia principal |
|-----|-----------|---------------------|
| IMP-082 | Credencial concluida | `tests/unit/domain/test_credencial.py` |
| IMP-083 | Sessao concluida | `tests/unit/domain/test_sessao.py` |
| IMP-084 | PerfilAcesso e Permissao concluidos | `tests/unit/domain/test_perfil.py`, `tests/unit/domain/test_permissao.py` |
| IMP-085 | Migrations IAM concluidas | `tests/integration/migrations/test_iam_schema.py` |
| IMP-086 | Repositories IAM concluidos | `tests/integration/repositories/test_iam_repositories.py` |
| IMP-087 | Gestao de credenciais concluida | `tests/unit/application/test_credenciais.py` |
| IMP-088 | Autenticacao concluida | `tests/unit/application/test_autenticacao.py`, `tests/integration/application/test_autenticacao_integration.py` |
| IMP-089 | Autorizacao concluida | `tests/unit/application/test_autorizacao.py` |
| IMP-090 | API de autenticacao concluida | `tests/integration/api/test_api_auth.py` |
| IMP-091 | Endpoints existentes protegidos | `tests/integration/api/test_api_protected_endpoints.py` |
| IMP-092 | RBAC e cross-tenant cobertos | `tests/integration/api/test_api_authorization.py` |
| IMP-093 | Recertificacao final concluida | este relatorio e gates abaixo |
| IMP-094 | Ativacao inicial segura concluida | `test_api_iam_management.py` |
| IMP-095 | API de credenciais concluida | `test_api_iam_management.py` |
| IMP-096 | FEATURE-011 operacional concluida | `test_api_iam_management.py` |
| IMP-097 | Auditoria persistida de negativas concluida | `test_api_authorization.py` |
| IMP-098 | Recertificacao corrigida concluida | este relatorio e gates abaixo |
| IMP-099 | Bootstrap seguro do Administrador da Plataforma concluido | `test_bootstrap_plataforma.py`, `test_bootstrap_plataforma_integration.py` e runbook operacional |
| IMP-100 | Contratos OpenAPI de erros IAM/autorizacao concluidos | `test_api_protected_endpoints.py` |
| IMP-101 | Suite completa de endpoints protegidos recertificada | `test_api_protected_endpoints.py` |
| IMP-102 | Recertificacao global do backend concluida | suite Python completa e gates globais |
| IMP-103 | Fechamento formal do EPIC-006/IAM concluido | EPIC, plano, backlog e este relatorio |

## Matriz de Aceite

| Contrato | Estado | Evidencia |
|----------|--------|-----------|
| `/health` publico | Aprovado | `test_api_protected_endpoints.py` |
| Login, refresh e logout | Aprovado | `test_api_auth.py` |
| 401 uniforme | Aprovado | auth invalido, token ausente, malformado e expirado cobertos |
| 403 sem permissao | Aprovado | matriz dos 13 endpoints protegidos em `test_api_authorization.py` |
| 404 cross-tenant | Aprovado | Carteira de outro Tenant responde 404 antes de 403 |
| OpenAPI 401/403/404 | Aprovado | `test_openapi_declara_contratos_de_erro_iam_autorizacao` |
| Credencial sem texto legivel | Aprovado | testes de dominio, aplicacao, API e auditoria de auth |
| Refresh revogavel | Aprovado | unit e API auth cobrem refresh/logout |
| RBAC por Perfil/Permissao | Aprovado | domain, repositories, application e API authorization |

## Gates Observados

- `uv run ruff check .`: passou.
- `uv run black --check .`: passou, 121 arquivos sem alteracao.
- `uv run mypy src tests`: passou, 112 source files sem issues.
- `uv run pytest -q`: passou, 596 testes.
- `uv run pytest --collect-only -o addopts=""`: 596 testes coletados.
- `npm run docs:validate`: 140 verificacoes OK, 47 avisos, 0 erros.
- `npm run docs:test`: 42/42 testes documentais passaram.
- `python -m pytest tests/integration/api/test_api_protected_endpoints.py::test_openapi_declara_bearer_somente_nas_rotas_protegidas tests/integration/api/test_api_protected_endpoints.py::test_openapi_declara_contratos_de_erro_iam_autorizacao -q`: passou.
- `python -m pytest tests/integration/api/test_api_protected_endpoints.py -q`:
  passou, 10 testes.

## Consolidacoes

- A rodada adversarial final encontrou e levou a correcao de backfill para
  usuarios legados, remocao do fallback textual de RBAC, login identificado por
  Tenant, bloqueio de Tenant inativo, isolamento das rotas de Tenant, consumo
  atomico do token de ativacao, revogacao de sessoes e Bearer no OpenAPI.
- A ultima rodada separou Administrador da Plataforma de Administrador do
  Tenant, restaurou o ciclo autenticado de inativacao/reativacao global,
  traduziu corrida de nome de Perfil para 409 e removeu divergencia entre
  metadata e schema Alembic.

- A suite planejada `tests/integration/application/test_iam.py` foi consolidada
  em suites mais especificas: `test_autenticacao_integration.py`,
  `test_iam_repositories.py`, `test_iam_schema.py` e suites unitarias de
  aplicacao IAM.
- A suite planejada `tests/integration/api/test_cross_tenant_isolation.py` foi
  consolidada em `tests/integration/api/test_api_authorization.py`, pois a
  fronteira cross-tenant e a autorizacao HTTP sao exercidas pelo mesmo ponto de
  controle.

## Caveats

- O validador documental segue com 47 avisos historicos de referencias futuras,
  buracos de numeracao e namespaces legados, mas com 0 erros.
- A suite Python segue com um aviso externo de deprecacao do
  `fastapi.testclient`/Starlette.
- O worktree contem mudancas acumuladas de IMPs anteriores; esta recertificacao
  registra o estado tecnico observado, nao uma atribuicao de autoria por diff.
- O bootstrap permanece deliberadamente fora da API e deve ser executado pela
  operacao conforme `docs/operations/bootstrap-administrador-plataforma.md`.
- A execucao completa de `tests/integration/api/test_api_protected_endpoints.py`
  exigiu PostgreSQL local em `localhost:5432`; com `emprestimo-postgres-1`
  healthy, a suite completou sem travar.

## Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.7.0 | 2026-08-09 | Fecha IMP-103 com encerramento formal do EPIC-006/IAM nos documentos de produto e execucao. |
| 1.6.0 | 2026-08-09 | Fecha IMP-102 com recertificacao global do backend e gates completos verdes. |
| 1.5.0 | 2026-08-09 | Fecha IMP-101 com recertificacao da suite completa de endpoints protegidos. |
| 1.4.0 | 2026-08-09 | Fecha IMP-100 com contratos OpenAPI de 401/403/404 e teste de regressao. |
| 1.3.0 | 2026-08-09 | Fecha IMP-099 com bootstrap singleton, credencial atomica e correcoes adversariais P0/P1. |
| 1.2.0 | 2026-08-09 | Fecha IMP-098 apos corrigir os achados P0/P1 da rodada adversarial final. |
| 1.1.0 | 2026-08-09 | Corrige a recertificacao apos segunda auditoria encontrar FEATURE-010/011 incompletas. |
| 1.0.0 | 2026-08-09 | Recertificacao final do EPIC-006/IAM apos IMP-092. |
