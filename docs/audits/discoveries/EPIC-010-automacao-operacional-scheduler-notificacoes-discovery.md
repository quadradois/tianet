# EPIC-010 - Discovery/SDD de Automacao Operacional, Scheduler e Notificacoes

**ID:** EPIC-010

**Tipo:** Artefato de Discovery/SDD

**Versao:** 1.2.0

**Status:** Discovery e Product concluidos; ADRs aceitas; pronto para PLAN

---

# 1. Objetivo

Este discovery decide o proximo pacote de entrega depois da conclusao dos
EPICs formais do MVP e prepara o EPIC-010 - Automacao Operacional, Scheduler e
Notificacoes.

O objetivo e automatizar lembretes e comunicacoes que hoje dependem de acao
manual, usando execucao duravel, idempotente, observavel e isolada por Tenant.
O EPIC nao altera vencimentos, saldos, juros, pagamentos, promessas ou qualquer
outra verdade financeira. Scheduler decide quando executar trabalho operacional;
Notification decide como solicitar o envio por um canal; os contextos de origem
continuam donos das regras de negocio e dos estados oficiais.

---

# 2. Autoridades Consultadas

- `docs/foundation/FOUNDATION-007-product-map.md`;
- `docs/foundation/FOUNDATION-008-mvp-scope.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`;
- `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md`;
- `docs/architecture/adrs/ADR-005-event-bus-interno-eventos-dominio.md`;
- `docs/architecture/adrs/ADR-007-scheduler-batch-processing.md`;
- `docs/architecture/adrs/ADR-009-notifications-channels.md`;
- `docs/architecture/adrs/ADR-015-ci-cd-gates-qualidade.md`;
- `docs/architecture/adrs/ADR-016-observability-logging-correlation-id.md`;
- `docs/audits/discoveries/EPIC-007-operacao-diaria-discovery.md`;
- `docs/audits/discoveries/EPIC-008-fundacao-operacional-observabilidade-discovery.md`;
- `docs/audits/discoveries/EPIC-009-configuracoes-financeiras-calendario-operacional-discovery.md`;
- `docs/product/credit/capabilities/PRODUCT-006-administrar-agenda.md`;
- `docs/product/credit/capabilities/PRODUCT-007-administrar-comunicacao.md`;
- `src/emprestimo/domain/credit/operacao_diaria.py`;
- `src/emprestimo/domain/common/events.py`;
- `src/emprestimo/application/ports.py`.

---

# 3. Contexto e Evidencia AS-IS

O backend concluiu a cadeia funcional do MVP e a fundacao operacional:

1. Agenda permite criar, reagendar, concluir e cancelar compromissos e
   lembretes.
2. Comunicacao registra contatos manuais, mas nao envia mensagens externas.
3. O estado atual de `Lembrete` e `programa`, `enviado`, `concluido` ou
   `cancelado`; as transicoes terminais somente partem de `programa`.
4. Operacao Diaria funciona de forma deterministica sem Scheduler e sem
   descoberta automatica de fatos financeiros.
5. O EPIC-008 entregou correlation ID, logs estruturados, healthcheck e um
   envelope de evento interno com dispatcher em memoria.
6. Broker externo, outbox transacional completa, Scheduler de producao e
   Notification real foram conscientemente adiados.
7. O AMP-001 posiciona `Scheduler + Notification` imediatamente depois de
   Operacao Diaria e Relatorios, antes de Workflow e Integracoes externas.

Essa sequencia torna a automacao operacional o proximo investimento coerente.
O contrato interno de eventos reduz acoplamento dentro do monolito, mas nao
oferece sozinho durabilidade, retry ou recuperacao depois de reinicio.

---

# 4. Problema

Sem Scheduler e Notification governados, o produto permanece com lacunas
operacionais relevantes:

- lembretes vencidos dependem de um operador chamar uma acao manual;
- marcar um lembrete como `enviado` nao comprova que um provedor aceitou a
  mensagem;
- falhas temporarias de canal nao possuem retry persistido nem limite;
- reinicio do processo pode perder trabalho somente mantido em memoria;
- execucoes concorrentes podem duplicar disparos;
- nao existe contrato unico para template, destinatario, preferencia, tentativa
  e resultado de envio;
- logs sem uma identidade de job nao permitem reconstruir toda a execucao;
- colocar essas responsabilidades em Agenda ou Comunicacao criaria acoplamento
  com infraestrutura e provedores.

---

# 5. Decisao de Recorte

O proximo pacote recomendado e:

**EPIC-010 - Automacao Operacional, Scheduler e Notificacoes.**

Ele atravessa duas Capabilities existentes, sem criar uma Capability de negocio
artificial:

- `PRODUCT-006 - Administrar Agenda`, como origem dos lembretes programados;
- `PRODUCT-007 - Administrar Comunicacao`, como historico operacional e
  consumidor do resultado de envio.

Scheduler e Notification sao contextos tecnicos emergentes conforme
FOUNDATION-009. Na fase Product deve-se decidir se serao representados por uma
Capability tecnica transversal ou apenas como componentes habilitadores das
Capabilities existentes. Este discovery recomenda **nao emitir automaticamente
uma nova Capability**: primeiro deve ser demonstrado valor de produto
independente, pois o pacote entrega automacao para Agenda e Comunicacao, e nao
uma funcao vendida isoladamente.

---

# 6. Escopo

O EPIC-010 contempla:

- criar contrato de job duravel com identidade, tipo, payload versionado,
  agendamento, estado, tentativas e correlation ID;
- persistir jobs no PostgreSQL e reivindica-los com exclusao concorrente;
- executar polling controlado em processo separado do servidor HTTP;
- recuperar jobs abandonados depois de timeout de lease;
- aplicar retry com backoff, limite de tentativas e estado terminal;
- cancelar trabalho ainda nao iniciado quando a origem for cancelada;
- criar solicitacao de notificacao idempotente a partir de lembrete elegivel;
- resolver destinatario a partir de contatos autorizados do Devedor, sem copiar
  Cadastro como nova fonte de verdade;
- renderizar template versionado com dados minimos e aprovados;
- definir porta de canal e adaptadores substituiveis;
- registrar tentativa, aceite do provedor, falha protegida e motivo tecnico;
- atualizar o lembrete para `enviado` somente apos aceite confirmado pelo
  adaptador de canal;
- preservar historico operacional e auditoria de negocio;
- propagar `tenant_id`, `correlation_id`, `job_id` e `notification_id` em toda a
  cadeia;
- fornecer healthcheck do worker e sinais operacionais de fila;
- expor APIs administrativas protegidas para consulta, retry e cancelamento;
- criar ADR-007 e ADR-009 antes do PLAN tecnico;
- preparar suites, IAM/RBAC, OpenAPI, runbook e recertificacao.

---

# 7. Fora do Escopo

Este Epic nao contempla:

- alterar calculo de juros, mora, multa, saldo, amortizacao, quitacao,
  renegociacao ou memoria de calculo;
- recalcular vencimento, inadimplencia ou valor de parcela;
- criar cobranca automatica ou confirmar pagamento;
- parear Pagamentos com promessas automaticamente;
- executar regra de Workflow, acordo ou aprovacao complexa;
- broker externo, Saga distribuida ou Event Bus como produto independente;
- outbox generica para todos os aggregates do sistema;
- garantia exatamente uma vez entre sistemas externos;
- comprovacao de leitura, entrega final ou engajamento quando o provedor nao
  oferecer receipt confiavel;
- marketing em massa, campanhas, segmentacao ou jornada comercial;
- WhatsApp, SMS e push simultaneamente no primeiro incremento;
- inbox de respostas do cliente;
- integracao bancaria, PIX, boleto ou webhook financeiro;
- frontend administrativo;
- infraestrutura cloud, Kubernetes ou IaC completa;
- substituir logs tecnicos pela auditoria de negocio.

---

# 8. Fronteiras

| Contexto | Relacao com EPIC-010 | Regra de fronteira |
|---|---|---|
| Platform | Upstream transversal | fornece Tenant e isolamento; nao conhece canal. |
| IAM | Upstream transversal | autentica administradores e protege operacoes de jobs/notificacoes. |
| Cadastro | Upstream | fornece contatos ativos e autorizados por contrato/ACL. |
| Agenda | Produtor de intencao | define lembrete, horario, cancelamento e mensagem operacional. |
| Cobranca | Produtor indireto | pode originar lembrete, mas nao dispara provedor diretamente. |
| Comunicacao | Historico de negocio | registra resultado do contato sem virar fila tecnica. |
| Scheduler | Contexto tecnico primario | executa trabalho no horario, sem decidir regra de negocio. |
| Notification | Contexto tecnico primario | renderiza e envia por porta de canal, sem alterar fatos financeiros. |
| Event Bus interno | Mecanismo auxiliar | transporta envelope no processo; nao substitui a fila duravel. |
| Observabilidade | Suporte transversal | correlaciona job, tentativa, canal e resultado sem expor PII. |
| Motor Financeiro | Fonte protegida | nao e chamado para recalculo por Scheduler ou Notification. |

---

# 9. Modelo Candidato

## 9.1 Scheduler

- `JobAgendado`: aggregate tecnico duravel;
- `JobId`: identidade global;
- `JobTipo`: nome versionado da tarefa;
- `JobEstado`: `pendente`, `processando`, `concluido`, `falhou` ou `cancelado`;
- `JobLease`: worker, inicio e expiracao da reivindicacao;
- `JobTentativa`: numero, inicio, fim, resultado e erro protegido;
- `JobPayload`: referencia minima e versionada, nunca objeto de dominio inteiro.

## 9.2 Notification

- `SolicitacaoNotificacao`: aggregate de envio;
- `NotificacaoEstado`: `pendente`, `processando`, `aceita`, `falhou`,
  `resultado_desconhecido` ou `cancelada`;
- `DestinatarioNotificacao`: referencia ao contato e valor mascarado para
  observabilidade;
- `TemplateNotificacao`: codigo, versao, canal e parametros permitidos;
- `TentativaNotificacao`: adaptador, instante, resultado e identificador externo;
- `ResultadoCanal`: aceite, falha temporaria, falha permanente ou resultado
  desconhecido.

## 9.3 Identidades e Chaves

- `job_id` identifica uma execucao agendada;
- `notification_id` identifica a intencao de notificacao;
- `idempotency_key` deriva de Tenant, origem, versao e finalidade;
- `provider_message_id` identifica o aceite externo quando existir;
- `correlation_id` liga request, evento, job, notificacao e logs.

---

# 10. Decisoes de Discovery

## DA-1001 - Scheduler agenda, o dominio decide

Scheduler pode identificar e executar jobs devidos, mas nao decide se uma
promessa foi cumprida, se uma parcela venceu ou se um contrato mudou de estado.
O handler chama um caso de uso oficial, que revalida a elegibilidade na mesma
fronteira de negocio usada pela API.

## DA-1002 - Job duravel no PostgreSQL antes de broker

O primeiro incremento usa tabela de jobs no PostgreSQL, com reivindicacao
atomica, lease e retry. Isso cobre reinicio e concorrencia no monolito atual sem
introduzir broker externo. Dispatcher em memoria pode notificar handlers, mas
nao e a fonte de durabilidade.

Criar, reagendar, concluir ou cancelar um Lembrete e criar, reagendar ou cancelar
seu job correspondente devem ocorrer na **mesma transacao PostgreSQL e na mesma
UnitOfWork**. Falha em qualquer escrita desfaz ambas. Um reconciliador periodico
pode detectar legado ou corrupcao operacional, mas nao substitui essa garantia
atomica no fluxo normal.

## DA-1003 - Entrega e pelo menos uma vez

A execucao interna assume semantica `at-least-once`. Todo handler deve ser
idempotente e toda solicitacao de notificacao deve possuir chave unica. O
sistema nao promete `exactly-once` para provedores externos.

Todo adapter real deve oferecer ao menos uma protecao verificavel contra o
intervalo entre aceite externo e persistencia local: chave idempotente aceita
pelo provedor ou consulta de status pela identidade da requisicao. Se uma
tentativa terminar com resultado desconhecido e o provedor nao permitir provar
que nao houve aceite, a notificacao passa a `resultado_desconhecido`, fica
bloqueada para reenvio automatico e exige conciliacao administrativa. Ausencia
de confirmacao local, sozinha, nunca autoriza novo disparo.

## DA-1004 - Estado de origem e revalidado antes do efeito

Um job vencido nao garante elegibilidade. Antes do envio, o handler recarrega o
Lembrete no mesmo Tenant/Carteira e exige estado `programa`, horario devido,
contato autorizado e ausencia de envio idempotente anterior. Lembrete concluido,
cancelado ou ja enviado encerra o job sem novo disparo.

## DA-1005 - `enviado` significa aceite do adaptador

No EPIC-010, `EstadoLembrete.ENVIADO` significa que o adaptador confirmou o
aceite da mensagem para processamento externo. Nao significa leitura nem
entrega final. Falha ou timeout nao pode marcar o lembrete como enviado.

A acao HTTP atual que apenas marca `enviado` deve ser reavaliada no PLAN. Ela
nao pode continuar simulando aceite externo para fluxos automatizados; pode ser
depreciada ou restrita a conciliacao administrativa auditada.

## DA-1006 - Notification nao e historico de Comunicacao

Notification guarda intencoes e tentativas tecnicas. Comunicacao guarda o fato
de negocio visivel ao operador. O aceite de envio gera um registro de
Comunicacao por caso de uso idempotente, sem compartilhar tabelas ou aggregates.

## DA-1007 - Um canal real por incremento

O desenho deve ser multicanal por porta, mas o primeiro PLAN seleciona somente
um canal real com base em provedor, credenciais, custo, consentimento e ambiente
de homologacao. Canais adicionais exigem adapters e suites proprias; nao entram
por enum sem integracao verificavel.

## DA-1008 - Retry distingue falha temporaria e permanente

Timeout confirmado sem aceite, limite do provedor e indisponibilidade temporaria
podem gerar retry com backoff. Depois do limite, o job vai para estado `falhou`,
fica consultavel e exige retry administrativo explicito.

Destinatario invalido, ausencia de consentimento e template rejeitado encerram
como falha permanente e **nao podem repetir a mesma solicitacao**. A retomada
exige corrigir contato, consentimento ou template e criar nova solicitacao
versionada, com nova chave idempotente e vinculo auditavel a original. Excecao
administrativa somente e permitida quando o erro for reclassificado, com motivo
e autoria registrados.

## DA-1009 - Lease protege concorrencia

Workers reivindicam jobs de forma atomica e por prazo. Somente o detentor do
lease pode concluir a tentativa. Lease expirado permite recuperacao; token ou
versao de lock impede que um worker antigo conclua depois da retomada.

## DA-1010 - Segredos e PII nao entram em payload ou logs

Credenciais de provedor ficam em configuracao segura fora do banco de jobs.
Payloads e logs nao armazenam token, senha, corpo completo da mensagem, e-mail,
telefone ou nome sem necessidade. Valores de destinatario sao mascarados.

## DA-1011 - Tenant acompanha toda a cadeia

Job, notificacao, contato, lembrete e registro de Comunicacao pertencem ao mesmo
Tenant e Carteira. Worker nao opera com principal humano, mas usa uma identidade
sistemica explicita e nunca remove filtros de isolamento.

## DA-1012 - Correlation ID sobrevive ao agendamento

O job preserva o correlation ID de origem e cada tentativa cria um execution ID
filho. Logs estruturados incluem ambos para separar a intencao original das
reexecucoes.

## DA-1013 - Cancelamento e cooperativo

Job `pendente` pode ser cancelado. Job `processando` recebe pedido de
cancelamento, mas uma chamada externa ja iniciada pode terminar. O reconciliador
deve registrar o resultado real e nunca declarar que um efeito externo foi
desfeito.

## DA-1014 - ADRs reservadas precedem o PLAN

O Product do EPIC-010 deve materializar as decisoes reservadas pelo AMP-001:

- `ADR-007 - Scheduler / Batch Processing`;
- `ADR-009 - Notifications / Channels`.

ADR-005 permanece vigente para eventos internos. Sua expansao para outbox ou
broker exige revisao propria e nao e condicao para o primeiro PLAN.

## DA-1015 - Guardrail anti-calculo continua obrigatorio

Jobs, templates, notificacoes e handlers podem transportar referencias e
resultados oficiais, mas nao calculam juros, mora, multa, saldo, amortizacao,
quitacao, renegociacao ou memoria. Data de vencimento e situacao financeira vem
do Motor por contrato oficial.

## DA-1016 - Health da API e do worker sao contratos separados

`GET /health` preserva o contrato publico do EPIC-008 e mede somente a aptidao
da API e de suas dependencias criticas para receber trafego HTTP. Atraso do
Scheduler nao torna a API indisponivel nem altera sozinho seu HTTP para `503`.

O worker possui liveness e readiness proprios, expostos apenas por mecanismo
interno ou protegido. Sua readiness e `degraded` quando o lag ultrapassa o
limite operacional e `unhealthy` quando nao acessa a fila ou nao renova leases.
Metricas detalhadas de fila permanecem protegidas e nao entram no payload
publico de `/health`.

---

# 11. Contratos Candidatos

## 11.1 `JobAgendadoV1`

- `job_id`;
- `tenant_id`;
- `carteira_id` quando aplicavel;
- `job_type` e `job_version`;
- `scheduled_for` com timezone;
- `payload` minimo e versionado;
- `idempotency_key`;
- `correlation_id`;
- `estado`;
- `attempt_count` e `max_attempts`;
- `lease_owner`, `lease_token` e `lease_expires_at` opcionais;
- `created_at`, `started_at`, `finished_at` opcionais;
- `last_error_code` protegido.

## 11.2 `SolicitacaoNotificacaoV1`

- `notification_id`;
- `tenant_id` e `carteira_id`;
- `origem_tipo`, `origem_id` e `origem_versao`;
- `canal`;
- `contato_id`;
- `template_code` e `template_version`;
- `template_params` em allowlist;
- `idempotency_key`;
- `correlation_id`;
- `estado`;
- timestamps de criacao, aceite e encerramento.

## 11.3 `ResultadoEnvioNotificacaoV1`

- `notification_id`;
- `attempt_id`;
- `provider_code`;
- `provider_message_id` opcional;
- `resultado`: `aceita`, `temporaria`, `permanente` ou `desconhecida`;
- `error_code` protegido;
- `occurred_at`;
- `correlation_id` e `execution_id`.

## 11.4 Porta `NotificationChannel`

A porta recebe uma solicitacao renderizada e devolve resultado tipado. Ela nao
abre transacao de dominio, nao altera Lembrete e nao grava Comunicacao. O caso de
uso de aplicacao coordena persistencia, chamada externa e reconciliacao.

---

# 12. Fluxos Candidatos

## 12.1 Agendar lembrete automatico

1. Usuario autorizado cria ou reagenda Lembrete em Agenda.
2. Aplicacao persiste o Lembrete e um `JobAgendadoV1` idempotente na mesma
   transacao PostgreSQL e UnitOfWork; falha em qualquer escrita desfaz ambas.
3. Cancelamento ou conclusao antes do horario cancela o job pendente na mesma
   transacao da mudanca do Lembrete.
4. Worker reivindica o job quando `scheduled_for` for devido.
5. Handler revalida estado, horario, Tenant, Carteira e contato.
6. Handler cria `SolicitacaoNotificacaoV1` e executa o canal configurado.
7. Aceite marca a notificacao como `aceita` e chama a transicao oficial do
   Lembrete para `enviado`.
8. Comunicacao recebe registro idempotente do fato aceito.
9. Falha temporaria reagenda; falha permanente encerra sem marcar envio.

## 12.2 Recuperar job abandonado

1. Worker A reivindica job e recebe lease/token.
2. Worker A termina inesperadamente antes da conclusao.
3. Depois da expiracao, Worker B reivindica nova versao do lease.
4. Handler consulta a chave idempotente e, quando necessario, o status no
   provedor antes de qualquer novo efeito externo.
5. Se o aceite anterior estiver confirmado, apenas reconcilia estados.
6. Se o provedor confirmar que nao houve aceite, executa nova tentativa conforme
   politica.
7. Se o resultado permanecer desconhecido, marca
   `resultado_desconhecido`, bloqueia reenvio automatico e exige conciliacao.
8. Conclusao tardia do Worker A e rejeitada pelo token antigo.

## 12.3 Retry administrativo

1. Usuario com permissao consulta job/notificacao falha.
2. API retorna motivo protegido e historico de tentativas.
3. Falha temporaria esgotada pode receber retry com justificativa e nova chave
   de tentativa, preservando a chave da solicitacao no provedor.
4. Resultado desconhecido exige conciliacao; nao aceita retry enquanto o aceite
   anterior nao for descartado ou reconciliado.
5. Falha permanente exige contato, consentimento ou template corrigido e cria
   nova solicitacao versionada vinculada a original.
6. Caso de uso revalida a origem antes de qualquer novo envio.

## 12.4 Cancelar antes do envio

1. Lembrete em `programa` e cancelado por caso de uso oficial.
2. Aplicacao cancela o job pendente na mesma transacao e UnitOfWork da mudanca
   do Lembrete.
3. Worker que encontrar job obsoleto revalida a origem e conclui sem efeito.
4. Notificacao ja aceita nao e desfeita; o fato permanece auditavel.

---

# 13. Plano Inicial de Testes

## 13.1 Contratos antes do codigo

- suite de estados de Job e Notificacao;
- suite de idempotencia por origem/versao/finalidade;
- suite de timezone, lease, retry e backoff;
- suite de payload versionado e allowlist de template;
- suite de mascaramento de PII e segredos;
- guardrail anti-calculo fora do Motor.

## 13.2 Dominio e Aplicacao

- agendar, reivindicar, renovar lease, concluir, falhar e cancelar job;
- impedir dupla reivindicacao concorrente;
- recuperar lease expirado e rejeitar token antigo;
- distinguir falha temporaria, permanente e desconhecida;
- nao enviar Lembrete concluido, cancelado ou ja enviado;
- aceitar apenas contato ativo, autorizado e do mesmo Tenant/Carteira;
- nao marcar `enviado` em timeout ou falha;
- bloquear reenvio automatico quando o resultado externo for desconhecido;
- exigir nova solicitacao corrigida para falha permanente;
- registrar Comunicacao uma unica vez apos aceite;
- preservar resultado no replay da mesma chave idempotente.

## 13.3 Persistencia

- migration aditiva para jobs, leases, notificacoes e tentativas;
- indices por estado, `scheduled_for`, Tenant e lease expirado;
- unique constraints de idempotencia;
- concorrencia real com dois workers no PostgreSQL;
- restart entre reivindicacao e conclusao;
- upgrade/downgrade reproduzivel pelo gate de migrations.

## 13.4 Adaptador de Canal

- contract test comum para todo adapter;
- aceite com identificador externo;
- timeout, limite, indisponibilidade e erro permanente;
- resposta malformada do provedor;
- credencial ausente sem vazamento no erro;
- simulador/fake deterministico para CI;
- teste sandbox do canal real separado dos gates sem credenciais.

## 13.5 Worker e Operacao

- startup/shutdown gracioso;
- limite de jobs por ciclo e concorrencia configuravel;
- liveness/readiness do worker separadas do `GET /health` publico da API;
- readiness do worker `degraded` quando estiver atrasado e `unhealthy` quando
  nao conseguir acessar a fila ou renovar leases;
- atraso do worker nao retorna `503` na API enquanto suas dependencias HTTP
  permanecerem aptas;
- metricas/logs de lag, jobs devidos, falhas, retries e duracao;
- correlation ID e execution ID em todas as tentativas;
- runbook para stuck jobs, retry, cancelamento e indisponibilidade do canal.

## 13.6 API, IAM e OpenAPI

- permissoes distintas para consultar, cancelar e retry administrativo;
- contratos HTTP `200/202/400/401/403/404/409`;
- nenhum endpoint publico de disparo arbitrario;
- testes cross-tenant e cross-carteira;
- respostas sem contato em claro, token, corpo integral ou stack trace;
- OpenAPI com schemas, erros, idempotency key e security.

## 13.7 Recertificacao

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- `npm run quality:migrations`;
- revisao adversarial final de concorrencia, idempotencia, seguranca e
  fronteira com o Motor.

---

# 14. Riscos

| Risco | Impacto | Mitigacao |
|---|---|---|
| envio duplicado apos timeout | contato recebe mensagem repetida | chave idempotente, consulta de resultado e reconciliacao. |
| worker concorrente processa o mesmo job | efeito duplicado | claim atomico, lease token e unique constraints. |
| job executa regra financeira | verdade paralela | DA-1001, DA-1015 e guardrail AST. |
| `enviado` continuar sendo acao manual ficticia | historico sem evidencia | DA-1005 e depreciacao/restricao no PLAN. |
| contato ou mensagem vazarem em logs | incidente LGPD | allowlist, mascaramento e testes negativos. |
| retry infinito congestiona fila | indisponibilidade crescente | limite, backoff e estado terminal consultavel. |
| provedor indisponivel bloquear transacao | lock e latencia | chamada externa fora da transacao longa e reconciliacao persistida. |
| cancelamento prometer desfazer envio | estado enganoso | cancelamento cooperativo e historico imutavel. |
| pacote crescer para mensageria distribuida | atraso e operacao complexa | PostgreSQL duravel; broker/outbox generica fora do escopo. |
| canal escolhido sem consentimento | risco legal e reputacional | contato autorizado, politica de opt-out e decisao no PLAN. |

---

# 15. Decisoes de Fechamento Product/ADR

- Product decidiu e-mail transacional como unico canal do primeiro incremento.
- Product exige contato ativo e autorizado no mesmo Tenant/Carteira; opt-out
  vigente bloqueia o envio antes da renderizacao.
- A allowlist inicial contem somente `lembrete_operacional_v1`, com parametros
  `data_hora` e `canal_atendimento`, e exige aprovacao autorizada para ativacao.
- A acao HTTP atual de marcar Lembrete como `enviado` fica restrita a
  conciliacao administrativa auditada e nao chama o provedor.
- ADR-009 escolhe Resend por REST, projeto de teste separado, fake deterministico,
  idempotencia e conciliacao de resultado desconhecido.
- ADR-007 fixa PostgreSQL, worker separado, lease, relogio, lag, tentativas,
  backoff, retencao, shutdown e health interno.

Matriz de fechamento:

| Decisao | Responsavel | Gate de fechamento |
|---|---|---|
| canal | Product | fechado: e-mail transacional no primeiro incremento. |
| provedor e ambiente de teste | Arquitetura | fechado: ADR-009 aceita. |
| consentimento, opt-out e templates | Product | fechado no EPIC-010, FEATURE-044 e US-118/US-119. |
| lag, tentativas, backoff e retencao | Arquitetura + Operacoes | fechado: ADR-007 aceita. |
| semantica da acao HTTP `enviar` | Product + API | fechado: somente conciliacao administrativa auditada. |

As decisoes de Product estao fechadas. As escolhas tecnicas foram encerradas
pelas ADR-007 e ADR-009, sem achado pendente conhecido antes do PLAN.

---

# 16. Alternativas Consideradas

| Alternativa | Razao para nao recomendar agora |
|---|---|
| Event Bus/Outbox completa como EPIC-010 | contrato interno ja existe; broker/outbox generica aumenta custo antes da automacao que prova a necessidade. |
| Scheduler sem Notification | automatiza selecao, mas preserva o gargalo manual de envio. |
| Notification sem Scheduler | permite envio sob comando, mas nao automatiza lembretes e vencimentos. |
| Workflow como proximo EPIC | depende de execucao temporal e comunicacao confiaveis. |
| Integracoes bancarias/PIX | AMP-001 recomenda integra-las somente apos operacao estavel. |
| Frontend | nao resolve a lacuna backend de durabilidade, retry e envio externo. |

---

# 17. Criterios de Pronto para Product

O discovery esta pronto para materializacao Product porque:

- o recorte conjunto Scheduler + Notification esta decidido na secao 5;
- PRODUCT-006 e PRODUCT-007 estao identificados como Capabilities beneficiadas;
- a decisao de emitir ou nao uma nova Capability esta atribuida a fase Product,
  com proibicao de duplicar Capabilities existentes;
- DA-1001 a DA-1016 estao preservadas;
- canal, consentimento, templates e semantica HTTP foram fechados na camada
  Product; provedor, ambiente de teste e parametros operacionais foram fechados
  pelas ADR-007 e ADR-009 na matriz da secao 15;
- ADR-007 e ADR-009 foram aceitas antes do PLAN;
- broker, outbox generica, Workflow, integracoes financeiras e frontend
  permanecem fora do escopo;
- suites e guardrails estao declarados como anteriores ao codigo no futuro
  execution backlog.

---

# 18. Recomendacao de Sequencia

1. Criar o proximo PLAN sequencial e execution backlog, preservando todas as
   decisoes das ADR-007 e ADR-009.
2. Implementar em macro-loop controlado por blocos: contratos, persistencia de
   jobs, worker, Notification, IAM/API, operacao e recertificacao.

---

# 19. Parecer

O proximo EPIC recomendado e **EPIC-010 - Automacao Operacional, Scheduler e
Notificacoes**.

Ele e o melhor proximo passo porque transforma Agenda e Comunicacao ja prontas
em operacao automatizavel, usa a fundacao de observabilidade entregue no
EPIC-008 e respeita a ordem do AMP-001. O recorte com fila PostgreSQL duravel e
um canal real evita introduzir mensageria distribuida antes de haver necessidade
comprovada, sem mascarar os riscos de duplicidade e falha externa.

---

# 20. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.2.0 | 2026-08-11 | ADR-007 e ADR-009 aceitas; matriz tecnica encerrada e discovery liberado para PLAN. |
| 1.1.0 | 2026-08-11 | Cinco achados adversariais corrigidos: prontidao, atomicidade, resultado desconhecido, retry permanente e health do worker. |
| 1.0.0 | 2026-08-11 | Discovery/SDD inicial e decisao do EPIC-010 - Automacao Operacional, Scheduler e Notificacoes. |
