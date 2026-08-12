#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');

const FILES = {
  discovery: 'docs/audits/discoveries/EPIC-010-automacao-operacional-scheduler-notificacoes-discovery.md',
  product006: 'docs/product/credit/capabilities/PRODUCT-006-administrar-agenda.md',
  product007: 'docs/product/credit/capabilities/PRODUCT-007-administrar-comunicacao.md',
  epic: 'docs/product/credit/epics/EPIC-010-automacao-operacional-scheduler-notificacoes.md',
  feature042: 'docs/product/credit/features/FEATURE-042-automatizar-lembretes-operacionais.md',
  feature043: 'docs/product/credit/features/FEATURE-043-processar-jobs-duraveis.md',
  feature044: 'docs/product/credit/features/FEATURE-044-enviar-notificacoes-transacionais.md',
  feature045: 'docs/product/credit/features/FEATURE-045-operar-reconciliar-automacao.md',
  us113: 'docs/product/credit/user-stories/US-113-agendar-lembrete-automatico.md',
  us114: 'docs/product/credit/user-stories/US-114-cancelar-trabalho-lembrete-inelegivel.md',
  us115: 'docs/product/credit/user-stories/US-115-reivindicar-executar-job-lease.md',
  us116: 'docs/product/credit/user-stories/US-116-recuperar-job-aplicar-retry-governado.md',
  us117: 'docs/product/credit/user-stories/US-117-observar-saude-atraso-worker.md',
  us118: 'docs/product/credit/user-stories/US-118-selecionar-contato-autorizado-notificacao.md',
  us119: 'docs/product/credit/user-stories/US-119-renderizar-template-transacional-versionado.md',
  us120: 'docs/product/credit/user-stories/US-120-enviar-notificacao-forma-idempotente.md',
  us121: 'docs/product/credit/user-stories/US-121-registrar-comunicacao-apos-aceite-provedor.md',
  us122: 'docs/product/credit/user-stories/US-122-administrar-job-notificacao-rbac.md',
  us123: 'docs/product/credit/user-stories/US-123-conciliar-resultado-externo-desconhecido.md',
  us124: 'docs/product/credit/user-stories/US-124-proteger-automacao-vazamento-calculo.md',
  adr007: 'docs/architecture/adrs/ADR-007-scheduler-batch-processing.md',
  adr009: 'docs/architecture/adrs/ADR-009-notifications-channels.md',
  amp: 'docs/architecture/amp/AMP-001-architecture-master-plan.md',
  runbook: 'docs/operations/observability-runbook.md',
  plan: 'docs/implementation/plans/PLAN-018-epic-010-automacao-operacional-scheduler-notificacoes.md',
  backlog: 'docs/implementation/backlogs/PLAN-018-execution-backlog.md',
  registry: 'docs/governance/registry/identifier-registry.json',
};

const docs = Object.fromEntries(Object.entries(FILES).map(([key, rel]) => [key, read(rel)]));
const normalizar = (texto) => texto.replace(/\s+/g, ' ').trim();

function assertTexto(doc, texto, contexto) {
  assert.ok(normalizar(doc).includes(normalizar(texto)), `${contexto}: contrato ausente: ${texto}`);
}

function mutar(base, origem, destino) {
  assert.ok(base.discovery.includes(origem), `fixture de mutacao ausente: ${origem}`);
  return { ...base, discovery: base.discovery.replace(origem, destino) };
}

const contracts = {
  readiness(source) {
    assertTexto(
      source.discovery,
      '**Status:** Discovery e Product concluidos; ADRs aceitas; pronto para PLAN',
      'status',
    );
    assertTexto(
      source.discovery,
      'As decisoes de Product estao fechadas',
      'criterio de pronto',
    );
    assertTexto(
      source.discovery,
      'As decisoes de Product estao fechadas',
      'fechamento da fase Product',
    );
    assertTexto(
      source.discovery,
      'As escolhas tecnicas foram encerradas pelas ADR-007 e ADR-009',
      'fechamento das escolhas arquiteturais',
    );
    assertTexto(source.discovery, 'canal | Product | fechado: e-mail transacional', 'canal fechado');
    assertTexto(source.discovery, 'provedor e ambiente de teste | Arquitetura | fechado: ADR-009 aceita', 'owner provedor');
    assertTexto(source.discovery, 'lag, tentativas, backoff e retencao | Arquitetura + Operacoes | fechado: ADR-007 aceita', 'owner scheduler');
    assertTexto(source.discovery, 'semantica da acao HTTP `enviar` | Product + API | fechado', 'owner API');
    assertTexto(
      source.discovery,
      'o recorte conjunto Scheduler + Notification esta decidido na secao 5',
      'evidencia presente de prontidao',
    );
  },

  atomicity(source) {
    assertTexto(
      source.discovery,
      'mesma transacao PostgreSQL e na mesma UnitOfWork',
      'atomicidade Lembrete/job',
    );
    assertTexto(source.discovery, 'Falha em qualquer escrita desfaz ambas', 'rollback atomico');
    assertTexto(
      source.discovery,
      'cancela o job pendente na mesma transacao e UnitOfWork da mudanca do Lembrete',
      'cancelamento atomico',
    );
    assertTexto(
      source.discovery,
      'reconciliador periodico pode detectar legado ou corrupcao operacional, mas nao substitui essa garantia atomica',
      'reconciliador nao substitui transacao',
    );
  },

  unknownOutcome(source) {
    assertTexto(source.discovery, '`resultado_desconhecido` ou `cancelada`', 'estado desconhecido');
    assertTexto(
      source.discovery,
      'chave idempotente aceita pelo provedor ou consulta de status pela identidade da requisicao',
      'protecao no provedor',
    );
    assertTexto(
      source.discovery,
      'bloqueada para reenvio automatico e exige conciliacao administrativa',
      'bloqueio de reenvio desconhecido',
    );
    assertTexto(
      source.discovery,
      'Ausencia de confirmacao local, sozinha, nunca autoriza novo disparo',
      'janela de crash',
    );
  },

  permanentFailure(source) {
    assertTexto(
      source.discovery,
      'falha permanente e **nao podem repetir a mesma solicitacao**',
      'falha permanente terminal',
    );
    assertTexto(
      source.discovery,
      'criar nova solicitacao versionada, com nova chave idempotente e vinculo auditavel a original',
      'correcao antes de nova solicitacao',
    );
    assertTexto(
      source.discovery,
      'Falha permanente exige contato, consentimento ou template corrigido',
      'retry administrativo permanente',
    );
  },

  healthSeparation(source) {
    assertTexto(source.discovery, 'DA-1016 - Health da API e do worker sao contratos separados', 'DA-1016');
    assertTexto(
      source.discovery,
      'Atraso do Scheduler nao torna a API indisponivel nem altera sozinho seu HTTP para `503`',
      'health publico da API',
    );
    assertTexto(
      source.discovery,
      'worker possui liveness e readiness proprios, expostos apenas por mecanismo interno ou protegido',
      'health interno do worker',
    );
    assertTexto(
      source.discovery,
      'Metricas detalhadas de fila permanecem protegidas e nao entram no payload publico de `/health`',
      'fila protegida',
    );
  },

  registry(source) {
    const registry = JSON.parse(source.registry);
    assert.ok(registry.namespaces.EPIC.ultimo >= 10, 'Registry EPIC deve incluir EPIC-010');
    assert.ok(registry.namespaces.FEATURE.ultimo >= 45, 'Registry FEATURE deve incluir FEATURE-045');
    assert.ok(registry.namespaces.US.ultimo >= 124, 'Registry US deve incluir US-124');
    assert.ok(registry.namespaces.PLAN.ultimo >= 18, 'Registry PLAN deve incluir PLAN-018');
  },

  productHierarchy(source) {
    assertTexto(source.product006, 'EPIC-010 - Automacao Operacional', 'PRODUCT-006');
    assertTexto(source.product007, 'EPIC-010 - Automacao Operacional', 'PRODUCT-007');
    assertTexto(source.epic, 'Nao cria uma Capability nova', 'decisao de Capability');

    const features = {
      feature042: ['FEATURE-042', 'US-113', 'US-114'],
      feature043: ['FEATURE-043', 'US-115', 'US-116', 'US-117'],
      feature044: ['FEATURE-044', 'US-118', 'US-119', 'US-120', 'US-121'],
      feature045: ['FEATURE-045', 'US-122', 'US-123', 'US-124'],
    };
    for (const [key, ids] of Object.entries(features)) {
      for (const id of ids) assertTexto(source[key], id, key);
      assertTexto(source.epic, ids[0], 'EPIC-010');
    }

    const storyFeatures = {
      us113: 'FEATURE-042', us114: 'FEATURE-042',
      us115: 'FEATURE-043', us116: 'FEATURE-043', us117: 'FEATURE-043',
      us118: 'FEATURE-044', us119: 'FEATURE-044', us120: 'FEATURE-044', us121: 'FEATURE-044',
      us122: 'FEATURE-045', us123: 'FEATURE-045', us124: 'FEATURE-045',
    };
    for (const [story, feature] of Object.entries(storyFeatures)) {
      assertTexto(source[story], feature, story);
    }
  },

  productDecisions(source) {
    assertTexto(source.epic, 'nenhuma nova Capability sera emitida', 'Capability reutilizada');
    assertTexto(source.epic, 'e-mail transacional e o unico canal', 'canal inicial');
    assertTexto(source.epic, '`lembrete_operacional_v1`', 'template inicial');
    assertTexto(source.epic, 'restrito a conciliacao administrativa auditada', 'acao enviar');
    assertTexto(source.epic, 'ADR-009 fecha o provedor Resend', 'gate ADR-009');
    assertTexto(source.epic, 'ADR-007 fecha lag, tentativas, backoff e retencao', 'gate ADR-007');
    assertTexto(source.us118, 'opt-out vigente bloqueia', 'opt-out');
    assertTexto(source.us120, 'resultado desconhecido bloqueia reenvio automatico', 'resultado desconhecido');
    assertTexto(source.us124, 'nao calculam juros, mora, multa', 'guardrail anti-calculo');
  },

  schedulerArchitecture(source) {
    assertTexto(source.adr007, '> **Status:** Aceito', 'ADR-007 aceita');
    assertTexto(source.adr007, 'mesma transacao PostgreSQL e na mesma UnitOfWork', 'atomicidade ADR-007');
    assertTexto(source.adr007, '`FOR UPDATE SKIP LOCKED`', 'claim concorrente');
    assertTexto(source.adr007, '`clock_timestamp()` do PostgreSQL e o relogio autoritativo', 'relogio autoritativo');
    assertTexto(source.adr007, '`SCHEDULER_BATCH_SIZE` | 4 | 1 a 16', 'limite de batch');
    assertTexto(source.adr007, '`SCHEDULER_CONCURRENCY` | 4 | 1 a 16', 'limite de concorrencia');
    assertTexto(source.adr007, 'min(batch_size, slots_de_execucao_livres)', 'claim limitado a capacidade');
    assertTexto(source.adr007, '`SCHEDULER_MAX_ATTEMPT_RUNTIME_SECONDS` | 300', 'duracao maxima');
    assertTexto(source.adr007, 'criados, reagendados, concluidos ou cancelados', 'conclusao atomica');
    assertTexto(source.adr007, 'no maximo cinco tentativas totais', 'limite de tentativas');
    assertTexto(source.adr007, '30 segundos, 2 minutos, 10 minutos e 30 minutos', 'backoff');
    assertTexto(source.adr007, 'Jobs terminais e tentativas ficam por 90 dias', 'retencao');
    assertTexto(source.adr007, 'Atraso do worker nao altera sozinho o HTTP de `/health`', 'health separado');
    assertTexto(source.adr007, 'Nenhum endpoint permite criar ou disparar job arbitrario', 'sem disparo arbitrario');
  },

  notificationArchitecture(source) {
    assertTexto(source.adr009, '> **Status:** Aceito', 'ADR-009 aceita');
    assertTexto(source.adr009, 'API HTTPS do Resend', 'provedor concreto');
    assertTexto(source.adr009, 'projeto e API key de teste separados da producao', 'ambiente verificavel');
    assertTexto(source.adr009, 'CI e testes locais usam um fake deterministico', 'CI sem rede');
    assertTexto(source.adr009, 'NotificationChannel', 'porta de canal');
    assertTexto(source.adr009, 'resultado_desconhecido', 'resultado desconhecido');
    assertTexto(source.adr009, 'nenhum reenvio automatico e permitido', 'bloqueio de reenvio');
    assertTexto(source.adr009, '5xx, 2xx malformado', 'fallback desconhecido');
    assertTexto(source.adr009, 'uma unica UnitOfWork marca a notificacao como aceita', 'efeitos locais atomicos');
    assertTexto(source.adr009, 'mesmo `lembrete_id`, tentativa, Tenant e Carteira', 'vinculo da conciliacao');
    assertTexto(source.adr009, '`provider_message_id` e status consultados pelo adaptador', 'evidencia verificavel');
    assertTexto(source.adr009, 'Declaracao humana, texto livre, print ou identificador nao verificavel', 'sem prova humana');
    assertTexto(source.adr009, 'jamais libera reenvio', 'evidencia fraca nao libera retry');
    assertTexto(source.adr009, '`lembrete_operacional_v1`', 'template inicial');
    assertTexto(source.adr009, '`data_hora` e `canal_atendimento`', 'parametros permitidos');
    assertTexto(source.adr009, 'Aceite significa apenas que o provedor aceitou a requisicao', 'sem promessa de entrega');
    assertTexto(source.adr009, 'alias depreciado de conciliacao e jamais chama o provedor', 'endpoint legado');
    assertTexto(source.adr009, 'Nao existe endpoint de disparo arbitrario', 'sem envio arbitrario');
  },

  governanceAndOperations(source) {
    assertTexto(source.amp, '**Alteração na v1.3.0:** ADR-007', 'AMP atualizado');
    assertTexto(source.amp, '**Status:** Aprovado como plano diretor', 'AMP aprovado');
    assertTexto(source.amp, '**EMITIDA em 11/08/2026** — ver [ADR-007]', 'reserva ADR-007 emitida');
    assertTexto(source.amp, '**EMITIDA em 11/08/2026** — ver [ADR-009]', 'reserva ADR-009 emitida');
    assertTexto(source.runbook, 'O health da API e do worker sao contratos separados', 'runbook health');
    assertTexto(source.runbook, 'resultado_desconhecido', 'runbook conciliacao');
    assertTexto(source.runbook, '5xx, 2xx malformado', 'runbook sem retry de 5xx');
    const registry = JSON.parse(source.registry);
    assert.ok(!Object.hasOwn(registry.namespaces.ADR, 'ultimo'), 'Registry nao deve calcular IDs de ADR');
  },

  planAndBacklog(source) {
    assertTexto(source.plan, '**ID:** PLAN-018', 'PLAN-018');
    assertTexto(source.plan, '**Status:** Planejado', 'status PLAN-018');
    assertTexto(source.backlog, '**ID:** PLAN-018-EXEC', 'PLAN-018-EXEC');
    assert.match(
      source.backlog,
      /\*\*Status:\*\* (?:Planejado|Concluido)/,
      'status backlog deve representar planejamento ou fechamento',
    );

    for (const bloco of ['P0', 'P1', 'P2', 'P3', 'P4', 'P5']) {
      assert.ok(new RegExp(`^## ${bloco} -`, 'm').test(source.backlog), `bloco ${bloco} ausente`);
    }

    const ids = [...source.backlog.matchAll(/^### (IMP-\d{3}) -/gm)].map((match) => match[1]);
    const expected = Array.from({ length: 29 }, (_, index) => `IMP-${225 + index}`);
    assert.deepStrictEqual(ids, expected, 'Backlog deve conter IMP-225..IMP-253 uma unica vez e em ordem');

    const headings = [...source.backlog.matchAll(/^### (IMP-(\d{3})) -/gm)];
    const impBlocks = new Map();
    const required = ['Objetivo', 'Componentes afetados', 'Dependencias', 'Criterios de conclusao', 'Suite minima', 'Status'];
    for (let index = 0; index < headings.length; index += 1) {
      const current = headings[index];
      const end = index + 1 < headings.length ? headings[index + 1].index : source.backlog.indexOf('\n---', current.index);
      const block = source.backlog.slice(current.index, end === -1 ? undefined : end);
      impBlocks.set(current[1], block);
      for (const field of required) assertTexto(block, `**${field}:**`, `${current[1]} campo`);
      assert.match(
        block,
        /\*\*Status:\*\* (?:Planejado|Concluido)\./,
        `${current[1]} status invalido`,
      );
      const currentNumber = Number(current[2]);
      const dependencyLine = block.match(/^- \*\*Dependencias:\*\* (.+)$/m)?.[1] ?? '';
      for (const ref of dependencyLine.matchAll(/IMP-(\d{3})/g)) {
        assert.ok(expected.includes(ref[0]), `${current[1]} depende de item externo ${ref[0]}`);
        assert.ok(Number(ref[1]) < currentNumber, `${current[1]} depende de item futuro ${ref[0]}`);
      }
    }

    for (const feature of ['FEATURE-042', 'FEATURE-043', 'FEATURE-044', 'FEATURE-045']) {
      assertTexto(source.plan, feature, 'rastreabilidade Feature');
    }
    for (let number = 113; number <= 124; number += 1) {
      assertTexto(source.plan, `US-${number}`, 'rastreabilidade User Story');
    }

    for (const gate of [
      'uv run pytest -q', 'uv run ruff check .', 'uv run black --check .',
      'uv run mypy src tests', 'npm run docs:validate', 'npm run docs:test',
      'node scripts/tests/test-epic-010-contracts.js', 'npm run quality:migrations',
    ]) {
      assertTexto(source.plan, gate, 'gate PLAN-018');
      assertTexto(source.backlog, gate, 'gate PLAN-018-EXEC');
    }

    assertTexto(source.plan, 'min(batch_size, slots_de_execucao_livres)', 'claim limitado');
    assertTexto(source.plan, 'Token expirado ou substituido nao conclui', 'fencing token');
    assertTexto(source.plan, '`resultado_desconhecido`. Somente evidencia consultada no provedor', 'incerteza externa');
    assertTexto(source.plan, 'uma unica UnitOfWork idempotente', 'atomicidade pos-aceite');
    assertTexto(source.plan, 'Nao existe endpoint de envio arbitrario', 'sem disparo arbitrario');
    assertTexto(source.plan, 'nao calculam nem reinterpretam juros', 'guardrail financeiro');

    const routes = [
      'GET /credit/automacao/jobs',
      'GET /credit/automacao/jobs/{job_id}',
      'POST /credit/automacao/jobs/{job_id}/cancelar',
      'POST /credit/automacao/jobs/{job_id}/retry',
      'GET /credit/notificacoes',
      'GET /credit/notificacoes/{notification_id}',
      'POST /credit/notificacoes/{notification_id}/conciliar',
      'GET /credit/notificacoes/templates',
      'POST /credit/notificacoes/templates',
      'POST /credit/notificacoes/templates/{template_id}/aprovar',
      'POST /credit/notificacoes/templates/{template_id}/ativar',
      'POST /credit/agenda/lembretes/{lembrete_id}/enviar',
    ];
    const routePattern = /\b(?:GET|POST|PUT|PATCH|DELETE) \/[A-Za-z0-9_{}./-]+/g;
    const routeSet = (text) => [...new Set(text.match(routePattern) ?? [])].sort();
    const expectedRoutes = [...routes].sort();
    assert.deepStrictEqual(routeSet(source.plan), expectedRoutes, 'PLAN deve conter somente a allowlist de rotas');
    assert.deepStrictEqual(routeSet(source.backlog), expectedRoutes, 'Backlog deve conter somente a allowlist de rotas');

    const httpRows = [
      '`GET /credit/automacao/jobs` | 200 | 400, 401, 403',
      '`GET /credit/automacao/jobs/{job_id}` | 200 | 401, 403, 404',
      '`POST /credit/automacao/jobs/{job_id}/cancelar` | 202 | 400, 401, 403, 404, 409',
      '`POST /credit/automacao/jobs/{job_id}/retry` | 202 | 400, 401, 403, 404, 409',
      '`GET /credit/notificacoes` | 200 | 400, 401, 403',
      '`GET /credit/notificacoes/{notification_id}` | 200 | 401, 403, 404',
      '`POST /credit/notificacoes/{notification_id}/conciliar` | 200 | 400, 401, 403, 404, 409',
      '`GET /credit/notificacoes/templates` | 200 | 400, 401, 403',
      '`POST /credit/notificacoes/templates` | 201 | 400, 401, 403, 409',
      '`POST /credit/notificacoes/templates/{template_id}/aprovar` | 200 | 400, 401, 403, 404, 409',
      '`POST /credit/notificacoes/templates/{template_id}/ativar` | 200 | 400, 401, 403, 404, 409',
      '`POST /credit/agenda/lembretes/{lembrete_id}/enviar` | 200 | 400, 401, 403, 404, 409',
    ];
    for (const row of httpRows) assertTexto(source.plan, row, 'Matriz HTTP');

    assertTexto(source.plan, 'Lembretes `PROGRAMADO` legados permanecem manuais', 'cutover legado');
    assertTexto(source.backlog, 'Lembrete `PROGRAMADO` legado permanece manual e sem job', 'migration legado');
    assertTexto(source.plan, 'auditoria append-only em sessao independente conforme ADR-002', 'auditoria independente');
    assertTexto(source.backlog, 'sobrevivem a rollback', 'auditoria apos rollback');
    assertTexto(source.plan, 'execution ID filho', 'execution ID');
    assertTexto(source.plan, 'scheduler_worker_heartbeats`, persistido', 'heartbeat persistido');
    assertTexto(source.backlog, 'heartbeat persistido a cada 10s', 'health operacional');
    assertTexto(source.backlog, '`notificacao.template.gerir`', 'permissao template');
    for (const permission of [
      '`automacao.job.consultar`', '`automacao.job.cancelar`', '`automacao.job.retry`',
      '`notificacao.consultar`', '`notificacao.conciliar`', '`notificacao.template.gerir`',
    ]) assertTexto(impBlocks.get('IMP-246'), permission, 'catalogo IAM');
    assertTexto(source.backlog, 'template precisa estar aprovado antes da ativacao', 'aprovacao template');
    assertTexto(source.backlog, 'PreferenciaNotificacao com evidencia, origem, estado, instante, ator, Tenant e Carteira', 'evidencia consentimento');
    assertTexto(source.plan, 'servico interno chamado pelos fluxos existentes de criacao/atualizacao de Contato', 'produtor consentimento');
    assertTexto(source.backlog, 'servico interno chamado por criacao/atualizacao de Contato cria ou altera PreferenciaNotificacao', 'execucao consentimento');
    assertTexto(source.backlog, 'sem rota publica de preferencia', 'preferencia sem API nova');
    assertTexto(source.plan, '`notificacao_estado` (`permitido|opt_out`)', 'campos consentimento');
    assertTexto(source.plan, 'Ausencia do grupo preserva compatibilidade, nao infere consentimento', 'compatibilidade consentimento');
    assertTexto(source.plan, 'Contato e preferencia sao gravados na mesma UnitOfWork', 'atomicidade consentimento');
    assertTexto(source.backlog, 'cadastro_devedor.py', 'modulo real cadastro');
    assertTexto(source.backlog, 'atualizacao_devedor.py', 'modulo real atualizacao');
    assertTexto(source.backlog, 'devedores_schemas.py', 'schema real cadastro');
    assertTexto(source.backlog, 'falha intermediaria desfaz ambos', 'rollback consentimento');
    assertTexto(source.backlog, 'Bootstrap administrativo auditado cria, aprova e ativa', 'bootstrap template');
    assertTexto(source.backlog, 'retry administrativo aceita apenas falha temporaria esgotada', 'matriz retry');
    assertTexto(source.backlog, 'provider_message_id, status, instante e chave idempotente', 'vinculo evidencia');
    assertTexto(source.plan, 'contrato/read model oficial do Motor', 'origem financeira oficial');
    assertTexto(impBlocks.get('IMP-226'), 'suites inicialmente vermelhas', 'P0 Scheduler red');
    assertTexto(impBlocks.get('IMP-228'), 'testes inicialmente vermelhos', 'P0 atomicidade red');
    assertTexto(impBlocks.get('IMP-233'), 'Criar migrations Scheduler e Notification', 'IMP-233 migration');
    assertTexto(impBlocks.get('IMP-233'), 'adicionar jobs, tentativas, heartbeats, preferencias, templates, solicitacoes e evidencias', 'schema IMP-233');
  },
};

const cases = [];
const test = (name, fn) => cases.push({ name, fn });

test('discovery possui status e ownership de decisoes coerentes', () => contracts.readiness(docs));
test('Lembrete e job compartilham transacao e UnitOfWork', () => contracts.atomicity(docs));
test('resultado desconhecido bloqueia reenvio sem prova externa', () => contracts.unknownOutcome(docs));
test('falha permanente exige solicitacao corrigida e versionada', () => contracts.permanentFailure(docs));
test('health da API permanece separado do health do worker', () => contracts.healthSeparation(docs));
test('Product possui rastreabilidade EPIC, Features e User Stories', () => contracts.productHierarchy(docs));
test('decisoes da fase Product estao fechadas e ADRs possuem gate', () => contracts.productDecisions(docs));
test('ADR-007 fecha Scheduler duravel e seus limites operacionais', () => contracts.schedulerArchitecture(docs));
test('ADR-009 fecha canal, provedor, idempotencia e conciliacao', () => contracts.notificationArchitecture(docs));
test('AMP, registry e runbook refletem as ADRs emitidas', () => contracts.governanceAndOperations(docs));
test('PLAN-018 e backlog possuem IMP-225..IMP-253 rastreaveis e executaveis', () => contracts.planAndBacklog(docs));
test('registry inclui o identificador EPIC-010', () => contracts.registry(docs));

test('mutacao: criterio de pronto condicional e rejeitado', () => {
  const altered = {
    ...docs,
    discovery: docs.discovery.replace(
      'As escolhas tecnicas foram encerradas\npelas ADR-007 e ADR-009',
      'As escolhas tecnicas ainda precisam ser encerradas',
    ),
  };
  assert.throws(() => contracts.readiness(altered));
});

test('mutacao: remover atomicidade Lembrete/job e rejeitado', () => {
  const altered = mutar(
    docs,
    'mesma transacao PostgreSQL e na mesma\nUnitOfWork',
    'transacoes independentes',
  );
  assert.throws(() => contracts.atomicity(altered));
});

test('mutacao: liberar reenvio de resultado desconhecido e rejeitado', () => {
  const altered = mutar(
    docs,
    'bloqueada para reenvio automatico e exige conciliacao administrativa',
    'liberada para reenvio automatico',
  );
  assert.throws(() => contracts.unknownOutcome(altered));
});

test('mutacao: repetir falha permanente sem correcao e rejeitado', () => {
  const altered = mutar(
    docs,
    'falha permanente e **nao podem repetir a mesma solicitacao**',
    'falha permanente e podem repetir a mesma solicitacao',
  );
  assert.throws(() => contracts.permanentFailure(altered));
});

test('mutacao: atraso do worker derrubar health da API e rejeitado', () => {
  const altered = mutar(
    docs,
    'Atraso do\nScheduler nao torna a API indisponivel nem altera sozinho seu HTTP para `503`',
    'Atraso do Scheduler torna a API indisponivel e altera seu HTTP para `503`',
  );
  assert.throws(() => contracts.healthSeparation(altered));
});

test('mutacao: criar Capability artificial e rejeitado', () => {
  const altered = {
    ...docs,
    epic: docs.epic.replace('nenhuma nova Capability sera emitida', 'uma nova Capability sera emitida'),
  };
  assert.throws(() => contracts.productDecisions(altered));
});

test('mutacao: liberar canal adicional no primeiro incremento e rejeitado', () => {
  const altered = { ...docs, epic: docs.epic.replace('e-mail transacional e o unico canal', 'e-mail e SMS sao canais') };
  assert.throws(() => contracts.productDecisions(altered));
});

test('mutacao: remover conciliacao da acao enviar e rejeitado', () => {
  const altered = {
    ...docs,
    epic: docs.epic.replace('restrito a conciliacao administrativa auditada', 'usado para envio manual'),
  };
  assert.throws(() => contracts.productDecisions(altered));
});

test('mutacao: remover claim concorrente do Scheduler e rejeitado', () => {
  const altered = { ...docs, adr007: docs.adr007.replace('`FOR UPDATE SKIP LOCKED`', '`SELECT` simples') };
  assert.throws(() => contracts.schedulerArchitecture(altered));
});

test('mutacao: liberar retry de resultado desconhecido e rejeitado', () => {
  const altered = {
    ...docs,
    adr009: docs.adr009.replace('nenhum\nreenvio automatico e permitido', 'reenvio automatico e permitido'),
  };
  assert.throws(() => contracts.notificationArchitecture(altered));
});

test('mutacao: adicionar contador ADR ao registry e rejeitado', () => {
  const registry = JSON.parse(docs.registry);
  registry.namespaces.ADR.ultimo = 18;
  const altered = { ...docs, registry: JSON.stringify(registry) };
  assert.throws(() => contracts.governanceAndOperations(altered));
});

test('mutacao: reivindicar acima da capacidade livre e rejeitado', () => {
  const altered = {
    ...docs,
    adr007: docs.adr007.replace(
      'min(batch_size, slots_de_execucao_livres)',
      'batch_size independentemente dos slots livres',
    ),
  };
  assert.throws(() => contracts.schedulerArchitecture(altered));
});

test('mutacao: tratar todo 5xx como retentavel e rejeitado', () => {
  const altered = { ...docs, adr009: docs.adr009.replace('5xx, 2xx malformado', '2xx malformado') };
  assert.throws(() => contracts.notificationArchitecture(altered));
});

test('mutacao: remover atomicidade pos-aceite e rejeitado', () => {
  const altered = {
    ...docs,
    adr009: docs.adr009.replace('uma\nunica UnitOfWork marca a notificacao como aceita', 'operacoes independentes marcam a notificacao como aceita'),
  };
  assert.throws(() => contracts.notificationArchitecture(altered));
});

test('mutacao: permitir declaracao humana como prova externa e rejeitado', () => {
  const altered = { ...docs, adr009: docs.adr009.replace('jamais libera\nreenvio', 'libera reenvio') };
  assert.throws(() => contracts.notificationArchitecture(altered));
});

test('mutacao: runbook omitir 5xx desconhecido e rejeitado', () => {
  const altered = { ...docs, runbook: docs.runbook.replace('5xx, 2xx malformado', '2xx malformado') };
  assert.throws(() => contracts.governanceAndOperations(altered));
});

test('mutacao: reduzir PLAN ultimo no registry e rejeitado', () => {
  const registry = JSON.parse(docs.registry);
  registry.namespaces.PLAN.ultimo = 17;
  const altered = { ...docs, registry: JSON.stringify(registry) };
  assert.throws(() => contracts.registry(altered));
});

test('mutacao: remover IMP do backlog e rejeitado', () => {
  const start = docs.backlog.indexOf('### IMP-240 -');
  const end = docs.backlog.indexOf('### IMP-241 -');
  assert.ok(start >= 0 && end > start, 'fixture IMP-240 ausente');
  const altered = { ...docs, backlog: docs.backlog.slice(0, start) + docs.backlog.slice(end) };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: dependencia futura no backlog e rejeitada', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replace('**Dependencias:** IMP-225.', '**Dependencias:** IMP-253.'),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: campo obrigatorio de IMP removido e rejeitado', () => {
  const altered = { ...docs, backlog: docs.backlog.replace('**Suite minima:**', '**Verificacao:**') };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: dependencia externa ao PLAN-018 e rejeitada', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replace('**Dependencias:** IMP-225.', '**Dependencias:** IMP-001.'),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: rota de aprovacao de template removida e rejeitada', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replaceAll('POST /credit/notificacoes/templates/{template_id}/aprovar', 'POST /credit/notificacoes/templates/{template_id}/ativar'),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: matriz HTTP de cancelamento enfraquecida e rejeitada', () => {
  const altered = {
    ...docs,
    plan: docs.plan.replace(
      '`POST /credit/automacao/jobs/{job_id}/cancelar` | 202 | 400, 401, 403, 404, 409',
      '`POST /credit/automacao/jobs/{job_id}/cancelar` | 200 | 400, 401',
    ),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: cutover manual de Lembretes legados removido e rejeitado', () => {
  const altered = { ...docs, plan: docs.plan.replace('Lembretes `PROGRAMADO` legados permanecem manuais', 'Lembretes legados recebem envio automatico') };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: auditoria independente removida e rejeitada', () => {
  const altered = { ...docs, plan: docs.plan.replace('auditoria append-only em sessao independente conforme ADR-002', 'auditoria na transacao principal') };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: permissao obrigatoria removida e rejeitada', () => {
  const altered = { ...docs, backlog: docs.backlog.replaceAll('`notificacao.conciliar`', '`notificacao.consultar`') };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: endpoint de disparo arbitrario extra e rejeitado', () => {
  const extra = '\n- `POST /credit/notificacoes/enviar`;';
  const altered = { ...docs, plan: docs.plan + extra, backlog: docs.backlog + extra };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: linha HTTP de recurso individual enfraquecida e rejeitada', () => {
  const altered = {
    ...docs,
    plan: docs.plan.replace(
      '`GET /credit/automacao/jobs/{job_id}` | 200 | 401, 403, 404',
      '`GET /credit/automacao/jobs/{job_id}` | 200 | 401, 403',
    ),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: P0 deixa de registrar fase vermelha e rejeitado', () => {
  const altered = { ...docs, backlog: docs.backlog.replace('suites inicialmente vermelhas', 'suites completas') };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: IMP-233 deixa de criar schema e rejeitado', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replace('adicionar jobs, tentativas, heartbeats, preferencias, templates, solicitacoes e evidencias', 'documentar tabelas futuras'),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: produtor interno de consentimento removido e rejeitado', () => {
  const altered = {
    ...docs,
    plan: docs.plan.replace(
      'servico interno chamado\npelos fluxos existentes de criacao/atualizacao de Contato',
      'preferencia precisa existir previamente',
    ),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

test('mutacao: atomicidade Contato/preferencia removida e rejeitada', () => {
  const altered = {
    ...docs,
    plan: docs.plan.replace('Contato e preferencia sao\ngravados na mesma UnitOfWork', 'Contato e preferencia usam transacoes independentes'),
  };
  assert.throws(() => contracts.planAndBacklog(altered));
});

function run() {
  let failures = 0;
  console.log('test-epic-010-contracts');
  console.log('='.repeat(50));
  for (const item of cases) {
    try {
      item.fn();
      console.log(`  [PASS] ${item.name}`);
    } catch (error) {
      failures += 1;
      console.log(`  [FAIL] ${item.name}`);
      console.log(`         ${error.message}`);
    }
  }
  console.log('='.repeat(50));
  console.log(`Resumo: ${cases.length - failures}/${cases.length} teste(s) passaram.`);
  return failures;
}

if (require.main === module) process.exit(run() ? 1 : 0);

module.exports = { FILES, contracts, docs, run };
