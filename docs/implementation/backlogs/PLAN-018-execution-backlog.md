# PLAN-018-EXEC - Backlog do EPIC-010/Automacao Operacional, Scheduler e Notificacoes

**ID:** PLAN-018-EXEC

**Versao:** 1.1.0

**Status:** Concluido

---

# 1. Contexto

Este backlog transforma o `PLAN-018` em ordem executavel. A numeracao continua
apos `IMP-224`, ultimo item do `PLAN-017-EXEC`. Os itens IMP-225..IMP-253 foram
implementados e recertificados no ciclo encerrado em 2026-08-11.

---

# 2. Ordem Executavel

## P0 - Suites e Guardrails antes do Codigo

### IMP-225 - Criar contratos documentais do EPIC-010 e PLAN-018

- **Objetivo:** proteger rastreabilidade Product/ADR/PLAN/backlog e IDs.
- **Componentes afetados:** `scripts/tests/test-epic-010-contracts.js`, `docs/implementation/`.
- **Dependencias:** EPIC-010, ADR-007 e ADR-009.
- **Criterios de conclusao:** mutacoes detectam IMP ausente/duplicado, dependencia futura e guardrail removido.
- **Suite minima:** `node scripts/tests/test-epic-010-contracts.js`.
- **Status:** Concluido.

### IMP-226 - Criar suites de dominio e concorrencia Scheduler

- **Objetivo:** especificar estados, relogio, claim, lease, fencing, retry, cancelamento e retencao.
- **Componentes afetados:** `tests/unit/domain/`, `tests/integration/repositories/`.
- **Dependencias:** IMP-225.
- **Criterios de conclusao:** suites inicialmente vermelhas contra fixtures incompletos cobrem dois workers, crash/restart, timezone, correlation ID original, execution ID filho e token expirado.
- **Suite minima:** `uv run pytest tests/unit/domain/test_scheduler.py tests/integration/repositories/test_scheduler_concurrency.py`.
- **Status:** Concluido.

### IMP-227 - Criar suites de contrato NotificationChannel

- **Objetivo:** especificar idempotencia, janela de 24h, classificacao e consulta externa.
- **Componentes afetados:** `tests/unit/application/`, `tests/integration/adapters/`.
- **Dependencias:** IMP-225.
- **Criterios de conclusao:** fake cobre aceite, 4xx, 5xx, 2xx malformado, timeout e status verificavel.
- **Suite minima:** `uv run pytest tests/unit/application/test_notification_channel.py`.
- **Status:** Concluido.

### IMP-228 - Criar suites de atomicidade e crash/replay

- **Objetivo:** provar atomicidade Lembrete/job e efeitos locais pos-aceite.
- **Componentes afetados:** `tests/integration/repositories/`, `tests/unit/application/`.
- **Dependencias:** IMP-226 e IMP-227.
- **Criterios de conclusao:** testes inicialmente vermelhos reproduzem rollback e replay; o verde final fica em IMP-235/IMP-245. Cobrem mesma chave dentro de 24h e estado desconhecido fora da janela sem prova.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_automacao_atomicity.py`.
- **Status:** Concluido.

### IMP-229 - Criar guardrails de seguranca e fronteiras

- **Objetivo:** bloquear cross-tenant/carteira, PII, segredo, calculo financeiro e disparo arbitrario.
- **Componentes afetados:** `tests/unit/architecture/`, `tests/integration/api/`.
- **Dependencias:** IMP-225.
- **Criterios de conclusao:** testes negativos cobrem logs, APIs, worker, adapters, broker, outbox, novos canais e acesso financeiro direto; fatos de vencimento/situacao so entram pelo contrato/read model oficial do Motor.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_automacao_guardrails.py`.
- **Status:** Concluido.

## P1 - Dominio e Persistencia

### IMP-230 - Implementar dominio Scheduler

- **Objetivo:** criar `JobAgendado`, `TentativaJob`, estados e value objects de lease/retry.
- **Componentes afetados:** `src/emprestimo/domain/`, `tests/unit/domain/`.
- **Dependencias:** IMP-226 e IMP-229.
- **Criterios de conclusao:** dominio rejeita transicoes invalidas e token expirado; job preserva correlation ID e tentativa cria execution ID filho.
- **Suite minima:** `uv run pytest tests/unit/domain/test_scheduler.py`.
- **Status:** Concluido.

### IMP-231 - Implementar dominio Notification

- **Objetivo:** criar preferencia, template, solicitacao e tentativa de notificacao.
- **Componentes afetados:** `src/emprestimo/domain/`, `tests/unit/domain/`.
- **Dependencias:** IMP-227 e IMP-229.
- **Criterios de conclusao:** estados, opt-out, imutabilidade, idempotencia e resultado desconhecido passam.
- **Suite minima:** `uv run pytest tests/unit/domain/test_notifications.py`.
- **Status:** Concluido.

### IMP-232 - Definir ports de Scheduler e Notification

- **Objetivo:** declarar Clock, repositories, `NotificationChannel` e consulta de status externo.
- **Componentes afetados:** `src/emprestimo/domain/credit/ports.py`, `src/emprestimo/application/ports.py`.
- **Dependencias:** IMP-230 e IMP-231.
- **Criterios de conclusao:** ports nao dependem de SQLAlchemy, FastAPI ou Resend e preservam tipos de resultado.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_automacao_guardrails.py`.
- **Status:** Concluido.

### IMP-233 - Criar migrations Scheduler e Notification

- **Objetivo:** adicionar jobs, tentativas, heartbeats, preferencias, templates, solicitacoes e evidencias.
- **Componentes afetados:** `migrations/versions/`, `tests/integration/migrations/`.
- **Dependencias:** IMP-228, IMP-230 e IMP-231.
- **Criterios de conclusao:** indices/constraints, Comunicacao aditiva e upgrade/downgrade/upgrade passam; Lembrete `PROGRAMADO` legado permanece manual e sem job ate opt-in explicito futuro, testado com dados preexistentes.
- **Suite minima:** `npm run quality:migrations`.
- **Status:** Concluido.

### IMP-234 - Implementar ORM e repositories

- **Objetivo:** persistir Scheduler e Notification com isolamento, claim e fencing.
- **Componentes afetados:** `src/emprestimo/infrastructure/db/`, `src/emprestimo/infrastructure/repositories/`.
- **Dependencias:** IMP-232 e IMP-233.
- **Criterios de conclusao:** round-trip, unicidade, filtros, claim concorrente e consulta de status passam.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_scheduler_concurrency.py tests/integration/repositories/test_automacao_atomicity.py`.
- **Status:** Concluido.

### IMP-235 - Integrar repositories no UnitOfWork e Agenda

- **Objetivo:** expor repositories Scheduler/Notification no UoW e atomicizar criacao/reagendamento/conclusao/cancelamento de Lembrete e job.
- **Componentes afetados:** `src/emprestimo/infrastructure/unit_of_work.py`, `src/emprestimo/application/operacao_diaria.py`.
- **Dependencias:** IMP-228 e IMP-234.
- **Criterios de conclusao:** UoW expoe jobs, tentativas, preferencias, templates e notificacoes; rollback cobre ambas as escritas e legado permanece compativel sem reconciliador como garantia primaria.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_automacao_atomicity.py`.
- **Status:** Concluido.

## P2 - Worker Scheduler

### IMP-236 - Implementar polling e claim por capacidade livre

- **Objetivo:** reivindicar em ordem deterministica com `FOR UPDATE SKIP LOCKED`.
- **Componentes afetados:** `src/emprestimo/infrastructure/scheduler/`, `tests/integration/repositories/`.
- **Dependencias:** IMP-226 e IMP-234.
- **Criterios de conclusao:** claim nao excede `min(batch_size, slots_de_execucao_livres)` nem cria backlog local leased.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_scheduler_concurrency.py`.
- **Status:** Concluido.

### IMP-237 - Implementar lease, retry, handlers e retencao

- **Objetivo:** renovar/recuperar lease, aplicar cinco tentativas e revalidar origem.
- **Componentes afetados:** `src/emprestimo/application/scheduler.py`, `src/emprestimo/infrastructure/scheduler/`.
- **Dependencias:** IMP-230, IMP-235 e IMP-236.
- **Criterios de conclusao:** token antigo nao conclui; backoff, jitter, falha permanente e purga de 90 dias passam.
- **Suite minima:** `uv run pytest tests/unit/domain/test_scheduler.py tests/integration/repositories/test_scheduler_concurrency.py`.
- **Status:** Concluido.

### IMP-238 - Criar processo worker separado

- **Objetivo:** criar entrypoint, polling, registry de handlers, configuracao e pool proprios.
- **Componentes afetados:** `src/emprestimo/worker/`, `pyproject.toml`, `tests/unit/worker/`.
- **Dependencias:** IMP-236 e IMP-237.
- **Criterios de conclusao:** worker inicia sem API, valida limites e respeita pool `concorrencia + 2`.
- **Suite minima:** `uv run pytest tests/unit/worker/test_scheduler_worker.py`.
- **Status:** Concluido.

### IMP-239 - Implementar cancelamento, runtime e shutdown

- **Objetivo:** aplicar cancelamento cooperativo, runtime maximo e drenagem graciosa.
- **Componentes afetados:** `src/emprestimo/worker/`, `tests/unit/worker/`.
- **Dependencias:** IMP-238.
- **Criterios de conclusao:** shutdown para claims, renova durante drenagem e nunca conclui trabalho incompleto.
- **Suite minima:** `uv run pytest tests/unit/worker/test_scheduler_worker.py`.
- **Status:** Concluido.

### IMP-240 - Implementar health, metricas e runbook do worker

- **Objetivo:** separar liveness/readiness internos do `/health` publico da API.
- **Componentes afetados:** `src/emprestimo/worker/`, `docs/operations/observability-runbook.md`.
- **Dependencias:** IMP-238 e IMP-239.
- **Criterios de conclusao:** heartbeat persistido a cada 10s, stale em 30s e limpeza em 24h, lag, banco, runtime e lease geram estados ADR-007 sem expor fila publicamente.
- **Suite minima:** `uv run pytest tests/unit/worker/test_scheduler_health.py`.
- **Status:** Concluido.

## P3 - Notification

### IMP-241 - Implementar preferencias, integracao com Cadastro e templates

- **Objetivo:** materializar consentimento/opt-out pelo fluxo existente de Contato, selecionar contato autorizado e gerir template versionado/aprovado.
- **Componentes afetados:** `src/emprestimo/application/notifications.py`, `src/emprestimo/application/cadastro_devedor.py`, `src/emprestimo/application/atualizacao_devedor.py`, `src/emprestimo/presentation/api/devedores_schemas.py`, `src/emprestimo/presentation/api/devedores_routes.py`, `tests/unit/application/`, `tests/integration/api/`.
- **Dependencias:** IMP-231, IMP-234 e IMP-235.
- **Criterios de conclusao:** `ContatoPayload` aceita grupo opcional e indivisivel `notificacao_estado` (`permitido|opt_out`), `notificacao_evidencia` e `notificacao_origem`; ator/instante sao derivados no servidor. O servico interno chamado por criacao/atualizacao de Contato cria ou altera PreferenciaNotificacao com evidencia, origem, estado, instante, ator, Tenant e Carteira. Ausencia preserva payload legado e nunca infere consentimento. Cadastro/atualizacao e PreferenciaNotificacao compartilham a mesma UnitOfWork do IMP-235; falha intermediaria desfaz ambos e substituicao de contatos revoga referencias removidas. Legado sem evidencia e ausencia/ambiguidade/opt-out aplicam default deny. Usa IAM do Cadastro e auditoria independente, sem rota publica de preferencia. Bootstrap administrativo auditado cria, aprova e ativa `lembrete_operacional_v1` com versao, hash e allowlist `data_hora`/`canal_atendimento`; handler nao fica ready antes disso.
- **Suite minima:** `uv run pytest tests/unit/domain/test_notifications.py tests/unit/application/test_notification_channel.py`.
- **Status:** Concluido.

### IMP-242 - Preparar solicitacao e fake deterministico

- **Objetivo:** persistir payload canonico/hash/chave antes do efeito e fornecer fake sem rede.
- **Componentes afetados:** `src/emprestimo/application/notifications.py`, `tests/fakes/`.
- **Dependencias:** IMP-227, IMP-232 e IMP-241.
- **Criterios de conclusao:** chave nao contem PII, payload divergente conflita e CI nao exige credencial.
- **Suite minima:** `uv run pytest tests/unit/application/test_notification_channel.py`.
- **Status:** Concluido.

### IMP-243 - Implementar adaptador Resend REST

- **Objetivo:** enviar e consultar status por `httpx` atras de `NotificationChannel`.
- **Componentes afetados:** `src/emprestimo/infrastructure/notifications/`, `tests/integration/adapters/`.
- **Dependencias:** IMP-232 e IMP-242.
- **Criterios de conclusao:** timeout, auth, idempotency key, mascaramento e consulta verificavel obedecem ADR-009.
- **Suite minima:** `uv run pytest tests/unit/application/test_notification_channel.py`.
- **Status:** Concluido.

### IMP-244 - Implementar orquestracao de notificacao

- **Objetivo:** coordenar handler, canal e classificacao sem transacao longa externa.
- **Componentes afetados:** `src/emprestimo/application/notifications.py`, `src/emprestimo/application/scheduler.py`.
- **Dependencias:** IMP-237, IMP-242 e IMP-243.
- **Criterios de conclusao:** 5xx/2xx malformado/incerteza ficam desconhecidos; apenas falha provada recebe retry.
- **Suite minima:** `uv run pytest tests/unit/domain/test_notifications.py tests/unit/application/test_notification_channel.py`.
- **Status:** Concluido.

### IMP-245 - Implementar efeitos pos-aceite e conciliacao

- **Objetivo:** atomicizar notificacao, Lembrete, Comunicacao e job e conciliar evidencia externa.
- **Componentes afetados:** `src/emprestimo/application/notifications.py`, `src/emprestimo/infrastructure/unit_of_work.py`.
- **Dependencias:** IMP-228, IMP-235 e IMP-244.
- **Criterios de conclusao:** dentro de 24h replay consulta/repete com a mesma chave e reaplica uma UnitOfWork; fora da janela sem prova fica desconhecido. Evidencia vincula notification_id, lembrete_id, tentativa, Tenant, Carteira, provider_message_id, status, instante e chave idempotente; divergencia retorna 409 e prova humana nao libera retry.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_automacao_atomicity.py tests/unit/domain/test_notifications.py`.
- **Status:** Concluido.

## P4 - IAM, API e Operacao

### IMP-246 - Registrar permissoes IAM de automacao

- **Objetivo:** registrar as seis permissoes iniciais de jobs, notificacoes, conciliacao e templates.
- **Componentes afetados:** `src/emprestimo/application/iam_catalogo.py`, `migrations/versions/`.
- **Dependencias:** IMP-229, IMP-240 e IMP-245.
- **Criterios de conclusao:** catalogo enumera `automacao.job.consultar`, `automacao.job.cancelar`, `automacao.job.retry`, `notificacao.consultar`, `notificacao.conciliar` e `notificacao.template.gerir`, sem permissao de disparo.
- **Suite minima:** `uv run pytest tests/unit/application/test_autorizacao.py`.
- **Status:** Concluido.

### IMP-247 - Implementar services administrativos

- **Objetivo:** consultar/cancelar/repetir jobs e consultar/conciliar notificacoes com auditoria.
- **Componentes afetados:** `src/emprestimo/application/automacao.py`, `tests/unit/application/`.
- **Dependencias:** IMP-240, IMP-245 e IMP-246.
- **Criterios de conclusao:** retry administrativo aceita apenas falha temporaria esgotada, com motivo, autoria, nova tentativa e mesma chave do provedor; permanente exige correcao e nova solicitacao, desconhecido exige conciliacao. Mutacoes geram auditoria append-only em sessao independente ADR-002 e sobrevivem a rollback; escopo divergente fica oculto.
- **Suite minima:** `uv run pytest tests/integration/api/test_automacao_api.py tests/unit/domain/test_scheduler.py`.
- **Status:** Concluido.

### IMP-248 - Criar schemas e dependencies da API

- **Objetivo:** definir DTOs, RBAC, tenancy, idempotencia, paginacao e mascaramento para jobs, notificacoes e templates.
- **Componentes afetados:** `src/emprestimo/presentation/api/`, `tests/integration/api/`.
- **Dependencias:** IMP-246 e IMP-247.
- **Criterios de conclusao:** schemas reproduzem por operacao a Matriz HTTP do PLAN e incluem `X-Correlation-ID`.
- **Suite minima:** `uv run pytest tests/integration/api/test_automacao_api.py`.
- **Status:** Concluido.

### IMP-249 - Expor endpoints administrativos de jobs

- **Objetivo:** publicar consulta, cancelamento e retry governado.
- **Componentes afetados:** `src/emprestimo/presentation/api/`, `tests/integration/api/`.
- **Dependencias:** IMP-248.
- **Criterios de conclusao:** `GET /credit/automacao/jobs`, `GET /credit/automacao/jobs/{job_id}`, `POST /credit/automacao/jobs/{job_id}/cancelar` e `POST /credit/automacao/jobs/{job_id}/retry` respeitam IAM e escopo.
- **Suite minima:** `uv run pytest tests/integration/api/test_automacao_api.py`.
- **Status:** Concluido.

### IMP-250 - Expor endpoints de Notification e compatibilidade

- **Objetivo:** publicar consultas, templates e conciliacao sem envio arbitrario; gestao publica de preferencias fica fora deste ciclo.
- **Componentes afetados:** `src/emprestimo/presentation/api/`, `tests/integration/api/`.
- **Dependencias:** IMP-241, IMP-245 e IMP-248.
- **Criterios de conclusao:** `GET /credit/notificacoes`, `GET /credit/notificacoes/{notification_id}`, `POST /credit/notificacoes/{notification_id}/conciliar`, `GET /credit/notificacoes/templates`, `POST /credit/notificacoes/templates`, `POST /credit/notificacoes/templates/{template_id}/aprovar`, `POST /credit/notificacoes/templates/{template_id}/ativar` e `POST /credit/agenda/lembretes/{lembrete_id}/enviar` cumprem ADR-009; template precisa estar aprovado antes da ativacao, autoria/aprovacao/motivo ficam auditados e a rota legada nao chama provedor.
- **Suite minima:** `uv run pytest tests/integration/api/test_automacao_api.py tests/integration/api/test_operacao_diaria_api.py`.
- **Status:** Concluido.

### IMP-251 - Atualizar OpenAPI e operacao

- **Objetivo:** documentar security, erros, idempotencia, deprecacao, worker e runbook.
- **Componentes afetados:** `src/emprestimo/presentation/api/openapi.py`, `docs/operations/`.
- **Dependencias:** IMP-249 e IMP-250.
- **Criterios de conclusao:** todas as rotas reproduzem a Matriz HTTP do PLAN; nao ha health publico do worker nem disparo arbitrario.
- **Suite minima:** `uv run pytest tests/integration/api/test_automacao_api.py`.
- **Status:** Concluido.

## P5 - Recertificacao

### IMP-252 - Recertificar guardrails e cenarios adversariais

- **Objetivo:** atacar concorrencia, crash/replay, IAM, escopo, PII, canal e fronteira financeira.
- **Componentes afetados:** `tests/`, `scripts/tests/`.
- **Dependencias:** IMP-251.
- **Criterios de conclusao:** mutacoes e testes reais falham diante de lease frouxo, retry incerto ou efeito duplicado.
- **Suite minima:** `uv run pytest tests/unit/architecture/test_automacao_guardrails.py tests/integration/repositories/test_scheduler_concurrency.py`.
- **Status:** Concluido.

### IMP-253 - Recertificar EPIC-010 com suite completa

- **Objetivo:** validar Product, ADRs, PLAN, codigo, migrations, API, worker e operacao.
- **Componentes afetados:** `docs/implementation/reports/`, `docs/implementation/backlogs/PLAN-018-execution-backlog.md`.
- **Dependencias:** IMP-252.
- **Criterios de conclusao:** todos os gates e revisao adversarial final passam sem achado bloqueante.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido.

---

# 3. Gates de Execucao

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- `node scripts/tests/test-epic-010-contracts.js`;
- `npm run quality:migrations`;
- revisao adversarial final sem achados bloqueantes.

---

# 4. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-11 | Backlog inicial do PLAN-018 com IMP-225..IMP-253 em blocos P0 a P5. |
| 1.1.0 | 2026-08-11 | IMP-225..IMP-253 concluidos e recertificados com os gates oficiais. |
