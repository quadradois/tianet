# PLAN-018 - Plano Tecnico do EPIC-010/Automacao Operacional, Scheduler e Notificacoes

**ID:** PLAN-018

**Versao:** 1.0.0

**Status:** Planejado

---

# 1. Contexto

Este plano transforma o Product e as decisoes arquiteturais do EPIC-010 em uma
sequencia implementavel para automatizar Lembretes por jobs duraveis e enviar
e-mail transacional governado.

O Scheduler executa trabalho no horario, mas o dominio de origem decide se o
efeito continua elegivel. Notification solicita o envio e interpreta evidencia
tecnica do canal, sem substituir Comunicacao nem alterar fatos financeiros.

---

# 2. Referencias

- `docs/audits/discoveries/EPIC-010-automacao-operacional-scheduler-notificacoes-discovery.md`;
- `docs/product/credit/epics/EPIC-010-automacao-operacional-scheduler-notificacoes.md`;
- `docs/product/credit/features/FEATURE-042-automatizar-lembretes-operacionais.md`;
- `docs/product/credit/features/FEATURE-043-processar-jobs-duraveis.md`;
- `docs/product/credit/features/FEATURE-044-enviar-notificacoes-transacionais.md`;
- `docs/product/credit/features/FEATURE-045-operar-reconciliar-automacao.md`;
- `docs/product/credit/user-stories/US-113-agendar-lembrete-automatico.md` a
  `docs/product/credit/user-stories/US-124-proteger-automacao-vazamento-calculo.md`;
- `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md`;
- `docs/architecture/adrs/ADR-005-event-bus-interno-eventos-dominio.md`;
- `docs/architecture/adrs/ADR-007-scheduler-batch-processing.md`;
- `docs/architecture/adrs/ADR-009-notifications-channels.md`;
- `docs/architecture/adrs/ADR-015-ci-cd-gates-qualidade.md`;
- `docs/architecture/adrs/ADR-016-observability-logging-correlation-id.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`;
- `docs/foundation/FOUNDATION-007-product-map.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/operations/observability-runbook.md`.

---

# 3. Situacao Atual

## Concluido e pronto para reutilizar

- Agenda, Lembretes e Comunicacao Manual do EPIC-007 estao implementados;
- IAM/RBAC, correlation ID, logs seguros, health e auditoria estao disponiveis;
- PostgreSQL 16, SQLAlchemy, Alembic, UnitOfWork e gates de migrations estao
  estabilizados;
- `httpx` ja integra a stack do backend;
- Product, Features e User Stories do EPIC-010 foram materializados;
- ADR-007 e ADR-009 foram aceitas e fecharam as decisoes anteriores ao PLAN.

## Pendencias para este plano

- suites de dominio, concorrencia, canal, crash/replay e guardrails;
- dominio e persistencia de jobs, tentativas, preferencias, templates e
  notificacoes;
- atomicidade entre Agenda e Scheduler e entre aceite, Lembrete, Comunicacao e
  conclusao do job;
- processo worker separado, claim, lease, retry, shutdown, health e retencao;
- porta `NotificationChannel`, fake deterministico e adaptador Resend REST;
- IAM, services administrativos, schemas, endpoints, OpenAPI e runbook;
- recertificacao integral do EPIC-010.

---

# 4. Decisoes Tecnicas

## D1 - Scheduler executa; a origem decide

Jobs guardam identidade e versao da origem. Todo handler recarrega e revalida o
Lembrete antes do efeito. Event Bus nao substitui a fila duravel.

## D2 - Fila duravel e worker separado

Jobs e tentativas usam PostgreSQL. O worker roda em processo separado da API,
com configuracao e pool proprios. Nao usa `BackgroundTasks` ou timers em
memoria como fonte de verdade.

## D3 - Claim limitado e lease com fencing

O claim usa `FOR UPDATE SKIP LOCKED`, ordem deterministica e no maximo
`min(batch_size, slots_de_execucao_livres)`. Token expirado ou substituido nao
conclui, renova ou reconcilia tentativa. O job preserva o correlation ID da
origem; cada tentativa gera e persiste um execution ID filho, e ambos atravessam
logs, metricas e efeitos.

## D4 - Relogio, retry, shutdown e retencao seguem ADR-007

`clock_timestamp()` do PostgreSQL governa elegibilidade, lease e lag. Sao cinco
tentativas totais, backoff 30s/2m/10m/30m com jitter governado, runtime padrao
de 300s, shutdown gracioso de 30s e retencao tecnica de 90 dias. Resultado
externo desconhecido nunca recebe retry automatico.

## D5 - Transacoes curtas ao redor do efeito externo

Persistencia da intencao ocorre antes do envio. A chamada ao provedor acontece
fora de transacao longa. Depois do aceite, uma unica UnitOfWork idempotente
marca a notificacao, envia o estado do Lembrete, registra Comunicacao e conclui
o job.

Se houver aceite externo e rollback local, o worker consulta ou repete com a
mesma chave idempotente dentro da janela de 24h e reaplica a UnitOfWork. Fora da
janela, sem prova verificavel, marca `resultado_desconhecido` e nao reenvia.

## D6 - E-mail Resend por porta

O unico canal inicial e e-mail. `NotificationChannel` possui fake deterministico
para CI e adaptador Resend REST por `httpx` para envio e consulta verificavel de
status. Teste real usa projeto separado e e opt-in.

## D7 - Incerteza falha fechada

`5xx`, `2xx` malformado ou falha apos possivel transmissao resultam em
`resultado_desconhecido`. Somente evidencia consultada no provedor altera esse
estado; declaracao humana, print ou texto livre nao libera reenvio.

## D8 - Consentimento e templates sao governados

Ausencia ou ambiguidade de consentimento, opt-out, contato removido ou escopo
divergente bloqueiam antes da renderizacao. O template inicial e somente
`lembrete_operacional_v1`, com `data_hora` e `canal_atendimento`, versionado,
imutavel apos ativacao e sem mensagem livre.

O produtor governado de `PreferenciaNotificacao` e um servico interno chamado
pelos fluxos existentes de criacao/atualizacao de Contato no Cadastro. Ele exige
evidencia, origem, estado permitido/opt-out, instante, ator, Tenant e Carteira e
usa as permissoes ja aplicaveis ao Cadastro; nao cria rota publica de preferencia
nem permissao IAM nova. Contato legado sem evidencia permanece em default deny
ate atualizacao explicita e auditada pelo fluxo de Cadastro.

`ContatoPayload` ganha o grupo opcional `notificacao_estado`
(`permitido|opt_out`), `notificacao_evidencia` e `notificacao_origem`. Se um
campo do grupo vier, todos sao obrigatorios; ator e instante sao derivados do
Principal e do relogio do servidor. Ausencia do grupo preserva compatibilidade,
nao infere consentimento e nao cria preferencia. Contato e preferencia sao
gravados na mesma UnitOfWork: qualquer falha desfaz ambos. A substituicao de
contatos reconcilia preferencias removidas ou recriadas sem deixar permissao
vigente ligada a contato removido.

## D9 - Operacao administrativa sem disparo arbitrario

Consulta, cancelamento, retry tecnico, templates e conciliacao usam permissoes
distintas. O endpoint legado `enviar` vira alias depreciado de conciliacao e
jamais chama o provedor. Nao existe endpoint de envio arbitrario.

Permissoes obrigatorias: `automacao.job.consultar`,
`automacao.job.cancelar`, `automacao.job.retry`, `notificacao.consultar`,
`notificacao.conciliar` e `notificacao.template.gerir`. No MVP, a mesma pessoa pode criar e aprovar um
template se possuir a permissao; autoria, aprovacao e motivo ficam registrados,
sem introduzir aprovacao dupla.

Cancelamento, retry, preferencia, aprovacao/ativacao de template e conciliacao
geram auditoria append-only em sessao independente conforme ADR-002, inclusive
quando a transacao de negocio sofre rollback.

## D10 - Fronteiras protegidas

Scheduler e Notification propagam Tenant, Carteira e correlation ID, mascaram
PII e segredos e nao calculam nem reinterpretam juros, mora, multa, saldo,
amortizacao, quitacao, vencimento ou memoria de calculo. Vencimentos e situacao
financeira chegam somente por contrato/read model oficial do Motor; acesso
direto a tabelas ou reconstrucao paralela desses fatos e proibido.

---

# 5. Modelo Tecnico Candidato

- aggregate `JobAgendado` e entity `TentativaJob`;
- entities `PreferenciaNotificacao`, `TemplateNotificacao`,
  `SolicitacaoNotificacao` e `TentativaNotificacao`;
- value objects de lease, identidade idempotente, hash de payload, timezone e
  evidencia externa;
- ports de Clock, repositories, `NotificationChannel` e consulta de status;
- repositories PostgreSQL com claim atomico e fencing token;
- services de Agenda/Scheduler, templates, preferencia, envio e conciliacao;
- integracao interna Cadastro -> PreferenciaNotificacao para consentimento e
  opt-out governados;
- worker entrypoint separado, registry de handlers e supervisor;
- fake deterministico e adaptador Resend REST;
- permissoes IAM `automacao.job.*` e `notificacao.*`;
- read model protegido de health e operacao do worker.

---

# 6. Persistencia

Tabelas candidatas:

- `scheduler_jobs` e `scheduler_job_attempts`;
- `scheduler_worker_heartbeats`, persistido com uma linha por `worker_id`;
- `notification_preferences`;
- `notification_templates`;
- `notification_requests` e `notification_attempts`;
- extensao aditiva de Comunicacao para `notification_id`, template/versao,
  ator tecnico e evidencia protegida.

Restricoes minimas:

- indices de claim por estado e `scheduled_for`;
- unicidade do token vigente e fencing de conclusao;
- identidade idempotente e hash de payload unicos no escopo;
- um registro de Comunicacao por `notification_id`;
- isolamento por Tenant/Carteira e referencias consistentes com a origem;
- templates ativados imutaveis;
- upgrade/downgrade/upgrade reproduzivel;
- compatibilidade com Lembretes e Comunicacoes existentes;
- Lembretes `PROGRAMADO` legados permanecem manuais e nao recebem job por
  migration; somente opt-in explicito posterior, com horario futuro,
  consentimento vigente e auditoria, cria job pela UnitOfWork normal;
- purga somente de jobs/tentativas terminais apos 90 dias; pendencias
  administrativas e resultados desconhecidos nao sao purgados.

Cada worker atualiza seu heartbeat a cada 10 segundos. Readiness considera
stale acima de 30 segundos. Linhas stale sem lease ativo sao removidas apos 24
horas; somente o worker e a rotina de limpeza escrevem nessa tabela.

---

# 7. API

Rotas administrativas candidatas:

- `GET /credit/automacao/jobs`;
- `GET /credit/automacao/jobs/{job_id}`;
- `POST /credit/automacao/jobs/{job_id}/cancelar`;
- `POST /credit/automacao/jobs/{job_id}/retry`;
- `GET /credit/notificacoes`;
- `GET /credit/notificacoes/{notification_id}`;
- `POST /credit/notificacoes/{notification_id}/conciliar`;
- `GET /credit/notificacoes/templates`;
- `POST /credit/notificacoes/templates`;
- `POST /credit/notificacoes/templates/{template_id}/aprovar`;
- `POST /credit/notificacoes/templates/{template_id}/ativar`;
- `POST /credit/agenda/lembretes/{lembrete_id}/enviar`, alias depreciado de
  conciliacao, sem chamada ao provedor.

Nao existe rota de envio arbitrario. Health do worker e metricas detalhadas
ficam em mecanismo interno ou protegido e nao alteram o `/health` publico da
API. Todas as respostas incluem `X-Correlation-ID`; recursos fora do
Tenant/Carteira retornam `404` logico.

## Matriz HTTP

| Operacao | Sucesso | Erros documentados |
|---|---|---|
| `GET /credit/automacao/jobs` | 200 | 400, 401, 403 |
| `GET /credit/automacao/jobs/{job_id}` | 200 | 401, 403, 404 |
| `POST /credit/automacao/jobs/{job_id}/cancelar` | 202 | 400, 401, 403, 404, 409 |
| `POST /credit/automacao/jobs/{job_id}/retry` | 202 | 400, 401, 403, 404, 409 |
| `GET /credit/notificacoes` | 200 | 400, 401, 403 |
| `GET /credit/notificacoes/{notification_id}` | 200 | 401, 403, 404 |
| `POST /credit/notificacoes/{notification_id}/conciliar` | 200 | 400, 401, 403, 404, 409 |
| `GET /credit/notificacoes/templates` | 200 | 400, 401, 403 |
| `POST /credit/notificacoes/templates` | 201 | 400, 401, 403, 409 |
| `POST /credit/notificacoes/templates/{template_id}/aprovar` | 200 | 400, 401, 403, 404, 409 |
| `POST /credit/notificacoes/templates/{template_id}/ativar` | 200 | 400, 401, 403, 404, 409 |
| `POST /credit/agenda/lembretes/{lembrete_id}/enviar` | 200 | 400, 401, 403, 404, 409 |

---

# 8. Estrategia de Testes

## Rastreabilidade de Product para execucao

| Feature | User Stories | IMPs principais |
|---|---|---|
| FEATURE-042 | US-113, US-114 | IMP-225, IMP-226, IMP-228, IMP-230, IMP-235 |
| FEATURE-043 | US-115, US-116, US-117 | IMP-226, IMP-230, IMP-236..IMP-240 |
| FEATURE-044 | US-118, US-119, US-120, US-121 | IMP-227, IMP-228, IMP-231..IMP-245 |
| FEATURE-045 | US-122, US-123, US-124 | IMP-229, IMP-246..IMP-253 |

- **Documentacao:** Product, ADRs, PLAN, backlog, IMPs e registry consistentes;
- **Dominio:** estados, timezone IANA/UTC, cancelamento, retry, templates,
  consentimento, opt-out e imutabilidade;
- **Concorrencia PostgreSQL:** dois workers, capacidade livre, lease, fencing,
  expiracao, crash e restart;
- **Atomicidade:** Lembrete/job e aceite/notificacao/Lembrete/Comunicacao/job;
- **Canal:** fake, Resend, idempotencia, janela de 24h, timeout, 4xx, 5xx,
  resposta malformada e consulta de status;
- **Worker:** polling, backoff, runtime maximo, shutdown, health, retencao e
  revalidacao da origem;
- **Seguranca:** IAM, cross-tenant/carteira, PII, segredos e endpoint legado;
- **Guardrails:** sem calculo financeiro, broker, outbox, novo canal ou disparo
  arbitrario; vencimentos e situacao financeira somente pelo contrato/read
  model oficial do Motor;
- **API/OpenAPI:** rotas, security, idempotencia, deprecacao, schemas e erros;
- **Recertificacao:** suite Python, qualidade, docs, migrations e revisao
  adversarial final.

---

# 9. Ordem de Implementacao

1. P0, suites e guardrails antes do codigo;
2. P1, dominio, ports, migrations, repositories e UnitOfWork;
3. P2, worker Scheduler e operacao;
4. P3, Notification e efeitos externos;
5. P4, IAM, services administrativos, API e OpenAPI;
6. P5, guardrails finais e recertificacao completa.

O backlog usa `IMP-225..IMP-253`. Cada item inicia apenas com dependencias
anteriores satisfeitas.

---

# 10. Gates de Aceite

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- `node scripts/tests/test-epic-010-contracts.js`;
- `npm run quality:migrations`;
- concorrencia real PostgreSQL, crash/replay e migrations verdes;
- fake deterministico como padrao do CI e Resend real apenas opt-in;
- `/health` publico independente do health do worker;
- OpenAPI sem endpoint de disparo arbitrario;
- ausencia de PII, segredo e calculo financeiro fora do Motor;
- revisao adversarial final sem achados bloqueantes.

---

# 11. Fora do Escopo Tecnico

- frontend;
- SMS, WhatsApp, push, campanhas ou marketing;
- broker externo, outbox generica ou Workflow;
- webhooks, receipts de entrega/leitura ou promessa de entrega;
- cloud/IaC e dashboards APM externos;
- API publica para terceiros;
- qualquer alteracao de regra ou fato financeiro.

---

# 12. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-11 | Plano tecnico inicial do EPIC-010 com backlog IMP-225..IMP-253. |
