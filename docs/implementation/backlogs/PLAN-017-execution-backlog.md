# PLAN-017-EXEC - Backlog de Execucao do EPIC-009/Configuracoes Financeiras e Calendario Operacional

**ID:** PLAN-017-EXEC

**Versao:** 1.0.0

**Status:** Planejado

---

# 1. Contexto

Este backlog transforma o `PLAN-017` em uma sequencia executavel para o
EPIC-009/Configuracoes Financeiras e Calendario Operacional. A numeracao de
implementacao continua apos o `PLAN-015-EXEC`, cujo ultimo item foi `IMP-200`.

O `PLAN-016` foi emitido como relatorio de execucao do EPIC-008; por isso o
proximo plano tecnico sequencial e `PLAN-017`.

---

# 2. Ordem Executavel

## P0 - Suites, Contratos e Guardrails antes do Codigo

### IMP-201 - Criar suites documentais e contratuais do EPIC-009

- **Objetivo:** cobrir Product/EPIC/Features/User Stories/PLAN/backlog e
  contratos candidatos antes da implementacao.
- **Componentes afetados:** `scripts/tests/`, `docs/implementation/`.
- **Dependencias:** `PLAN-017`, `EPIC-009 Product`.
- **Criterios de conclusao:** suites falham se a fronteira Configuracoes
  parametriza/Motor calcula, snapshots ou IDs forem removidos ou enfraquecidos.
- **Suite minima:** `npm run docs:test`.
- **Status:** Concluido em 2026-08-11.

### IMP-202 - Criar guardrail anti-calculo em Configuracoes Financeiras

- **Objetivo:** impedir juros, mora, multa, saldo, amortizacao, quitacao e
  memoria de calculo dentro de Configuracoes.
- **Componentes afetados:** `tests/unit/architecture/`, `tests/unit/domain/`.
- **Dependencias:** `IMP-201`.
- **Criterios de conclusao:** teste negativo falha diante de formulas
  financeiras definitivas fora do Motor.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_configuracoes_financeiras_guardrails.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-203 - Criar guardrail contra regra financeira livre em APIs consumidoras

- **Objetivo:** garantir que Comercial, Contratos e Motor nao aceitem payload
  financeiro arbitrario como fonte oficial.
- **Componentes afetados:** `tests/integration/api/`, `tests/unit/architecture/`.
- **Dependencias:** `IMP-201`.
- **Criterios de conclusao:** testes falham se rotas consumidoras aceitarem
  regra financeira livre em vez de referencia governada ou snapshot.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_configuracoes_financeiras_guardrails.py`.
- **Status:** Concluido em 2026-08-11.

## P1 - Dominio Configuracoes Financeiras

### IMP-204 - Implementar ModalidadeFinanceira e Value Objects

- **Objetivo:** modelar codigo de modalidade, taxa configurada, parametro
  financeiro, politica de arredondamento e janela de vigencia.
- **Componentes afetados:** `src/emprestimo/domain/credit/`,
  `tests/unit/domain/`.
- **Dependencias:** `IMP-202`, `IMP-203`.
- **Criterios de conclusao:** dominio valida formato, faixa, escala,
  moeda/unidade e vigencia sem calcular resultado financeiro.
- **Suite minima:** `uv run pytest tests/unit/domain/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-205 - Implementar CalendarioFinanceiro sem calculo definitivo

- **Objetivo:** modelar calendario operacional para periodos e datas de
  referencia, sem calcular juros ou inadimplencia.
- **Componentes afetados:** `src/emprestimo/domain/credit/`,
  `tests/unit/domain/`.
- **Dependencias:** `IMP-204`.
- **Criterios de conclusao:** calendario resolve convencoes permitidas e rejeita
  ambiguidade ou configuracao invalida.
- **Suite minima:** `uv run pytest tests/unit/domain/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-206 - Implementar ConfiguracaoFinanceira e estados

- **Objetivo:** criar aggregate de configuracao versionada com estados
  `rascunho`, `ativa`, `programada`, `substituida` e `inativa`.
- **Componentes afetados:** `src/emprestimo/domain/credit/`,
  `tests/unit/domain/`.
- **Dependencias:** `IMP-204`, `IMP-205`.
- **Criterios de conclusao:** transicoes de criacao, aprovacao, programacao,
  ativacao, substituicao e inativacao seguem Product/US.
- **Suite minima:** `uv run pytest tests/unit/domain/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-207 - Implementar contratos ConfiguracaoFinanceiraVigenteV1 e SnapshotConfiguracaoContratualV1

- **Objetivo:** formalizar contratos de consulta vigente e snapshot contratual
  imutavel.
- **Componentes afetados:** `src/emprestimo/domain/credit/`,
  `tests/unit/domain/`.
- **Dependencias:** `IMP-206`.
- **Criterios de conclusao:** snapshot preserva origem, versao,
  `capturado_em`, parametros normalizados e hash, sem campo volatil
  `consultada_em`.
- **Suite minima:** `uv run pytest tests/unit/domain/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-208 - Implementar eventos de ConfiguracaoFinanceira

- **Objetivo:** registrar eventos de criacao, aprovacao, programacao,
  ativacao, substituicao, inativacao e captura de snapshot.
- **Componentes afetados:** `src/emprestimo/domain/credit/`,
  `tests/unit/domain/`.
- **Dependencias:** `IMP-207`.
- **Criterios de conclusao:** eventos possuem tenant, carteira quando aplicavel,
  usuario, motivo, timestamp, versao anterior/nova e correlation ID quando
  disponivel.
- **Suite minima:** `uv run pytest tests/unit/domain/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

## P2 - Persistencia e Migrations

### IMP-209 - Criar migration Configuracoes Financeiras

- **Objetivo:** adicionar tabelas de configuracoes, versoes, modalidades,
  calendarios, eventos e snapshots quando aplicavel.
- **Componentes afetados:** `migrations/versions/`, `tests/integration/migrations/`.
- **Dependencias:** `IMP-208`.
- **Criterios de conclusao:** upgrade/downgrade/upgrade reproduzivel, indices e
  constraints de escopo/vigencia sem alterar tabelas de Comercial, Contratos ou
  Motor.
- **Suite minima:** `npm run quality:migrations`.
- **Status:** Concluido em 2026-08-11.

### IMP-210 - Implementar ORM e repositories de Configuracoes Financeiras

- **Objetivo:** persistir configuracoes, modalidades, calendarios, versoes,
  eventos e snapshots com isolamento por tenant/carteira.
- **Componentes afetados:** `src/emprestimo/infrastructure/db/`,
  `src/emprestimo/infrastructure/repositories/`.
- **Dependencias:** `IMP-209`.
- **Criterios de conclusao:** round-trip e consultas por tenant, carteira,
  modalidade, estado e `data_referencia` passam em testes.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_configuracoes_financeiras_repositories.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-211 - Integrar repositories Configuracoes Financeiras no UnitOfWork

- **Objetivo:** expor acesso transacional para services de aplicacao sem commit
  manual fora do UoW.
- **Componentes afetados:** `src/emprestimo/infrastructure/unit_of_work.py`,
  `src/emprestimo/application/ports.py`.
- **Dependencias:** `IMP-210`.
- **Criterios de conclusao:** services conseguem usar repositories dentro da
  mesma transacao e respeitam rollback.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_configuracoes_financeiras_repositories.py`.
- **Status:** Concluido em 2026-08-11.

## P3 - Application

### IMP-212 - Implementar ModalidadeFinanceiraService

- **Objetivo:** criar, listar e validar modalidades permitidas por tenant e
  carteira.
- **Componentes afetados:** `src/emprestimo/application/configuracoes_financeiras.py`,
  `tests/unit/application/`.
- **Dependencias:** `IMP-211`.
- **Criterios de conclusao:** validacoes de escopo, duplicidade, 404 logico e
  auditoria passam em testes.
- **Suite minima:** `uv run pytest tests/unit/application/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-213 - Implementar ConfiguracaoFinanceiraService

- **Objetivo:** criar rascunho, validar parametros permitidos, aprovar,
  programar, ativar, substituir e inativar configuracoes.
- **Componentes afetados:** `src/emprestimo/application/configuracoes_financeiras.py`,
  `tests/unit/application/`.
- **Dependencias:** `IMP-212`.
- **Criterios de conclusao:** estados, vigencias, idempotencia, auditoria e 409
  de conflito ficam cobertos.
- **Suite minima:** `uv run pytest tests/unit/application/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-214 - Implementar CalendarioFinanceiroService

- **Objetivo:** administrar calendarios e resolver periodo por
  `data_referencia` sem calcular resultado financeiro.
- **Componentes afetados:** `src/emprestimo/application/configuracoes_financeiras.py`,
  `tests/unit/application/`.
- **Dependencias:** `IMP-213`.
- **Criterios de conclusao:** ausencia retorna 404 logico, ambiguidade retorna
  409 e payload malformado retorna erro mapeavel para 400.
- **Suite minima:** `uv run pytest tests/unit/application/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-215 - Implementar ConsultaConfiguracaoVigenteService

- **Objetivo:** consultar configuracao vigente por tenant, carteira, modalidade
  e data de referencia.
- **Componentes afetados:** `src/emprestimo/application/configuracoes_financeiras.py`,
  `tests/unit/application/`.
- **Dependencias:** `IMP-214`.
- **Criterios de conclusao:** retorna exatamente uma configuracao consumivel ou
  erro mapeavel para 404/409.
- **Suite minima:** `uv run pytest tests/unit/application/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-216 - Implementar CapturaSnapshotConfiguracaoService

- **Objetivo:** produzir snapshot imutavel para Comercial/Contratos sem enviar
  chamada direta ao Motor.
- **Componentes afetados:** `src/emprestimo/application/configuracoes_financeiras.py`,
  `tests/unit/application/`.
- **Dependencias:** `IMP-215`.
- **Criterios de conclusao:** snapshot possui origem, versao,
  `capturado_em`, usuario, motivo, hash e payload normalizado congelado.
- **Suite minima:** `uv run pytest tests/unit/application/test_configuracoes_financeiras.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-217 - Integrar contrato logico com Contratos sem quebrar Motor

- **Objetivo:** preparar `ContratoLiberadoLogico` para carregar referencia e
  snapshot oficial consumidos pelo Motor.
- **Componentes afetados:** `src/emprestimo/domain/credit/`,
  `src/emprestimo/application/`.
- **Dependencias:** `IMP-216`.
- **Criterios de conclusao:** Motor recebe parametros congelados via contrato
  liberado logico e nao consulta Configuracoes diretamente.
- **Suite minima:** `uv run pytest tests/unit/application/test_configuracoes_financeiras_integracao.py`.
- **Status:** Concluido em 2026-08-11.

## P4 - IAM, API e OpenAPI

### IMP-218 - Registrar permissoes de Configuracoes Financeiras no catalogo IAM

- **Objetivo:** criar permissoes para administrar, aprovar, ativar, consultar e
  capturar snapshots.
- **Componentes afetados:** `src/emprestimo/application/iam_catalogo.py`,
  `migrations/versions/`.
- **Dependencias:** `IMP-212..IMP-217`.
- **Criterios de conclusao:** principal sem permissao recebe 403 e principal
  autorizado executa.
- **Suite minima:** `uv run pytest tests/unit/application/test_autorizacao.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-219 - Criar schemas e dependencies da API Configuracoes Financeiras

- **Objetivo:** definir DTOs de modalidades, calendarios, configuracoes,
  consultas vigentes e snapshots.
- **Componentes afetados:** `src/emprestimo/presentation/api/`,
  `tests/integration/api/`.
- **Dependencias:** `IMP-218`.
- **Criterios de conclusao:** request/response validam payload, filtros,
  tenancy, carteira, datas e idempotencia.
- **Suite minima:** `uv run pytest tests/integration/api/test_configuracoes_financeiras_api.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-220 - Expor endpoints de modalidades, calendarios e configuracoes

- **Objetivo:** publicar rotas administrativas protegidas para criar/listar
  modalidades, calendarios e configuracoes.
- **Componentes afetados:** `src/emprestimo/presentation/api/`,
  `tests/integration/api/`.
- **Dependencias:** `IMP-219`.
- **Criterios de conclusao:** rotas retornam 200/201/400/401/403/404/409
  conforme Product/US.
- **Suite minima:** `uv run pytest tests/integration/api/test_configuracoes_financeiras_api.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-221 - Expor endpoints de vigencia e snapshots

- **Objetivo:** publicar rotas de aprovar, programar, ativar, inativar,
  consultar vigente e capturar snapshot.
- **Componentes afetados:** `src/emprestimo/presentation/api/`,
  `tests/integration/api/`.
- **Dependencias:** `IMP-220`.
- **Criterios de conclusao:** transicoes invalidas retornam 409, ausencia
  retorna 404, payload malformado retorna 400 e RBAC responde 401/403.
- **Suite minima:** `uv run pytest tests/integration/api/test_configuracoes_financeiras_api.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-222 - Atualizar OpenAPI de Configuracoes Financeiras

- **Objetivo:** documentar rotas, schemas, security, erros e
  `X-Correlation-ID`.
- **Componentes afetados:** `src/emprestimo/presentation/api/openapi.py`,
  `tests/integration/api/`.
- **Dependencias:** `IMP-220`, `IMP-221`.
- **Criterios de conclusao:** OpenAPI publica 400/401/403/404/409 e nao expoe
  regra financeira livre como fonte oficial.
- **Suite minima:** `uv run pytest tests/integration/api/test_openapi_contract.py`.
- **Status:** Concluido em 2026-08-11.

## P5 - Recertificacao

### IMP-223 - Recertificar guardrails Configuracoes/Motor/Consumidores

- **Objetivo:** validar fronteiras entre Configuracoes, Comercial, Contratos e
  Motor apos API e contratos.
- **Componentes afetados:** `tests/unit/architecture/`,
  `tests/integration/api/`.
- **Dependencias:** `IMP-222`.
- **Criterios de conclusao:** nao ha calculo financeiro fora do Motor, nem
  chamada direta Configuracoes -> Motor, nem regra livre em APIs consumidoras.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_configuracoes_financeiras_guardrails.py`.
- **Status:** Concluido em 2026-08-11.

### IMP-224 - Recertificar EPIC-009 com suite completa

- **Objetivo:** validar que EPIC-009 esta consistente em Product, PLAN, codigo,
  API, OpenAPI, IAM, migrations e guardrails.
- **Componentes afetados:** `docs/implementation/reports/`,
  `docs/implementation/backlogs/PLAN-017-execution-backlog.md`.
- **Dependencias:** `IMP-223`.
- **Criterios de conclusao:** pytest, ruff, black, mypy, docs, migrations e
  revisao adversarial final sem achados bloqueantes.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido em 2026-08-11.

---

# 3. Gates de Execucao

O EPIC-009 avanca com:

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- `npm run quality:migrations`;
- revisao adversarial final sem achados bloqueantes.

---

# 4. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.8.0 | 2026-08-11 | IMP-223..IMP-224 concluidos com recertificacao de guardrails, suite completa, lint, formatacao, tipagem, docs e migrations em banco descartavel. |
| 1.7.0 | 2026-08-11 | IMP-218..IMP-222 concluidos com permissoes IAM, schemas, dependencies, rotas API e OpenAPI automatico de Configuracoes Financeiras. |
| 1.6.0 | 2026-08-11 | IMP-212..IMP-217 concluidos com services de aplicacao, consulta vigente, captura de snapshot e integracao logica com Contratos. |
| 1.5.0 | 2026-08-11 | IMP-209..IMP-211 concluidos com migration, ORM, repositories e UnitOfWork de Configuracoes Financeiras. |
| 1.4.0 | 2026-08-11 | IMP-204..IMP-208 concluidos com dominio de Configuracoes Financeiras, calendario, estados, contratos vigentes, snapshots e eventos. |
| 1.3.0 | 2026-08-11 | IMP-203 concluido com guardrail compartilhado para rejeitar regra financeira livre em APIs consumidoras. |
| 1.2.0 | 2026-08-11 | IMP-202 concluido com guardrail arquitetural anti-calculo para Configuracoes Financeiras. |
| 1.1.0 | 2026-08-11 | IMP-201 concluido com suite documental e contratual do EPIC-009 integrada ao `npm run docs:test`. |
| 1.0.0 | 2026-08-11 | Backlog inicial de execucao do PLAN-017/EPIC-009 com IMP-201..IMP-224 e suites antes de codigo. |
