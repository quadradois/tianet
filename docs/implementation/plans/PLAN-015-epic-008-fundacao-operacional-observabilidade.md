# PLAN-015 - Plano Tecnico do EPIC-008/Fundacao Operacional e Observabilidade

**ID:** PLAN-015

**Versao:** 1.0.0

**Status:** Implementado

---

# 1. Contexto

Este plano executa o EPIC-008/Fundacao Operacional e Observabilidade apos a
recertificacao dos EPICs de IAM, Comercial, Contratos, Motor Financeiro e
Operacao Diaria.

O objetivo e pagar a divida operacional apontada pelo AMP-001: CI/CD,
healthcheck real, logs estruturados, correlation ID, tratamento tecnico de
erros e base inicial para eventos/projections. O plano nao altera regra de
negocio de credito.

---

# 2. Referencias

- `docs/audits/discoveries/EPIC-008-fundacao-operacional-observabilidade-discovery.md`;
- `docs/product/platform/capabilities/PRODUCT-001-administrar-plataforma.md`;
- `docs/product/platform/epics/EPIC-008-fundacao-operacional-observabilidade.md`;
- `docs/product/platform/features/FEATURE-032-automatizar-pipeline-de-qualidade.md`;
- `docs/product/platform/features/FEATURE-033-validar-saude-operacional-backend.md`;
- `docs/product/platform/features/FEATURE-034-rastrear-requisicoes-correlation-id.md`;
- `docs/product/platform/features/FEATURE-035-padronizar-logs-erros-tecnicos.md`;
- `docs/product/platform/features/FEATURE-036-preparar-eventos-internos-projections.md`;
- `docs/product/platform/user-stories/US-089-executar-gates-oficiais-pr-master.md`;
- `docs/product/platform/user-stories/US-090-validar-migrations-forma-reproduzivel.md`;
- `docs/product/platform/user-stories/US-091-consultar-healthcheck-real.md`;
- `docs/product/platform/user-stories/US-092-impedir-vazamento-healthcheck.md`;
- `docs/product/platform/user-stories/US-093-propagar-correlation-id-http.md`;
- `docs/product/platform/user-stories/US-094-correlacionar-erros-tecnicos.md`;
- `docs/product/platform/user-stories/US-095-registrar-logs-estruturados-seguros.md`;
- `docs/product/platform/user-stories/US-096-operar-falhas-runbook-minimo.md`;
- `docs/product/platform/user-stories/US-097-definir-contrato-inicial-eventos-internos.md`;
- `docs/product/platform/user-stories/US-098-proteger-projections-verdade-paralela.md`;
- `docs/architecture/adrs/ADR-005-event-bus-interno-eventos-dominio.md`;
- `docs/architecture/adrs/ADR-015-ci-cd-gates-qualidade.md`;
- `docs/architecture/adrs/ADR-016-observability-logging-correlation-id.md`;
- `docs/operations/quality-gates-and-migrations.md`.

---

# 3. Situacao Atual

## Concluido e pronto para reutilizar

- IAM operacional, com `/health` publico como excecao;
- suites globais locais verdes no master pos-merge;
- script `quality:migrations` ja declarado em `package.json`;
- validadores documentais e de identifiers estabilizados;
- guardrails de calculo financeiro fora do Motor ja usados em EPIC-005 e
  EPIC-007.

## Pendencias para este plano

- pipeline de qualidade em CI;
- healthcheck real com banco;
- middleware/contrato de correlation ID;
- logs estruturados e mascaramento;
- resposta tecnica segura para excecao inesperada;
- runbook operacional minimo;
- contrato interno de eventos/projections;
- recertificacao completa.

---

# 4. Decisoes Tecnicas

## D1 - EPIC tecnico transversal em Platform

O EPIC-008 e executado sob PRODUCT-001 como excecao tecnica governada. Ele nao
cria nova capability funcional nem inaugura Bounded Context autonomo de
Observability.

## D2 - CI equivale aos gates locais

O pipeline deve executar a mesma matriz usada para recertificacao local:
pytest, ruff, black, mypy, docs:test, docs:validate e migrations.

## D3 - Healthcheck publico e minimo

`GET /health` permanece publico. A resposta informa saude operacional sem
expor tenant, usuario, DSN, token, stack trace ou configuracao sensivel. Os
estados publicos sao `healthy`, `degraded` e `unhealthy`, com HTTP `200` para
`healthy` e HTTP `503` para `degraded` ou `unhealthy`.

## D4 - Correlation ID na borda HTTP

Toda requisicao recebe correlation ID. A API aceita `X-Correlation-ID` valido,
gera valor quando ausente/invalido e devolve o header em respostas 2xx, 4xx e
5xx.

## D5 - Logs tecnicos nao substituem auditoria

Logs estruturados sao telemetria tecnica. Metricas de runtime ficam para ciclo
posterior e, quando introduzidas, tambem nao substituem auditoria de negocio.
A auditoria de negocio continua governada pela ADR-002.

## D6 - Eventos/projections sem infraestrutura distribuida

O ciclo pode definir porta interna e envelope de evento, mas nao implementa
broker externo, outbox completa, Saga ou mensageria distribuida.

## D7 - Projections nao calculam valores financeiros

Read models e projections sao reconstruiveis a partir de fatos oficiais e nao
calculam juros, saldo, quitacao, amortizacao ou memoria fora do Motor.

---

# 5. Modelo Tecnico Candidato

Componentes candidatos:

- middleware HTTP de correlation ID;
- configuracao de logging estruturado;
- helper de mascaramento de campos sensiveis;
- handler global de excecoes inesperadas;
- health service com check de banco;
- porta `EventPublisher`;
- envelope `DomainEventEnvelope`;
- contrato de projection reconstruivel;
- workflow CI em `.github/workflows/`;
- runbook em `docs/operations/`.

Nenhum desses componentes deve depender de regra financeira especifica.

---

# 6. API

Rotas afetadas:

- `GET /health` - publico, retorna saude operacional minima;
- todas as rotas HTTP existentes - passam a devolver `X-Correlation-ID`;
- OpenAPI deve documentar o header de correlation ID e contrato de health.

O plano nao cria endpoints de negocio novos.

## Fora do escopo tecnico deste ciclo

- Scheduler de producao;
- Notification real;
- broker externo;
- outbox completa;
- dashboards APM externos;
- infraestrutura cloud/IaC completa;
- frontend;
- qualquer mudanca em regra financeira.

---

# 7. Estrategia de Testes

- **CI contract:** valida existencia e comandos obrigatorios do workflow;
- **Migrations:** valida rotina reproduzivel de upgrade/downgrade quando
  suportado;
- **Healthcheck:** banco saudavel, banco indisponivel e resposta publica minima;
- **Correlation ID:** header ausente, valido, invalido, 2xx, 4xx e 5xx;
- **Logs:** campos minimos e mascaramento;
- **Erros tecnicos:** 500 seguro e log com correlation ID;
- **Eventos/projections:** envelope minimo, idempotencia e guardrail anti-Motor;
- **Docs:** registry, Product, ADRs, PLAN e backlog consistentes.

---

# 8. Ordem de Implementacao

1. suites e validadores antes de codigo operacional;
2. pipeline e migrations;
3. healthcheck real;
4. correlation ID e logs estruturados;
5. tratamento de erros e runbook;
6. eventos internos/projections minimos;
7. OpenAPI e recertificacao global.

Cada tarefa inicia somente com dependencias satisfeitas no backlog.

---

# 9. Gates de Aceite

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:test`;
- `npm run docs:validate`;
- `npm run quality:migrations`;
- pipeline declarado e equivalente aos comandos locais;
- `/health` publico, real e sem vazamento;
- `X-Correlation-ID` em respostas 2xx, 4xx e 5xx;
- resposta 500 sem stack trace;
- logs estruturados com mascaramento;
- eventos/projections sem calculo financeiro fora do Motor.

---

# 10. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Plano tecnico inicial do EPIC-008/Fundacao Operacional e Observabilidade. |
| 1.1.0 | 2026-08-11 | Macro-loop IMP-186 a IMP-200 implementado e recertificado localmente. |
