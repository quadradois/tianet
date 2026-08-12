# PLAN-024 - Hardening Tecnico de Warnings do Backend MVP

**ID:** PLAN-024

**Data:** 2026-08-12

**Escopo:** hardening tecnico pos-certificacao do Backend MVP

**Plano relacionado:** PLAN-020

**Status:** Concluido

---

# 1. Objetivo

Registrar o tratamento dos avisos nao bloqueantes encontrados na recertificacao
pos-merge do Backend MVP, sem criar novo EPIC funcional, sem iniciar frontend e
sem alterar regra financeira, IAM/RBAC ou contratos de negocio.

---

# 2. Decisoes de Hardening

| Aviso | Decisao | Justificativa |
|---|---|---|
| Alembic `path_separator` ausente | Corrigir em `alembic.ini` | Configuracao recomendada pelo proprio warning; nao altera migrations. |
| `fastapi.testclient` | Trocar imports de teste para `starlette.testclient` | Evita depender do wrapper depreciado do FastAPI mantendo o mesmo cliente ASGI. |
| Starlette `httpx` vs `httpx2` | Filtrar warning externo conhecido no pytest | A instalacao de `httpx2` muda dependencia; fica fora deste pacote ate decisao explicita de stack. |
| `docs:validate` com 29 avisos historicos | Manter como caveat governado | Os avisos apontam referencias antigas, aliases legados ou planejamento historico ja aceitos pelo Registry e pelo PLAN-022. |
| CRLF em comandos Git/npm | Validar com `git diff --check` | Warnings de conversao de linha nao indicam erro de conteudo quando o diff-check permanece verde. |

---

# 3. Caveats Governados

Os 29 avisos do `docs:validate` permanecem aceitos como divida historica
documental. Eles nao bloqueiam o Backend MVP porque:

- o validador reporta `0 erro(s)`;
- namespaces legados `DECISION` e `FEATURES` estao registrados como `LEGACY`;
- referencias antigas como `BR-*`, `ENT-*` e `VO-*` pertencem a documentos de
  discovery, auditoria ou planejamento anterior;
- o PLAN-022 ja classificou documentos historicos como aceitos para rastreio,
  sem reescrita retroativa.

---

# 4. Criterios de Validacao

Este hardening deve ser aceito somente se os gates abaixo permanecerem verdes:

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- `npm run quality:migrations`;
- `git diff --check`.

---

# 5. Evidencias Observadas

| Gate | Resultado |
|---|---|
| `uv run pytest -q` | 935 testes passaram, sem warnings tecnicos no resumo |
| `uv run ruff check .` | All checks passed |
| `uv run black --check .` | 247 files would be left unchanged |
| `uv run mypy src tests` | Success em 229 source files |
| `npm run docs:validate` | 306 verificacoes OK, 29 avisos historicos, 0 erros |
| `npm run docs:test` | Todas as suites documentais passaram |
| `npm run quality:migrations` | upgrade head -> downgrade base -> upgrade head concluido |
| `git diff --check` | Sem erro de whitespace; avisos CRLF/LF permanecem ate normalizacao pelo Git |

Smoke adicional executado apos `quality:migrations`:

- `uv run pytest tests/integration/api/test_api.py::test_health -q` passou,
  confirmando que a fixture de banco recomeça limpa mesmo apos o ciclo
  destrutivo de migrations.

---

# 6. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-12 | Registro do hardening tecnico de warnings pos-certificacao do Backend MVP. |
