# PLAN-014-EXEC - Backlog de Execução do EPIC-007/Operacao Diaria

**ID:** PLAN-014-EXEC

**Versao:** 1.0.0

**Status:** Implementado em 2026-08-11

---

# 1. Contexto

Este backlog transforma o `PLAN-014` em uma sequência executável para o
EPIC-007/Operacao Diaria. A numeração de implementação continua após o
`PLAN-013-EXEC`, cujo último item foi `IMP-170`.

---

# 2. Ordem Executavel

## P1 - Suites e Guardrails

### IMP-171 - Criar suites de dominio Operacao Diaria antes do código

- **Objetivo:** cobrir casos de Cobranca, Agenda, Comunicacao manual e Relatorios
  antes da implementação.
- **Componentes afetados:** `tests/unit/domain/test_operacao_diaria.py`,
  `tests/unit/domain/test_operacao_diaria_guardrails.py`.
- **Dependencias:** `PLAN-014`, `EPIC-007 Product`.
- **Criterios de conclusao:** suites cobrem contratos de promessa, agenda,
  comunicacao e agregacoes permitidas.
- **Suite minima:** `uv run pytest tests/unit/domain/test_operacao_diaria.py`.
- **Status:** Concluído.

### IMP-172 - Criar guardrail anti-cálculo financeiro fora do Motor

- **Objetivo:** garantir falha de implementação caso a operação tente calcular juros,
  saldo, multa ou amortizacao fora do Motor.
- **Componentes afetados:** `tests/unit/domain/test_operacao_diaria_guardrails.py`.
- **Dependencias:** `IMP-171`.
- **Criterios de conclusao:** AST/semântica de domínio nega `Decimal`/`float` de
  cálculo financeiro não oficiais.
- **Suite minima:** `uv run pytest tests/unit/domain/test_operacao_diaria_guardrails.py`.
- **Status:** Concluído.

### IMP-173 - Formalizar estado de promessa e transições (DA-718)

- **Objetivo:** validar maquina de estados da promessa e gatilhos de
  invalidacao/reavaliacao.
- **Componentes afetados:** `src/emprestimo/domain/credit/promessa.py`,
  `tests/unit/domain/test_promessa_pagamento.py`.
- **Dependencias:** `IMP-171`, `IMP-172`.
- **Criterios de conclusao:** estado e transições seguem tabelas oficiais e são
  reprodutíveis por teste.
- **Suite minima:** `uv run pytest tests/unit/domain/test_promessa_pagamento.py`.
- **Status:** Concluído.

## P2 - Persistencia e Migrations

### IMP-174 - Criar migration operacional do EPIC-007

- **Objetivo:** adicionar tabela de suporte para cobranca, promessa,
  apropriacao, agenda, comunicacao e cache operacional.
- **Componentes afetados:** `src/emprestimo/infrastructure/db/migrations`.
- **Dependencias:** `IMP-173`.
- **Criterios de conclusao:** upgrade/downgrade/upgrade estável com FKs,
  indices e unicidades por escopo.
- **Suite minima:** `uv run pytest tests/integration/migrations/test_operacao_diaria_schema.py`.
- **Status:** Concluído.

### IMP-175 - Implementar ORM e repositories do EPIC-007

- **Objetivo:** persistir/consultar entidades operacionais e histórico imutável.
- **Componentes afetados:** `src/emprestimo/infrastructure/db/orm.py`,
  `src/emprestimo/infrastructure/repositories/operacao_diaria.py`.
- **Dependencias:** `IMP-174`.
- **Criterios de conclusao:** round-trip por tenant/carteira/devedor e filtros de
  estado e janela temporal.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_operacao_diaria_repositories.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-176 - Integrar repositorios Operacao Diaria no UnitOfWork

- **Objetivo:** expor acesso transacional unificado para domain/application.
- **Componentes afetados:** `src/emprestimo/infrastructure/unit_of_work.py`,
  `src/emprestimo/application/ports.py`.
- **Dependencias:** `IMP-175`.
- **Criterios de conclusao:** serviços transitam sem commit manual fora do UoW.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_operacao_diaria_repositories.py`.
- **Status:** Concluido em 2026-08-11.

## P3 - Application

### IMP-177 - Implementar serviços da Cobranca Manual

- **Objetivo:** implementar `ConsultarFilaCobranca`, `RegistrarAcaoCobranca`,
  `RegistrarPromessa` e `ApropriarPagamentoPromessa`.
- **Componentes afetados:** `src/emprestimo/application/operacao_diaria.py`.
- **Dependencias:** `IMP-176`.
- **Criterios de conclusao:** contratos de idempotência e rejeição de payload/cadeia
  inválidos passam em testes.
- **Suite minima:** `uv run pytest tests/unit/application/test_operacao_diaria_cobranca.py tests/integration/application/test_operacao_diaria_application.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-178 - Implementar serviços de Agenda Operacional

- **Objetivo:** implementar criação, consulta, reagendamento, conclusão e
  cancelamento de compromissos/lembretes com trilha de transição.
- **Componentes afetados:** `src/emprestimo/application/operacao_diaria.py`.
- **Dependencias:** `IMP-177`.
- **Criterios de conclusao:** estado em aberto/fechado é irreversível conforme regras
  e histórico preservado.
- **Suite minima:** `uv run pytest tests/unit/application/test_operacao_diaria_agenda.py tests/integration/application/test_operacao_diaria_application.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-179 - Implementar serviços de Comunicacao Manual

- **Objetivo:** registrar e consultar histórico de comunicacao manual com validação
  de cadeia canônica.
- **Componentes afetados:** `src/emprestimo/application/operacao_diaria.py`.
- **Dependencias:** `IMP-178`.
- **Criterios de conclusao:** escrita idempotente, filtros autorizados e 404 lógico
  quando cadeias divergirem.
- **Suite minima:** `uv run pytest tests/unit/application/test_operacao_diaria_comunicacao.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-180 - Implementar serviços de Relatorios Operacionais

- **Objetivo:** oferecer consultas de resumo de carteira, vencimentos,
  inadimplência, pagamentos e fluxo.
- **Componentes afetados:** `src/emprestimo/application/operacao_diaria.py`,
  `src/emprestimo/application/relatorios.py`.
- **Dependencias:** `IMP-179`.
- **Criterios de conclusao:** relatórios consistentes com fatos oficiais e sem
  recalculo financeiro.
- **Suite minima:** `uv run pytest tests/unit/application/test_operacao_diaria_relatorios.py`.
- **Status:** Concluido em 2026-08-11.

## P4 - IAM, API e OpenAPI

### IMP-181 - Registrar permissões de operação diária no catálogo IAM

- **Objetivo:** criar e mapear permissões de cobranca, agenda, comunicacao e
  relatorios em `permission_catalog`.
- **Componentes afetados:** `src/emprestimo/application/iam_catalogo.py`.
- **Dependencias:** `IMP-177..IMP-180`.
- **Criterios de conclusao:** principal sem permissão recebe 403 e principal
  autorizado executa.
- **Suite minima:** `uv run pytest tests/unit/application/test_autorizacao.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-182 - Criar schemas e dependencies de API

- **Objetivo:** incluir DTOs, filtros e dependências por tenancy/carteira com
  isolamento canônico.
- **Componentes afetados:** `src/emprestimo/presentation/api/operacao_diaria_schemas.py`,
  `src/emprestimo/presentation/api/dependencies.py`.
- **Dependencias:** `IMP-181`.
- **Criterios de conclusao:** validação de request/response e paginação
  consistente com User Stories.
- **Suite minima:** `uv run pytest tests/integration/api/test_operacao_diaria_api.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-183 - Expor rotas de Cobranca, Agenda e Comunicacao

- **Objetivo:** expor endpoints de acompanhamento operacional e escrita
  manual (somente leitura/calculado no Motor).
- **Componentes afetados:** `src/emprestimo/presentation/api/operacao_diaria_routes.py`.
- **Dependencias:** `IMP-182`.
- **Criterios de conclusao:** rotas retornam 200/400/401/403/404/409 conforme cada
  User Story.
- **Suite minima:** `uv run pytest tests/integration/api/test_operacao_diaria_api.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-184 - Expor rotas de Relatorios e OpenAPI de Operacao Diaria

- **Objetivo:** publicar contratos de leitura operacional e declarar erros de forma
  explícita.
- **Componentes afetados:** `src/emprestimo/presentation/api/operacao_diaria_routes.py`,
  `src/emprestimo/presentation/api/openapi.py`.
- **Dependencias:** `IMP-183`.
- **Criterios de conclusao:** OpenAPI documenta filtros, paginação, escopos e
  códigos `400/401/403/404/409`.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_protected_endpoints.py tests/integration/api/test_operacao_diaria_api.py`.
- **Status:** Concluido em 2026-08-11.

## P5 - Recertificação

### IMP-185 - Recertificar EPIC-007 com suite completa

- **Objetivo:** validar que o EPIC-007 está implementado conforme Discovery,
  produto, regras e governança.
- **Componentes afetados:** `docs/implementation/reports/PLAN-014-execution-report-*.md`,
  `docs/implementation/backlogs/PLAN-014-execution-backlog.md`.
- **Dependencias:** `IMP-184`.
- **Criterios de conclusao:** suíte completa (pytest, qualidade e validação docs)
  verde e revisão adversarial sem achados.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido em 2026-08-11.

---

# 3. Gates de Execução

O EPIC-007 avanca com:

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- recertificação adversarial em andamento sem achados críticos.

---

# 4. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-10 | Backlog inicial de execução do PLAN-014/EPIC-007 com blocos por prioridade. |
