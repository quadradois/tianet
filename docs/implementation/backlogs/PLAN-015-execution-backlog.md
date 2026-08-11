# PLAN-015-EXEC - Backlog de Execucao do EPIC-008/Fundacao Operacional e Observabilidade

**ID:** PLAN-015-EXEC

**Versao:** 1.0.0

**Status:** Implementado

---

# 1. Contexto

Este backlog transforma o `PLAN-015` em uma sequencia executavel para o
EPIC-008/Fundacao Operacional e Observabilidade. A numeracao de implementacao
continua apos o `PLAN-014-EXEC`, cujo ultimo item foi `IMP-185`.

---

# 2. Ordem Executavel

## P0 - Suites e Contratos antes do Codigo

### IMP-186 - Criar suites de contrato operacional do EPIC-008

- **Objetivo:** cobrir Product/ADR/PLAN, health, correlation ID, logs e eventos
  antes da implementacao.
- **Componentes afetados:** `tests/`, `scripts/tests/`.
- **Dependencias:** `PLAN-015`, `EPIC-008 Product`.
- **Criterios de conclusao:** suites falham se contratos documentados forem
  removidos ou enfraquecidos.
- **Suite minima:** `npm run docs:test`.
- **Status:** Concluido.

### IMP-187 - Criar guardrail de seguranca para observabilidade

- **Objetivo:** impedir vazamento de tokens, senhas, DSN, documentos pessoais,
  stack trace e payload sensivel em health/logs/erros.
- **Componentes afetados:** `tests/unit/`, `tests/integration/api/`.
- **Dependencias:** `IMP-186`.
- **Criterios de conclusao:** testes negativos cobrem healthcheck, logs e erro
  tecnico.
- **Suite minima:** `uv run pytest tests/integration/api/test_observability_api.py`.
- **Status:** Concluido.

### IMP-188 - Criar guardrail anti-calculo em eventos e projections

- **Objetivo:** impedir que eventos, logs ou read models calculem juros, saldo,
  quitacao, amortizacao ou memoria fora do Motor.
- **Componentes afetados:** `tests/unit/architecture/`.
- **Dependencias:** `IMP-186`.
- **Criterios de conclusao:** AST/contrato falha diante de formulas financeiras
  fora do Motor.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_observability_guardrails.py`.
- **Status:** Concluido.

## P1 - Pipeline e Migrations

### IMP-189 - Criar pipeline de qualidade em CI

- **Objetivo:** declarar workflow que rode pytest, ruff, black, mypy e docs.
- **Componentes afetados:** `.github/workflows/`.
- **Dependencias:** `IMP-186`.
- **Criterios de conclusao:** workflow contem os comandos oficiais e falha em
  erro de gate.
- **Suite minima:** `npm run docs:test`.
- **Status:** Concluido.

### IMP-190 - Integrar validacao reproduzivel de migrations ao gate

- **Objetivo:** incluir rotina de migrations no CI e documentar execucao local.
- **Componentes afetados:** `.github/workflows/`, `docs/operations/`.
- **Dependencias:** `IMP-189`.
- **Criterios de conclusao:** `npm run quality:migrations` fica documentado e
  executado pelo pipeline.
- **Suite minima:** `npm run quality:migrations`.
- **Status:** Concluido.

## P2 - Healthcheck Real

### IMP-191 - Implementar health service com banco de dados

- **Objetivo:** verificar saude da aplicacao e conectividade com banco.
- **Componentes afetados:** `src/emprestimo/presentation/api/`, `src/emprestimo/infrastructure/`.
- **Dependencias:** `IMP-187`.
- **Criterios de conclusao:** health responde saudavel com banco disponivel e
  indisponivel/degradado quando banco falha.
- **Suite minima:** `uv run pytest tests/integration/api/test_healthcheck.py`.
- **Status:** Concluido.

### IMP-192 - Blindar contrato publico de healthcheck

- **Objetivo:** garantir resposta minima e sem dados sensiveis.
- **Componentes afetados:** `src/emprestimo/presentation/api/`, `tests/integration/api/`.
- **Dependencias:** `IMP-191`.
- **Criterios de conclusao:** endpoint publico nao exige token e nao vaza
  segredo, tenant, usuario, DSN ou stack trace.
- **Suite minima:** `uv run pytest tests/integration/api/test_healthcheck.py`.
- **Status:** Concluido.

## P3 - Correlation ID, Logs e Erros

### IMP-193 - Implementar middleware de correlation ID

- **Objetivo:** propagar `X-Correlation-ID` em toda requisicao/resposta.
- **Componentes afetados:** `src/emprestimo/presentation/api/`.
- **Dependencias:** `IMP-192`.
- **Criterios de conclusao:** respostas 2xx, 4xx e 5xx incluem correlation ID.
- **Suite minima:** `uv run pytest tests/integration/api/test_correlation_id.py`.
- **Status:** Concluido.

### IMP-194 - Implementar logs estruturados e mascaramento

- **Objetivo:** padronizar log tecnico com correlation ID e mascaramento.
- **Componentes afetados:** `src/emprestimo/`, `tests/unit/`.
- **Dependencias:** `IMP-193`.
- **Criterios de conclusao:** logs contem campos minimos e nao vazam dados
  sensiveis.
- **Suite minima:** `uv run pytest tests/unit/test_logging_observability.py`.
- **Status:** Concluido.

### IMP-195 - Padronizar tratamento tecnico de erro inesperado

- **Objetivo:** retornar 500 seguro e registrar erro com correlation ID.
- **Componentes afetados:** `src/emprestimo/presentation/api/`.
- **Dependencias:** `IMP-194`.
- **Criterios de conclusao:** excecao inesperada nao devolve stack trace e loga
  contexto tecnico.
- **Suite minima:** `uv run pytest tests/integration/api/test_error_handling.py`.
- **Status:** Concluido.

### IMP-196 - Criar runbook operacional minimo

- **Objetivo:** documentar diagnostico de falha de banco, pipeline, migration e
  erro 500.
- **Componentes afetados:** `docs/operations/`.
- **Dependencias:** `IMP-195`.
- **Criterios de conclusao:** runbook referencia comandos oficiais e correlation
  ID, sem pedir segredo em texto claro.
- **Suite minima:** `npm run docs:validate`.
- **Status:** Concluido.

## P4 - Eventos Internos e Projections

### IMP-197 - Implementar contrato de envelope de evento interno

- **Objetivo:** definir envelope e porta interna de publicacao de eventos.
- **Componentes afetados:** `src/emprestimo/domain/`, `src/emprestimo/application/ports.py`.
- **Dependencias:** `IMP-188`, `IMP-193`.
- **Criterios de conclusao:** evento possui ID, tipo, versao, horario, tenant,
  correlation ID e payload.
- **Suite minima:** `uv run pytest tests/unit/domain/test_domain_events.py`.
- **Status:** Concluido.

### IMP-198 - Definir diretrizes tecnicas de projections reconstruiveis

- **Objetivo:** preparar read models sem verdade financeira paralela.
- **Componentes afetados:** `docs/operations/`, `src/emprestimo/application/`.
- **Dependencias:** `IMP-197`.
- **Criterios de conclusao:** projection registra origem, versao e
  `data_referencia` quando aplicavel, e guardrail proibe calculo financeiro.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_observability_guardrails.py`.
- **Status:** Concluido.

## P5 - OpenAPI e Recertificacao

### IMP-199 - Atualizar OpenAPI para health e correlation ID

- **Objetivo:** documentar healthcheck, headers e erros tecnicos.
- **Componentes afetados:** `src/emprestimo/presentation/api/openapi.py`,
  `tests/integration/api/`.
- **Dependencias:** `IMP-195`.
- **Criterios de conclusao:** OpenAPI descreve `X-Correlation-ID`, `/health` e
  respostas 500 seguras.
- **Suite minima:** `uv run pytest tests/integration/api/test_openapi_contract.py`.
- **Status:** Concluido.

### IMP-200 - Recertificar EPIC-008 com suite completa

- **Objetivo:** validar que EPIC-008 esta consistente em Product, ADR, PLAN,
  codigo e gates.
- **Componentes afetados:** `docs/implementation/reports/`.
- **Dependencias:** `IMP-199`, `IMP-198`.
- **Criterios de conclusao:** pytest, ruff, black, mypy, docs, migrations e
  revisao adversarial sem achados bloqueantes.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido.

---

# 3. Gates de Execucao

O EPIC-008 avanca com:

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:test`;
- `npm run docs:validate`;
- `npm run quality:migrations`;
- revisao adversarial final sem achados bloqueantes.

---

# 4. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Backlog inicial de execucao do PLAN-015/EPIC-008 com blocos P0 a P5. |
| 1.1.0 | 2026-08-11 | IMP-186 a IMP-200 marcados como concluidos apos macro-loop de implementacao. |
