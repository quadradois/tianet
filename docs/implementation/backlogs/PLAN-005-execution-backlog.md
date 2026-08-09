# PLAN-005-EXEC - Backlog de Execucao do EPIC-006/IAM

**ID:** PLAN-005-EXEC

**Versao:** 1.8.0

**Status:** Concluido

---

# 1. Contexto

Este backlog transforma o `PLAN-005` em uma sequencia executavel para o
EPIC-006/IAM. A numeracao continua o PLAN-004-EXEC, que encerrou em IMP-081.

---

# 2. Ordem Executavel

## P3.1 - Dominio IAM

### IMP-082 - Criar entidade Credencial

- **Objetivo:** armazenar somente hash e metadados da credencial.
- **Componentes afetados:** `src/emprestimo/domain/platform/credencial.py`.
- **Criterios de conclusao:** nenhuma credencial legivel exposta; verificacao por hash.
- **Suite minima:** `uv run pytest tests/unit/domain/test_credencial.py`.

### IMP-083 - Criar entidade Sessao

- **Objetivo:** representar refresh token expiravel e revogavel.
- **Componentes afetados:** `src/emprestimo/domain/platform/sessao.py`.
- **Criterios de conclusao:** refresh valido, expirado e revogado cobertos.
- **Suite minima:** `uv run pytest tests/unit/domain/test_sessao.py`.

### IMP-084 - Criar PerfilAcesso e Permissao

- **Objetivo:** modelar RBAC por Perfil e Permissao de operacao.
- **Componentes afetados:** `src/emprestimo/domain/platform/perfil.py`,
  `src/emprestimo/domain/platform/permissao.py`.
- **Criterios de conclusao:** perfil ativo/inativo, permissao atribuida e permissao
  ausente cobertos.
- **Suite minima:** `uv run pytest tests/unit/domain/test_perfil.py tests/unit/domain/test_permissao.py`.

## P3.2 - Persistencia IAM

### IMP-085 - Criar migrations IAM

- **Objetivo:** adicionar tabelas de credenciais, sessoes, perfis, permissoes e
  associacoes.
- **Componentes afetados:** nova migration Alembic.
- **Criterios de conclusao:** upgrade/downgrade/upgrade reproduzivel.
- **Suite minima:** `uv run pytest tests/integration/migrations/test_iam_schema.py`.

### IMP-086 - Criar repositories IAM

- **Objetivo:** persistir e consultar credenciais, sessoes, perfis e permissoes.
- **Componentes afetados:** repositories SQLAlchemy e ports de Platform.
- **Criterios de conclusao:** round-trip real em PostgreSQL.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_iam_repositories.py`.

## P3.3 - Application IAM

### IMP-087 - Implementar gestao de credenciais

- **Objetivo:** definir credencial inicial, alterar propria credencial e redefinir
  credencial de Usuario do mesmo Tenant.
- **Componentes afetados:** services de credenciais.
- **Criterios de conclusao:** ativacao de Usuario convidado, troca e redefinicao
  auditadas.
- **Suite minima:** `uv run pytest tests/unit/application/test_credenciais.py`.

### IMP-088 - Implementar autenticacao

- **Objetivo:** login, refresh e logout com access token curto e refresh token
  persistido.
- **Componentes afetados:** services de autenticacao.
- **Criterios de conclusao:** 401 uniforme para credencial invalida, usuario
  inexistente e usuario nao ativo.
- **Suite minima:** `uv run pytest tests/unit/application/test_autenticacao.py`.

### IMP-089 - Implementar autorizacao

- **Objetivo:** resolver Principal e avaliar permissao RBAC por operacao.
- **Componentes afetados:** services/dependencies de autorizacao.
- **Criterios de conclusao:** 401, 403 e 404 cross-tenant separados.
- **Suite minima:** `uv run pytest tests/unit/application/test_autorizacao.py`.

## P3.4 - API e Retrofit

### IMP-090 - Criar API de autenticacao

- **Objetivo:** expor login, refresh e logout.
- **Componentes afetados:** rotas de autenticacao.
- **Criterios de conclusao:** contratos HTTP de FEATURE-009.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_auth.py`.

### IMP-091 - Proteger endpoints existentes

- **Objetivo:** exigir token valido nos endpoints de Platform e Credit, mantendo
  `/health` publico.
- **Componentes afetados:** dependencies/routers existentes.
- **Criterios de conclusao:** endpoints protegidos retornam 401 sem token.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_protected_endpoints.py`.

### IMP-092 - Cobrir autorizacao e cross-tenant

- **Objetivo:** provar 403 sem permissao e 404 para recurso de outro Tenant.
- **Componentes afetados:** dependencies de autorizacao e resolucao de recurso.
- **Criterios de conclusao:** nenhum vazamento de existencia cross-tenant.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_authorization.py`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `tests/integration/api/test_api_authorization.py` cobre token valido
  sem permissao, sem Perfil, Perfil inexistente, operacao Credit sem permissao,
  404 cross-tenant antes de 403 e ausencia de persistencia em tentativa
  cross-tenant.
- **Nota:** a suite de isolamento cross-tenant foi consolidada na suite de
  autorizacao HTTP porque o ponto de controle e a rota afetada sao os mesmos.

### IMP-093 - Recertificar EPIC-006/IAM

- **Objetivo:** fechar o EPIC-006/IAM com evidencias de aceite, gates globais e
  caveats documentados.
- **Componentes afetados:** relatorio de execucao e status do PLAN-005.
- **Criterios de conclusao:** relatorio final criado, gates verdes e suites
  consolidadas explicitadas.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `docs/implementation/reports/PLAN-005-execution-report-2026-08-09.md`.

---

# 3. Gates

## P3.5 - Correcoes da Segunda Auditoria

### IMP-094 - Implementar ativacao inicial segura

- **Status:** Concluido em 2026-08-09.
- **Resultado:** token descartavel persistido somente por hash, expiravel e de uso unico;
  bootstrap do administrador devolve o token apenas na primeira resposta.
- **Evidencia:** `tests/integration/api/test_api_iam_management.py`.

### IMP-095 - Expor gestao de credenciais

- **Status:** Concluido em 2026-08-09.
- **Resultado:** alteracao propria e redefinicao administrativa protegidas por Principal/RBAC.
- **Endpoints:** `PATCH /iam/credencial` e
  `POST /iam/usuarios/{usuario_id}/credencial/redefinir`.
- **Evidencia:** `tests/integration/api/test_api_iam_management.py`.

### IMP-096 - Implementar gestao de Perfis e Permissoes

- **Status:** Concluido em 2026-08-09.
- **Resultado:** US-035..038 implementadas com idempotencia, auditoria, isolamento por
  Tenant e vinculo real em `usuario_perfil`.
- **Endpoints:** `POST /iam/perfis`, `GET /iam/perfis`,
  `GET /iam/perfis/{perfil_id}`, `PATCH /iam/perfis/{perfil_id}`,
  `POST /iam/perfis/{perfil_id}/inativar`,
  `PUT /iam/perfis/{perfil_id}/permissoes/{codigo}`,
  `DELETE /iam/perfis/{perfil_id}/permissoes/{codigo}`,
  `PUT /iam/usuarios/{usuario_id}/perfil/{perfil_id}`,
  `DELETE /iam/usuarios/{usuario_id}/perfil` e
  `GET /iam/usuarios/{usuario_id}/permissoes`.
- **Evidencia:** `tests/integration/api/test_api_iam_management.py` e
  `tests/integration/repositories/test_iam_repositories.py`.

### IMP-097 - Recertificar auditoria de acesso

- **Status:** Concluido em 2026-08-09.
- **Resultado:** recusas 401, 403 e 404 persistem eventos append-only sem segredos.
- **Evidencia:** `tests/integration/api/test_api_authorization.py`.

### IMP-098 - Recertificacao corrigida do EPIC-006

- **Status:** Concluido em 2026-08-09.
- **Criterio:** todos os gates globais e documentais aprovados apos IMP-094..097.
- **Evidencia:** 568 testes Python, gates Ruff/Black/Mypy verdes, 42/42 testes
  documentais e segunda rodada adversarial com correcoes de backfill, RBAC
  normalizado, isolamento de Tenant, ativacao atomica e contrato OpenAPI Bearer.

### IMP-099 - Bootstrap seguro do Administrador da Plataforma

- **Status:** Concluido em 2026-08-09.
- **Resultado:** comando operacional local, sem endpoint HTTP, protegido por gate
  temporario e segredo fora de `argv`; cria atomicamente Tenant de controle,
  Usuario ativo, Credencial PBKDF2 e Perfil `administrador_plataforma` somente
  com `tenant.*`.
- **Seguranca:** idempotencia singleton, replay com validacao do estado persistido,
  concorrencia PostgreSQL, bloqueio de autoelevacao pela gestao comum de Perfis e
  protecao aplicacional contra inativacao do Tenant de controle.
- **Comando:** `emprestimo-bootstrap-plataforma`.
- **Evidencia:** `tests/unit/application/test_bootstrap_plataforma.py`,
  `tests/unit/presentation/test_bootstrap_plataforma_cli.py`,
  `tests/integration/application/test_bootstrap_plataforma_integration.py` e
  `docs/operations/bootstrap-administrador-plataforma.md`.

### IMP-100 - Contratos OpenAPI de erros IAM/autorizacao

- **Status:** Concluido em 2026-08-09.
- **Resultado:** OpenAPI declara `ErroResponse` para 401 em `/auth/*`, 401/403
  nas rotas protegidas e 404 nas rotas com resolucao de recurso ou isolamento
  cross-tenant.
- **Componentes afetados:** `presentation/api/openapi.py`, routers REST e suite
  de contrato dos endpoints protegidos.
- **Evidencia:** `tests/integration/api/test_api_protected_endpoints.py`.

### IMP-101 - Recertificar suite completa de endpoints protegidos

- **Status:** Concluido em 2026-08-09.
- **Resultado:** travamento anterior explicado por ausencia do PostgreSQL local em
  `localhost:5432`; o servico `postgres` do `docker-compose.yml` foi iniciado e
  validado como pre-condicao da suite de integracao.
- **Evidencia:** `docker ps` com `emprestimo-postgres-1` healthy, `select 1`
  via SQLAlchemy e `tests/integration/api/test_api_protected_endpoints.py` com
  10 testes aprovados.

### IMP-102 - Recertificacao global do backend com Postgres saudavel

- **Status:** Concluido em 2026-08-09.
- **Resultado:** suite Python completa e gates estaticos/documentais aprovados
  com `emprestimo-postgres-1` healthy em `localhost:5432`.
- **Evidencia:** `pytest -q` com 596 testes aprovados; `ruff check .`,
  `black --check .`, `mypy src tests`, `docs:validate` e `docs:test` verdes.

### IMP-103 - Encerrar formalmente EPIC-006/IAM

- **Status:** Concluido em 2026-08-09.
- **Resultado:** EPIC-006, PLAN-005, backlog e relatorio final foram alinhados
  para registrar que todo o escopo IAM esta implementado e recertificado.
- **Evidencia:** `docs/product/platform/epics/EPIC-006-iam.md`,
  `docs/implementation/plans/PLAN-005-epic-006-iam-detalhado.md` e
  `docs/implementation/reports/PLAN-005-execution-report-2026-08-09.md`.

O EPIC-006 avanca somente com:

- `uv run pytest`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`.

---

# 4. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.8.0 | 2026-08-09 | IMP-103 fechou formalmente EPIC-006/IAM apos recertificacao global. |
| 1.7.0 | 2026-08-09 | IMP-102 concluiu recertificacao global do backend com Postgres healthy e gates verdes. |
| 1.6.0 | 2026-08-09 | IMP-101 concluiu recertificacao da suite completa de endpoints protegidos com Postgres local healthy. |
| 1.5.0 | 2026-08-09 | IMP-100 concluido com contratos OpenAPI de 401/403/404 e teste de regressao. |
| 1.4.0 | 2026-08-09 | IMP-099 concluido com bootstrap operacional singleton e credencial atomica. |
| 1.3.0 | 2026-08-09 | IMP-094..098 adicionados apos a segunda auditoria adversarial. |
| 1.2.0 | 2026-08-09 | IMP-093 concluido com recertificacao final do EPIC-006/IAM. |
| 1.1.0 | 2026-08-09 | IMP-092 concluido com RBAC por operacao na API e prova HTTP de 403/404 cross-tenant. |
| 1.0.0 | 2026-08-08 | Backlog tecnico do PLAN-005/EPIC-006 com IMP-082..IMP-092. |
