# PLAN-020-EXEC - Backlog de Fechamento e Certificacao do Backend MVP

**ID:** PLAN-020-EXEC

**Versao:** 1.7.0

**Status:** Concluido

---

# 1. Contexto

Este backlog transforma o `PLAN-020` em ordem executavel. A numeracao continua
apos `IMP-253`, ultimo item concluido no `PLAN-018-EXEC`. Os itens `IMP-254..IMP-273`
devem certificar o backend MVP sem criar novo EPIC funcional e sem iniciar
frontend.

---

# 2. Ordem Executavel

## P0 - Inventario e Contratos antes das Correcoes

### IMP-254 - Criar contrato documental do PLAN-020

- **Objetivo:** proteger a consistencia entre PLAN-020, backlog, registry,
  EPICs 001 a 010 e relatorios de execucao.
- **Componentes afetados:** `scripts/tests/`, `docs/implementation/`.
- **Dependencias:** PLAN-020.
- **Criterios de conclusao:** teste detecta ausencia de PLAN-020, faixa
  `IMP-254..IMP-273` incompleta, dependencia futura, novo EPIC funcional
  indevido, remocao dos gates finais e ausencia da propria suite no
  `npm run docs:test`.
- **Suite minima:** `node scripts/tests/test-plan-020-contracts.js`.
- **Status:** Concluido.

### IMP-255 - Inventariar Product, API, RBAC e suites existentes

- **Objetivo:** gerar matriz automatizada ou verificavel de Product -> EPIC ->
  Feature -> User Story -> endpoint -> permissao -> suite.
- **Componentes afetados:** `tests/`, `scripts/tests/`, `docs/implementation/reports/`.
- **Dependencias:** IMP-254.
- **Criterios de conclusao:** rotas reais em FastAPI, OpenAPI e docs ficam
  comparaveis; lacunas sao classificadas por contexto e severidade.
- **Suite minima:** `uv run pytest tests/integration/api`.
- **Status:** Concluido.

### IMP-256 - Criar baseline de cobertura e gates do backend MVP

- **Objetivo:** registrar quantidade de testes, gates oficiais, migrations,
  scripts documentais e smoke commands que serao exigidos no fechamento.
- **Componentes afetados:** `docs/implementation/reports/`, `scripts/`.
- **Dependencias:** IMP-254.
- **Criterios de conclusao:** baseline distingue falha real, divida
  preexistente, problema ambiental e divergencia documental.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido.

## P1 - Fluxos E2E Transversais

### IMP-257 - Criar E2E Tenant, IAM e Cadastro

- **Objetivo:** provar provisionamento, ativacao de credencial, login,
  principal, RBAC, cadastro e consulta de Devedor.
- **Componentes afetados:** `tests/e2e/` ou `tests/integration/api/`.
- **Dependencias:** IMP-255 e IMP-256.
- **Criterios de conclusao:** fluxo cobre idempotencia, auditoria, 401/403/404,
  cross-tenant e correlation ID.
- **Suite minima:** `uv run pytest tests/integration/api/test_backend_mvp_e2e.py`.
- **Status:** Concluido.

### IMP-258 - Criar E2E Cadastro, Comercial e Contratos

- **Objetivo:** provar Devedor ativo, SimulacaoComercial, PropostaComercial,
  decisao, contrato logico, formalizacao, assinatura e liberacao.
- **Componentes afetados:** `tests/e2e/` ou `tests/integration/api/`.
- **Dependencias:** IMP-257.
- **Criterios de conclusao:** Comercial nao calcula fato financeiro definitivo
  e Contratos nao aceita proposta fora do estado aprovado.
- **Suite minima:** `uv run pytest tests/integration/api/test_backend_mvp_e2e.py`.
- **Status:** Concluido.

### IMP-259 - Criar E2E Contratos e Motor Financeiro

- **Objetivo:** provar Emprestimo a partir de ContratoLiberadoLogico, parcelas,
  pagamento, saldo, quitacao, renegociacao e memoria de calculo.
- **Componentes afetados:** `tests/e2e/` ou `tests/integration/api/`.
- **Dependencias:** IMP-258.
- **Criterios de conclusao:** Motor e a unica autoridade de calculo; replay
  idempotente nao duplica parcelas, pagamentos ou memorias.
- **Suite minima:** `uv run pytest tests/integration/api/test_backend_mvp_e2e.py`.
- **Status:** Concluido.

### IMP-260 - Criar E2E Motor e Operacao Diaria

- **Objetivo:** provar cobranca manual, promessa, agenda, lembrete, comunicacao
  manual e relatorios a partir de fatos oficiais do Motor.
- **Componentes afetados:** `tests/e2e/` ou `tests/integration/api/`.
- **Dependencias:** IMP-259.
- **Criterios de conclusao:** relatorios nao truncam dados, periodo invalido
  retorna 400 e Operacao Diaria nao recalcula saldo, juros ou memoria.
- **Suite minima:** `uv run pytest tests/integration/api/test_backend_mvp_e2e.py`.
- **Status:** Concluido.

### IMP-261 - Criar E2E Agenda, Scheduler e Notification

- **Objetivo:** provar job duravel criado com Lembrete, claim por lease, envio
  por fake deterministico, Comunicacao pos-aceite e conclusao atomica.
- **Componentes afetados:** `tests/e2e/`, `tests/unit/worker/`.
- **Dependencias:** IMP-260.
- **Criterios de conclusao:** resultado desconhecido bloqueia retry automatico,
  token expirado nao conclui e rota legada nao dispara provedor.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_automacao_atomicity.py tests/unit/worker`.
- **Status:** Concluido.

## P2 - Seguranca, Isolamento e Auditoria

### IMP-262 - Recertificar RBAC global por endpoint

- **Objetivo:** comparar catalogo IAM, dependencies FastAPI, rotas reais e
  OpenAPI para todos os endpoints protegidos.
- **Componentes afetados:** `tests/integration/api/`, `src/emprestimo/application/iam_catalogo.py`.
- **Dependencias:** IMP-255 e IMP-261.
- **Criterios de conclusao:** cada endpoint protegido exige permissao correta;
  `/health` permanece publico; ausencia de token retorna 401 e permissao
  insuficiente retorna 403.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_protected_endpoints.py`.
- **Status:** Concluido.

### IMP-263 - Recertificar isolamento Tenant e Carteira

- **Objetivo:** provar ocultacao logica e ausencia de vazamento cross-tenant ou
  cross-carteira em todos os fluxos do MVP.
- **Componentes afetados:** `tests/integration/api/`, `tests/integration/application/`.
- **Dependencias:** IMP-262.
- **Criterios de conclusao:** recurso fora do escopo retorna 404 logico quando
  aplicavel e nunca permite mutacao indireta.
- **Suite minima:** `uv run pytest tests/integration/api`.
- **Status:** Concluido.

### IMP-264 - Recertificar idempotencia e replay

- **Objetivo:** cobrir payload igual, payload divergente, rollback, replay e
  efeitos duplicados nos fluxos mutaveis do MVP.
- **Componentes afetados:** `tests/integration/api/`, `tests/integration/application/`.
- **Dependencias:** IMP-257..IMP-261.
- **Criterios de conclusao:** chave repetida replaya resultado consistente;
  payload divergente retorna 409; rollback nao deixa efeito parcial indevido.
- **Suite minima:** `uv run pytest tests/integration/api tests/integration/application`.
- **Status:** Concluido.

### IMP-265 - Recertificar auditoria append-only

- **Objetivo:** provar trilha independente em provisionamento, IAM, contratos,
  operacao, configuracoes, automacao e falhas administrativas.
- **Componentes afetados:** `tests/integration/application/`, `tests/integration/api/`.
- **Dependencias:** IMP-264.
- **Criterios de conclusao:** eventos de auditoria sobrevivem a rollback quando
  ADR-002 exige, sao imutaveis e preservam correlation ID.
- **Suite minima:** `uv run pytest tests/integration/application`.
- **Status:** Concluido.

## P3 - Operacao, Migrations e Worker

### IMP-266 - Recertificar migrations e seed minimo do MVP

- **Objetivo:** validar upgrade/downgrade/upgrade ate a head atual, constraints,
  indices criticos e dados minimos necessarios ao smoke.
- **Componentes afetados:** `migrations/`, `scripts/validate_migrations.py`,
  `tests/integration/migrations/`.
- **Dependencias:** IMP-256.
- **Criterios de conclusao:** migrations reproduziveis passam sem alteracao
  destrutiva em tabelas dos EPICs 001 a 010.
- **Suite minima:** `npm run quality:migrations`.
- **Status:** Concluido.

### IMP-267 - Recertificar health, logs, erros e correlation ID

- **Objetivo:** provar contrato operacional da API em 2xx, 4xx e 5xx, incluindo
  mascaramento e ausencia de stack trace publico.
- **Componentes afetados:** `tests/integration/api/`, `tests/unit/`.
- **Dependencias:** IMP-256.
- **Criterios de conclusao:** `/health` nao vaza segredo, DSN, token, PII ou
  dado financeiro; `X-Correlation-ID` aparece em todas as respostas.
- **Suite minima:** `uv run pytest tests/integration/api/test_observability_api.py tests/unit/test_logging_observability.py`.
- **Status:** Concluido.

### IMP-268 - Recertificar worker Scheduler em smoke operacional

- **Objetivo:** executar worker com banco e fake Notification, verificando
  claim, lease, retry, shutdown, health interno e logs.
- **Componentes afetados:** `tests/unit/worker/`, `tests/integration/repositories/`.
- **Dependencias:** IMP-261 e IMP-267.
- **Criterios de conclusao:** worker separado da API fica saudavel apenas com
  configuracao valida, nao perde excecoes de Future e nao excede concorrencia.
- **Suite minima:** `uv run pytest tests/unit/worker tests/integration/repositories/test_scheduler_concurrency.py`.
- **Status:** Concluido.

## P4 - Contratos HTTP, OpenAPI e Documentacao Historica

### IMP-269 - Recertificar OpenAPI contra rotas reais

- **Objetivo:** comparar paths, methods, security, schemas, `X-Correlation-ID`
  e respostas documentadas.
- **Componentes afetados:** `src/emprestimo/presentation/api/openapi.py`,
  `tests/integration/api/`.
- **Dependencias:** IMP-262 e IMP-267.
- **Criterios de conclusao:** nenhuma rota implementada fica fora do OpenAPI e
  nenhum path documentado aponta para endpoint inexistente.
- **Suite minima:** `uv run pytest tests/integration/api`.
- **Status:** Concluido.

### IMP-270 - Criar matriz global HTTP 400/401/403/404/409

- **Objetivo:** consolidar e testar respostas esperadas por contexto e endpoint.
- **Componentes afetados:** `docs/implementation/reports/`, `tests/integration/api/`.
- **Dependencias:** IMP-269.
- **Criterios de conclusao:** payload invalido retorna 400, autenticacao 401,
  permissao 403, escopo/inexistencia 404 e conflito/idempotencia/estado 409.
- **Suite minima:** `uv run pytest tests/integration/api`.
- **Status:** Concluido.

### IMP-271 - Classificar documentacao historica desatualizada

- **Objetivo:** revisar discoveries, auditorias, handoffs, planos e relatorios
  antigos para separar historico aceito de divergencia ativa.
- **Componentes afetados:** `docs/audits/`, `docs/governance/`, `docs/implementation/reports/`.
- **Dependencias:** IMP-255 e IMP-270.
- **Criterios de conclusao:** nenhum documento historico apresenta caveat
  superado como pendencia atual; divergencias sao anotadas sem reescrever
  identidade historica.
- **Suite minima:** `npm run docs:validate && npm run docs:test`.
- **Status:** Concluido.

## P5 - Certificacao Final

### IMP-272 - Executar recertificacao completa do backend MVP

- **Objetivo:** rodar todos os gates oficiais e smokes definidos no PLAN-020.
- **Componentes afetados:** `tests/`, `docs/implementation/reports/`.
- **Dependencias:** IMP-254..IMP-271.
- **Criterios de conclusao:** pytest, ruff, black, mypy, docs, migrations,
  smoke API, smoke worker e guardrails passam sem achado bloqueante.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido.

### IMP-273 - Emitir relatorio de prontidao do Backend MVP

- **Objetivo:** registrar escopo certificado, evidencias, caveats reais,
  riscos residuais e recomendacao de proximo ciclo.
- **Componentes afetados:** `docs/implementation/reports/`.
- **Dependencias:** IMP-272.
- **Criterios de conclusao:** relatorio distingue backend pronto, pendencias
  nao bloqueantes, bloqueios reais e decisao recomendada sobre frontend ou
  hardening.
- **Suite minima:** `npm run docs:validate && npm run docs:test`.
- **Status:** Concluido.

---

# 3. Gates de Execucao

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- `node scripts/tests/test-plan-020-contracts.js`;
- `npm run quality:migrations`;
- smoke API com PostgreSQL real;
- smoke worker Scheduler com fake Notification;
- revisao adversarial final sem achados bloqueantes.

---

# 4. Criterios de Controle

- suites de regressao precedem correcoes;
- nenhum novo EPIC funcional e emitido sem evidencia de necessidade;
- nenhum frontend e iniciado;
- nenhuma regra financeira e alterada;
- nenhum teste ou guardrail e enfraquecido para passar gate;
- todo gap possui evidencia em codigo, teste ou documentacao;
- todo caveat final e classificado como bloqueante, nao bloqueante,
  preexistente ou ambiental.

---

# 5. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.7.0 | 2026-08-12 | IMP-272 e IMP-273 concluidos com recertificacao completa e relatorio final de prontidao do Backend MVP. |
| 1.6.0 | 2026-08-12 | IMP-269 a IMP-271 concluidos com recertificacao OpenAPI, matriz HTTP global e classificacao de documentacao historica. |
| 1.5.0 | 2026-08-12 | IMP-266 a IMP-268 concluidos com recertificacao de migrations, health/logs/correlation ID e smoke operacional do worker Scheduler. |
| 1.4.0 | 2026-08-12 | IMP-262 a IMP-265 concluidos com suite P2 de seguranca, isolamento, idempotencia e auditoria append-only do Backend MVP. |
| 1.3.0 | 2026-08-12 | IMP-257 a IMP-261 concluidos com suite E2E transversal cobrindo IAM/Cadastro, Comercial/Contratos, Motor, Operacao Diaria, Agenda/Scheduler/Notification. |
| 1.2.0 | 2026-08-12 | IMP-255 e IMP-256 concluidos com inventario FastAPI/OpenAPI e baseline P0 registrados em relatorio. |
| 1.1.0 | 2026-08-12 | IMP-254 concluido com suite contratual do PLAN-020 integrada ao `npm run docs:test`. |
| 1.0.0 | 2026-08-12 | Backlog inicial do PLAN-020 com IMP-254..IMP-273 em P0 a P5. |
