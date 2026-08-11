# EPIC-008 - Discovery/SDD de Fundacao Operacional e Observabilidade

**ID:** EPIC-008

**Tipo:** Artefato de Discovery/SDD

**Versao:** 1.1.0

**Status:** Aprovado para implementacao

---

# 1. Objetivo

Este discovery prepara o ciclo do EPIC-008 - Fundacao Operacional e
Observabilidade.

O objetivo e transformar o backend, ja funcionalmente rico apos IAM, Comercial,
Contratos, Motor Financeiro e Operacao Diaria, em um servico operacionalmente
confiavel: validado por pipeline reproduzivel, observavel em runtime, rastreavel
por correlation ID, com healthcheck real e pronto para evoluir read models,
eventos internos, Scheduler e Notification em ciclos posteriores.

Este Epic nao nasce para adicionar regra de negocio de credito. Ele nasce para
reduzir risco operacional antes de acelerar novos contextos.

---

# 2. Autoridades Consultadas

- `docs/foundation/FOUNDATION-007-product-map.md`;
- `docs/foundation/FOUNDATION-008-mvp-scope.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`;
- `docs/architecture/amp/DOCUMENT-ARCHITECTURE-MIGRATION-PLAN.md`;
- `docs/architecture/amp/DOCUMENT-ARCHITECTURE-DISCOVERY.md`;
- `docs/audits/audits/raio-x-arquitetural-ecossistema.md`;
- `docs/audits/audits/auditoria-as-is-to-be-ecossistema.md`;
- `docs/operations/quality-gates-and-migrations.md`;
- `docs/product/credit/epics/EPIC-007-operacao-diaria.md`;
- `docs/implementation/plans/PLAN-014-epic-007-operacao-diaria.md`.

---

# 3. Contexto

O roadmap arquitetural consolidado posiciona as seguintes entregas como ja
enderecadas no backend:

1. Platform e Tenant Management;
2. IAM com autenticacao, autorizacao RBAC e protecao de endpoints;
3. Cadastro de Devedores;
4. Comercial, Propostas e Simulacao;
5. Contratos de Credito;
6. Emprestimos, Pagamentos e Motor Financeiro;
7. Operacao Diaria manual com Cobranca, Agenda, Comunicacao e Relatorios.

O AMP-001 ainda registra dividas perigosas de engenharia: CI/CD, observabilidade,
logs estruturados, correlation ID e healthcheck real. Tambem posiciona Event
Bus, Scheduler, Notification e Read Models como evolucoes proximas, mas essas
evolucoes precisam de uma base operacional minima para serem confiaveis.

O EPIC-008 fecha essa lacuna. Ele deve ser tratado como pacote transversal de
Platform/Engineering, com impacto em toda a API, mas sem alterar invariantes de
dominio financeiro.

---

# 4. Problema

O backend ja consegue executar fluxos de negocio, mas ainda depende demais de
validacao manual e de observacao indireta. Em producao, isso cria riscos:

- regressao entrar sem rodar a mesma matriz de qualidade local;
- endpoint parecer saudavel mesmo com dependencia critica indisponivel;
- erro de producao nao ter request ID/correlation ID para rastreio;
- logs tecnicos nao permitirem seguir uma requisicao ponta a ponta;
- migrations serem aplicadas sem uma rotina padrao de validacao;
- relatorios e operacoes futuras ficarem pesados sem preparo de read models;
- Scheduler/Notification/Event Bus nascerem sem base de operacao e diagnostico.

---

# 5. Escopo

O EPIC-008 contempla:

- definir pipeline de qualidade reproduzivel para PR e `master`;
- executar gates de backend e documentacao em CI;
- validar migrations de forma reproduzivel;
- padronizar healthcheck real com status de aplicacao e banco de dados;
- expor endpoint publico minimo de health, sem vazar dados sensiveis;
- introduzir correlation ID por requisicao HTTP;
- propagar correlation ID para logs, erros e auditoria tecnica quando aplicavel;
- padronizar logs estruturados com campos minimos;
- registrar tratamento consistente de excecoes inesperadas;
- definir runbook minimo de operacao local/CI;
- definir contrato inicial para Event Bus interno em memoria ou porta de dominio;
- definir diretrizes para read models/projections sem obrigar separacao fisica;
- manter compatibilidade com IAM/RBAC e contratos HTTP existentes;
- criar suites de guardrail para impedir que observabilidade altere regra de
  negocio ou exponha segredo.

---

# 6. Fora do Escopo

Este Epic nao contempla:

- envio automatico de WhatsApp, SMS, e-mail ou push;
- Scheduler, cron, batch operacional ou job queue de producao;
- Event Bus externo, broker, outbox transacional completa ou mensageria
  distribuida;
- metricas de runtime, dashboards externos de APM, tracing distribuido completo
  ou alerting SaaS;
- plataforma de deploy, provisionamento cloud ou infraestrutura como codigo
  completa;
- API publica para parceiros, rate limiting externo ou API Gateway;
- BI avancado, data lake, analytics ou materialized views complexas;
- mudanca no modelo multi-tenant nivel 1;
- mudanca em calculos financeiros, memoria de calculo, juros, quitacao ou
  renegociacao;
- frontend.

---

# 7. Fronteiras

| Contexto | Relacao com EPIC-008 | Regra de fronteira |
|---|---|---|
| Platform | Contexto primario | hospeda preocupacoes transversais de runtime, configuracao e health. |
| IAM | Upstream transversal | autenticacao/autorizacao seguem intactas; health publico e excecao explicita. |
| Credit | Consumidor | endpoints de credito recebem correlation ID e logs sem alterar regras. |
| Motor Financeiro | Consumidor protegido | observabilidade nao calcula, arredonda ou altera fatos financeiros. |
| Relatorios | Consumidor/futuro upstream de read models | EPIC-008 prepara diretrizes; nao cria BI avancado. |
| Event Bus | Futuro tecnico | pode nascer como porta/contrato interno, sem broker externo obrigatorio. |
| Scheduler | Futuro | depende de health/logs/correlation para diagnostico, mas nao entra neste ciclo. |
| Notification | Futuro | depende de logs/correlation e contratos de canal, mas nao envia mensagens neste ciclo. |
| Observability | Cross-cutting | coleta fatos tecnicos; nao substitui auditoria de negocio da ADR-002. |

---

# 8. Decisoes de Discovery

## DA-801 - EPIC transversal de engenharia

O EPIC-008 sera tratado como pacote transversal de Platform/Engineering. Ele nao
cria nova regra de negocio e nao pertence a uma capability funcional de credito.

## DA-802 - Healthcheck publico e minimo

O healthcheck permanece publico, mas deve retornar apenas informacao operacional
minima: status da aplicacao, status agregado de dependencias criticas e versao
quando disponivel. Nao deve expor tenant, credenciais, DSN, stack trace ou
detalhes sensiveis.

## DA-803 - Correlation ID por borda HTTP

Toda requisicao deve possuir um correlation ID. Se o cliente enviar um valor
aceito, ele e reaproveitado; caso contrario, a API gera um novo. A resposta deve
devolver o correlation ID para permitir rastreio pelo cliente e pelo suporte.

## DA-804 - Logs tecnicos nao sao auditoria de negocio

Logs estruturados sao telemetria tecnica. Metricas de runtime podem evoluir em
ciclo posterior, mas nao fazem parte da entrega minima deste EPIC. A trilha de
auditoria de negocio continua sendo a definida pela ADR-002 e nao pode ser
substituida por logs.

## DA-805 - Pipeline reproduzivel antes de automacao operacional

Scheduler, Notification, Event Bus externo e read models pesados so devem avancar
apos existir pipeline de qualidade e observabilidade basica para diagnosticar
falhas.

## DA-806 - Event Bus inicial como contrato interno

Quando necessario neste ciclo, Event Bus deve nascer como porta/contrato interno
ou publicador em memoria, suficiente para desacoplar produtores e consumidores
dentro do monolito. Broker externo e outbox completa ficam para ADR propria.

## DA-807 - Read models sem verdade paralela

Read models e projections podem acelerar leituras, mas nao viram fonte oficial
de regra financeira. Devem ser reconstruiveis a partir dos fatos oficiais e
preservar origem, versao e data de referencia.

## DA-808 - Observabilidade sem vazamento

Logs, erros e healthcheck nao podem expor credenciais, tokens, hashes, payloads
sensiveis, documentos pessoais completos ou valores internos de configuracao.
Quando metricas forem introduzidas em ciclo posterior, elas devem obedecer ao
mesmo criterio de nao vazamento.

---

# 9. Features Candidatas

## 9.1 Pipeline de Qualidade e Migrations

Objetivo: garantir que cada PR e `master` executem a matriz minima de qualidade
do backend e da documentacao.

Escopo candidato:

- rodar `uv run pytest -q`;
- rodar `uv run ruff check .`;
- rodar `uv run black --check .`;
- rodar `uv run mypy src tests`;
- rodar `npm run docs:test`;
- rodar `npm run docs:validate`;
- executar rotina de validacao de migrations;
- documentar comandos equivalentes para execucao local.

## 9.2 Healthcheck Real

Objetivo: tornar o endpoint de saude confiavel para operacao e deploy.

Escopo candidato:

- verificar aplicacao;
- verificar conectividade com banco;
- separar estados `healthy`, `degraded` e `unhealthy`;
- retornar status HTTP coerente;
- manter endpoint publico e sem dados sensiveis;
- cobrir falha de banco por teste.

## 9.3 Correlation ID e Logs Estruturados

Objetivo: permitir rastrear uma requisicao em logs e resposta HTTP.

Escopo candidato:

- middleware de correlation ID;
- header de entrada e saida;
- contexto de log por requisicao;
- campos minimos: timestamp, level, logger, correlation_id, metodo, rota,
  status_code e duracao;
- mascaramento de dados sensiveis;
- testes de propagacao e geracao automatica.

## 9.4 Erros Tecnicos e Runbook Operacional

Objetivo: padronizar tratamento de falhas inesperadas e resposta operacional.

Escopo candidato:

- resposta 500 sem stack trace;
- logging de excecao com correlation ID;
- runbook minimo para falha de banco, migration, testes e rollback manual;
- guia de leitura de logs;
- matriz de sintomas e comandos de diagnostico.

## 9.5 Contrato Inicial de Eventos e Projections

Objetivo: preparar evolucao para Event Bus/read models sem acoplamento novo.

Escopo candidato:

- porta de publicacao de eventos de dominio;
- contrato minimo de envelope de evento;
- idempotencia e versao do evento;
- diretrizes de projection/read model reconstruivel;
- guardrail para impedir projection como fonte de calculo financeiro.

---

# 10. User Stories Oficiais

As User Stories abaixo foram materializadas na fase Product do EPIC-008 e seus
IDs oficiais foram registrados em `docs/governance/registry/identifier-registry.json`.

| ID | Intencao |
|----|----------|
| US-089 | Executar gates oficiais em PR e `master`. |
| US-090 | Validar migrations de forma reproduzivel. |
| US-091 | Consultar healthcheck real. |
| US-092 | Impedir vazamento no healthcheck publico. |
| US-093 | Propagar correlation ID HTTP. |
| US-094 | Correlacionar erros tecnicos. |
| US-095 | Registrar logs estruturados seguros. |
| US-096 | Operar falhas com runbook minimo. |
| US-097 | Definir contrato inicial de eventos internos. |
| US-098 | Proteger projections contra verdade paralela. |

---

# 11. Contratos Tecnicos Candidatos

## 11.1 Healthcheck

Endpoint candidato:

- `GET /health`

Matriz candidata de estado HTTP:

| Estado | HTTP | Cenario |
|--------|------|---------|
| `healthy` | `200` | aplicacao e banco aptos a receber trafego. |
| `degraded` | `503` | aplicacao responde, mas dependencia critica esta degradada. |
| `unhealthy` | `503` | aplicacao ou banco indisponivel para trafego normal. |

Resposta candidata `200`:

```json
{
  "status": "healthy",
  "service": "emprestimo-api",
  "dependencies": {
    "database": "healthy"
  },
  "correlation_id": "..."
}
```

Resposta candidata `503`:

```json
{
  "status": "unhealthy",
  "service": "emprestimo-api",
  "dependencies": {
    "database": "unhealthy"
  },
  "correlation_id": "..."
}
```

## 11.2 Correlation ID

Headers candidatos:

- entrada: `X-Correlation-ID`;
- saida: `X-Correlation-ID`.

Regras candidatas:

- valor ausente gera novo ID;
- valor invalido e substituido por novo ID;
- valor aceito deve aparecer nos logs e na resposta;
- erros 4xx/5xx tambem devolvem o correlation ID.

## 11.3 Evento Interno

Envelope candidato:

```json
{
  "event_id": "...",
  "event_type": "PagamentoRegistrado",
  "event_version": 1,
  "occurred_at": "2026-08-11T00:00:00Z",
  "tenant_id": "...",
  "correlation_id": "...",
  "payload": {}
}
```

---

# 12. Plano Inicial de Testes

## 12.1 Suites de CI

- teste que valida a existencia dos jobs esperados no pipeline;
- teste local que confirma comandos documentados;
- validacao de migrations em ambiente controlado;
- smoke test de API.

## 12.2 Healthcheck

- `GET /health` retorna `200` com banco disponivel;
- `GET /health` retorna `503` com estado `degraded` ou `unhealthy` quando
  dependencia critica falha;
- resposta nao contem DSN, senha, token, stack trace ou variavel sensivel;
- healthcheck permanece publico, sem depender de token.

## 12.3 Correlation ID e Logs

- request sem header recebe correlation ID gerado;
- request com header valido preserva o valor;
- response 2xx, 4xx e 5xx devolvem correlation ID;
- log de requisicao contem correlation ID;
- dados sensiveis sao mascarados.

## 12.4 Guardrails

- observabilidade nao altera payload de dominio;
- logs nao substituem audit log de negocio;
- projections/read models nao calculam juros, saldo, quitacao, amortizacao ou
  memoria de calculo;
- eventos internos nao permitem reprocessamento duplicado sem idempotencia.

---

# 13. Riscos

| Risco | Impacto | Mitigacao |
|---|---|---|
| EPIC virar infraestrutura demais | ciclo grande e pouco verificavel | limitar a CI, health, logs, correlation e contratos internos minimos. |
| Logs vazarem dados sensiveis | risco de seguranca e LGPD | mascaramento por padrao e testes negativos. |
| Healthcheck expor detalhes internos | superficie de ataque | resposta minima e sem stack/DSN. |
| Event Bus crescer para broker completo | atraso e complexidade | nascer apenas como porta/contrato interno. |
| Read model virar fonte financeira | quebra do Motor como autoridade | guardrail anti-calculo e reconstrucao por fatos oficiais. |
| Pipeline divergir do ambiente local | falso verde/vermelho | documentar comandos identicos e rodar suites locais no CI. |

---

# 14. Criterios de Pronto para PLAN

O EPIC-008 estara pronto para PLAN tecnico quando:

- Arquitetura confirmar que o pacote sera tratado como Platform/Engineering;
- Product aceitar que nao ha nova regra de negocio de credito neste ciclo;
- escopo e fora do escopo deste discovery forem aprovados;
- Features e User Stories oficiais forem emitidas ou explicitamente dispensadas
  por se tratar de pacote tecnico transversal;
- ADRs necessarias forem decididas: ADR-015 (CI/CD), ADR-016
  (Observability/Logging) e, se entrar no ciclo, recorte minimo de ADR-005
  (Event Bus);
- backlog de IMPs separar P0 pipeline, P1 health, P2 correlation/logs, P3
  runbook, P4 eventos/projections e P5 recertificacao.

---

# 15. Recomendacao de Sequencia

1. Materializar a camada Product do EPIC-008 ou registrar excecao tecnica
   governada.
2. Emitir ADR-015 e ADR-016, ou confirmar que o PLAN pode implementa-las com
   decisao local temporaria.
3. Criar `PLAN-015 - EPIC-008 Fundacao Operacional e Observabilidade`.
4. Criar execution backlog com IMPs pequenos e testaveis.
5. Implementar primeiro pipeline e healthcheck; depois correlation/logs; por
   ultimo eventos/read models minimos.
6. Recertificar `master` com gates locais e CI.

---

# 16. Parecer

O proximo EPIC recomendado e o EPIC-008 - Fundacao Operacional e
Observabilidade.

Ele e mais urgente que Scheduler, Notification, Workflow ou Integracoes porque
reduz risco de operacao e torna os proximos ciclos diagnosticaveis. Sem ele, a
plataforma continuaria funcional em ambiente controlado, mas fragil para
producao e para automacoes futuras.

---

# 17. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-11 | Product, ADRs e PLAN-015 materializados para o EPIC-008. |
| 1.0.0 | 2026-08-11 | Discovery/SDD inicial do EPIC-008 - Fundacao Operacional e Observabilidade. |
