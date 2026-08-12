# PLAN-020 - Fechamento e Certificacao do Backend MVP

**ID:** PLAN-020

**Versao:** 1.0.0

**Status:** Planejado

---

# 1. Contexto

Este plano fecha a camada backend do MVP apos a conclusao dos EPICs 001 a 010.
Ele nao cria novo EPIC funcional: organiza uma certificacao transversal para
provar que os contextos ja implementados operam de ponta a ponta, com contratos
HTTP, seguranca, persistencia, observabilidade, worker e documentacao
consistentes.

O objetivo e transformar o estado atual em uma base pronta para decisao de
frontend, demo controlada ou hardening pontual, sem alterar regra financeira e
sem introduzir escopo novo.

---

# 2. Referencias

- `docs/foundation/FOUNDATION-007-product-map.md`;
- `docs/foundation/FOUNDATION-008-mvp-scope.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`;
- `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md`;
- `docs/architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md`;
- `docs/architecture/adrs/ADR-005-event-bus-interno-eventos-dominio.md`;
- `docs/architecture/adrs/ADR-007-scheduler-batch-processing.md`;
- `docs/architecture/adrs/ADR-009-notifications-channels.md`;
- `docs/architecture/adrs/ADR-015-ci-cd-gates-qualidade.md`;
- `docs/architecture/adrs/ADR-016-observability-logging-correlation-id.md`;
- `docs/implementation/plans/PLAN-001-feature-001-tenant-provisioning.md`;
- `docs/implementation/plans/PLAN-002-epic-001-tenant-management.md`;
- `docs/implementation/plans/PLAN-003-epic-002-cadastro-de-devedores.md`;
- `docs/implementation/plans/PLAN-005-epic-006-iam-detalhado.md`;
- `docs/implementation/plans/PLAN-009-epic-003-comercial.md`;
- `docs/implementation/plans/PLAN-011-epic-004-contratos.md`;
- `docs/implementation/plans/PLAN-013-epic-005-motor-financeiro.md`;
- `docs/implementation/plans/PLAN-014-epic-007-operacao-diaria.md`;
- `docs/implementation/plans/PLAN-015-epic-008-fundacao-operacional-observabilidade.md`;
- `docs/implementation/plans/PLAN-017-epic-009-configuracoes-financeiras-calendario-operacional.md`;
- `docs/implementation/plans/PLAN-018-epic-010-automacao-operacional-scheduler-notificacoes.md`;
- `docs/implementation/reports/PLAN-018-execution-report-2026-08-11.md`;
- `docs/operations/quality-gates-and-migrations.md`;
- `docs/operations/observability-runbook.md`.

---

# 3. Situacao Atual

## Concluido e pronto para certificar

- Plataforma possui Tenant, Carteira padrao, Usuario administrador, IAM,
  RBAC, credenciais, sessoes e bootstrap operacional;
- Cadastro possui Devedor, Contatos, unicidade por Carteira, historico
  cadastral e endpoints protegidos;
- Comercial possui SimulacaoComercial, PropostaComercial, decisoes, contrato
  logico de proposta aprovada e guardrail anti-Motor;
- Contratos possui formalizacao, assinatura, cancelamento, encerramento e
  liberacao logica para Motor;
- Motor Financeiro possui Emprestimo, Parcelas, Pagamentos, Saldo, Quitacao,
  Renegociacao, Memoria de Calculo, eventos financeiros e guardrails de
  precisao;
- Operacao Diaria possui cobranca manual, promessas, agenda, lembretes,
  comunicacao manual e relatorios operacionais;
- Configuracoes Financeiras possui modalidades, parametros, calendario,
  vigencias, snapshots contratuais e fronteira Configuracoes parametriza,
  Motor calcula;
- Fundacao Operacional possui CI/gates, migrations reproduziveis, healthcheck
  real, correlation ID, logs estruturados, tratamento tecnico de erro,
  eventos internos e diretrizes de projections;
- Automacao possui Scheduler duravel, worker separado, lease/fencing/retry,
  Notification por canal, fake deterministico, Resend REST, conciliacao e
  operacao administrativa protegida.

## Lacunas reais para fechamento do MVP

- falta uma matriz unica Product -> API -> suites que cubra todos os EPICs do
  backend MVP;
- existem suites por contexto, mas faltam suites E2E transversais que exercitem
  a jornada inteira entre contextos com PostgreSQL real;
- os contratos HTTP existem por area, mas falta uma matriz global 400/401/403/
  404/409 e um teste que compare rotas reais, OpenAPI e RBAC;
- o isolamento Tenant/Carteira e idempotencia sao cobertos em pontos criticos,
  mas faltam regressions globais por fluxo composto;
- auditoria append-only existe, mas falta recertificacao transversal de eventos
  de negocio, mutacoes administrativas, rollback e trilha historica;
- migrations estao encadeadas ate `0016`, mas falta congelar baseline final do
  MVP e validar dados minimos sem migrations destrutivas;
- health, logs, correlation ID e worker estao implementados, mas falta smoke
  integrado API + worker + banco;
- documentos historicos ainda podem conter nomenclatura antiga ou caveats
  superados, exigindo classificacao como historico, atualizado ou obsoleto.

---

# 4. Escopo do Fechamento

O PLAN-020 audita e certifica o backend MVP existente. O trabalho pode criar
suites, contratos de validacao e documentos de evidencia; correcoes de defeito
podem ser planejadas no backlog, mas nao fazem parte desta fase documental.

Nao ha novo EPIC funcional, nova Capability, frontend, regra financeira nova,
integracao bancaria, canal novo de notificacao, broker externo, outbox
generica, cloud/IaC ou dashboard APM externo.

---

# 5. Matriz de Rastreabilidade Backend MVP

| Area | Product/EPIC | Superficie backend | Suites existentes | Gap de certificacao |
|---|---|---|---|---|
| Plataforma | EPIC-001, EPIC-006, EPIC-008 | `/platform/tenants`, `/auth`, `/iam`, `/health` | unit, integration api/application/repositories, observability | matriz global Product/API/RBAC e smoke completo |
| Cadastro | EPIC-002 | `/credit/carteiras/{carteira_id}/devedores` | domain, application, repository, api | E2E Tenant -> IAM -> Cadastro com idempotencia e auditoria |
| Comercial | EPIC-003 | `/credit/comercial/*` | domain, application, repository, api, guardrails | E2E Cadastro -> Simulacao -> Proposta -> Aprovacao |
| Contratos | EPIC-004 | `/credit/contratos/*` | domain, application, repository, api | E2E proposta aprovada -> contrato assinado -> liberado |
| Motor | EPIC-005 | `/credit/motor/*` | domain, application, repository, api, precision guardrails | E2E contrato liberado -> emprestimo -> parcelas -> pagamento -> saldo |
| Operacao Diaria | EPIC-007 | `/credit/cobranca`, `/credit/agenda`, `/credit/comunicacoes`, `/credit/relatorios` | domain, application, repository, api, relatorios | E2E Motor -> cobranca -> agenda -> comunicacao |
| Configuracoes | EPIC-009 | `/credit/configuracoes-financeiras/*` | domain, application, repository, api, consumer guardrails | E2E configuracao vigente -> snapshot -> contrato sem calculo paralelo |
| Automacao | EPIC-010 | `/credit/automacao`, `/credit/notificacoes`, worker Scheduler | domain, application, repository, api, worker, atomicity | smoke API + worker + fake Notification + replay |

---

# 6. API

O PLAN-020 nao cria rotas novas. A certificacao cobre as superficies ja
implementadas e compara rotas reais, OpenAPI, permissao IAM, tenant/carteira,
correlation ID e matriz HTTP.

Superficies obrigatorias:

- Platform: tenants, autenticacao, IAM e health;
- Credit/Cadastro: devedores e historico cadastral;
- Comercial: simulacoes, propostas, decisoes e contrato logico;
- Contratos: formalizacao, assinatura, liberacao, cancelamento e encerramento;
- Motor Financeiro: emprestimos, parcelas, pagamentos, saldo, quitacao,
  renegociacao e memoria;
- Operacao Diaria: cobranca, promessas, agenda, lembretes, comunicacao e
  relatorios;
- Configuracoes Financeiras: modalidades, calendarios, configuracoes,
  vigencias e snapshots;
- Automacao: jobs, notificacoes, templates, conciliacao e alias legado de
  lembrete sem disparo arbitrario.

Erros globais a certificar: `400`, `401`, `403`, `404` e `409`, mantendo
`404` logico para recursos fora do escopo quando isso protege isolamento.

---

# 7. Fluxos E2E Obrigatorios

## F1 - Provisionamento e acesso

Tenant e administrador sao criados com idempotencia, auditoria e Carteira
padrao. O usuario ativa credencial, autentica, recebe principal e acessa apenas
recursos permitidos do proprio Tenant.

## F2 - Cadastro a proposta

Usuario autorizado cadastra Devedor com Contato, consulta por documento,
executa SimulacaoComercial sem calculo financeiro definitivo no Comercial,
cria PropostaComercial e aprova dentro do estado permitido.

## F3 - Proposta a contrato

Proposta aprovada gera contrato logico, Contratos formaliza, assina e libera
ContratoLiberadoLogico sem retroatividade e sem recalcular parametros
financeiros.

## F4 - Contrato a Motor

Motor cria Emprestimo a partir do contrato liberado, gera parcelas, registra
pagamento idempotente, consulta saldo, memoria de calculo, quitacao e
renegociacao usando apenas autoridade do Motor.

## F5 - Motor a Operacao Diaria

Operacao Diaria consulta vencimentos e inadimplencia por fatos oficiais, abre
cobranca manual, registra acao, promessa, agenda, lembrete, comunicacao manual
e relatorios sem recalcular juros, saldo ou memoria.

## F6 - Agenda a Scheduler e Notification

Lembrete elegivel cria job na mesma UnitOfWork, worker reivindica por lease,
revalida origem, envia notificacao por fake deterministico, registra Comunicacao
apos aceite e conclui job de forma atomica e idempotente.

---

# 8. Decisoes de Certificacao

## D1 - Suites antecedem correcoes

Todo gap deve primeiro ganhar teste ou contrato que reproduza o risco. Correcao
sem suite precedente so e permitida para higiene documental ou ajuste mecanico
de lint sem comportamento.

## D2 - Matriz global nao substitui suites locais

As suites locais continuam sendo autoridade de cada contexto. A matriz global
verifica integracao, rastreabilidade e contratos entre areas.

## D3 - 404 logico preserva isolamento

Recursos fora do Tenant ou Carteira permanecem indistinguiveis de inexistentes
quando isso protege isolamento. O fechamento deve testar 401/403/404 conforme a
matriz HTTP global.

## D4 - Motor continua unica autoridade financeira

Comercial, Contratos, Operacao Diaria, Configuracoes, Scheduler, Notification,
eventos e projections nao calculam nem reinterpretam juros, mora, multa, saldo,
quitacao, amortizacao, renegociacao ou memoria de calculo.

## D5 - Observabilidade nao vaza negocio sensivel

Health, logs, correlation ID, erros tecnicos e worker podem informar estado
operacional, mas nao expõem segredo, token, DSN, PII, tenant nao autorizado,
payload integral de notificacao ou fatos financeiros sensiveis.

## D6 - Historico documental e preservado

Documentos historicos com nomes antigos nao devem ser reescritos
silenciosamente. A certificacao classifica cada divergencia como: historico
aceito, documento a atualizar, documento obsoleto ou erro ativo.

---

# 9. Estrategia de Testes

- **Contratos documentais:** PLAN-020, execution backlog, Product, EPICs,
  Features, User Stories, ADRs, reports e registry consistentes; a suite
  `node scripts/tests/test-plan-020-contracts.js` deve integrar o gate
  `npm run docs:test`;
- **Inventario API/OpenAPI:** todas as rotas reais aparecem na matriz, possuem
  security quando aplicavel, `X-Correlation-ID` e erros 400/401/403/404/409;
- **E2E transversais:** F1 a F6 com PostgreSQL real, principal autenticado,
  idempotencia, auditoria e rollback;
- **Seguranca:** cross-tenant/carteira, permissao ausente, token invalido,
  dados mascarados, endpoint publico minimo e endpoint protegido governado;
- **Persistencia/migrations:** upgrade/downgrade/upgrade, constraints,
  indices criticos, seed minimo e ausencia de alteracao destrutiva;
- **Worker/operacao:** claim, lease, retry, resultado desconhecido, shutdown,
  health interno, fake sem rede e logs com correlation ID;
- **Guardrails:** anti-calculo fora do Motor, anti-regra financeira livre,
  anti-disparo arbitrario, anti-broker/outbox fora de escopo;
- **Docs historicos:** documentos divergentes classificados e sem falso status
  de concluido quando houver caveat ativo;
- **Recertificacao:** suite Python completa, qualidade, docs, migrations, smoke
  API/worker e revisao adversarial final.

---

# 10. Ordem de Execucao

1. P0 inventario, contratos documentais e suites globais antes de qualquer
   correcao;
2. P1 fluxos E2E entre contextos;
3. P2 seguranca, isolamento, idempotencia e auditoria;
4. P3 operacao, worker, health, logs e migrations;
5. P4 OpenAPI, matriz HTTP e documentacao historica;
6. P5 recertificacao final, relatorio de prontidao e recomendacao de proximo
   ciclo.

O backlog usa `IMP-254..IMP-273`. Cada item inicia apenas com dependencias
anteriores satisfeitas.

---

# 11. Gates de Aceite

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
- matriz Product/API/RBAC sem lacunas bloqueantes;
- OpenAPI consistente com rotas reais e erros documentados;
- ausencia de calculo financeiro fora do Motor;
- revisao adversarial final sem achados bloqueantes;
- relatorio de prontidao do backend MVP emitido.

---

# 12. Fora do Escopo Tecnico

- frontend;
- mobile;
- novo EPIC ou pacote funcional sem necessidade comprovada;
- mudanca de regra financeira;
- novos canais de notificacao;
- integracao bancaria, PIX, boleto ou API publica;
- broker externo, outbox generica, workflow ou campanhas;
- cloud/IaC e dashboards externos;
- commit ou PR nesta fase documental.

---

# 13. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-12 | Plano tecnico de fechamento e certificacao transversal do Backend MVP apos EPIC-010. |
