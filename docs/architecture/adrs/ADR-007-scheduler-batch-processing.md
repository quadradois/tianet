# ADR-007: Scheduler e Batch Processing

> **Status:** Aceito
> **Data:** 2026-08-11
> **Autor(es):** Arquitetura
> **Revisor(es):** Arquitetura e Operacoes
> **Aprovacao:** Arquitetura / 2026-08-11
> **Substitui:** —
> **Substituido por:** —

---

## Contexto

O EPIC-010 automatiza lembretes que hoje dependem de acao manual. A API nao
pode manter timers em memoria: reinicios, replicas concorrentes e indisponibilidade
temporaria perderiam ou duplicariam trabalho. O Scheduler precisa executar no
horario sem assumir as regras do dominio de Agenda, Comunicacao ou Motor.

O PostgreSQL 16 ja e a dependencia duravel oficial. O primeiro incremento nao
justifica broker externo, outbox generica ou plataforma de Workflow.

---

## Decisao

### Persistencia e fronteira transacional

- Jobs e tentativas serao persistidos no PostgreSQL em tabelas proprias.
- O Lembrete e seu job serao criados, reagendados, concluidos ou cancelados na
  mesma transacao PostgreSQL e na mesma UnitOfWork. Concluir ou cancelar a
  origem cancela seu job elegivel. Falha em qualquer escrita desfaz ambas.
- O job guarda a identidade e a versao da origem. Antes de produzir efeito, o
  handler recarrega e revalida a origem; o Scheduler executa, o dominio decide.
- O Event Bus interno pode anunciar fatos, mas nao e a fila duravel nem fonte
  de recuperacao do Scheduler.
- Scheduler, handlers e projections nao calculam nem reinterpretam juros,
  mora, multa, saldo, vencimento ou qualquer outro fato financeiro.

### Worker, polling e reivindicacao

O worker roda em processo separado da API. Nao usa `BackgroundTasks`, timer no
processo web ou estado em memoria como fonte de verdade.

Cada ciclo abre uma transacao curta e:

1. seleciona jobs elegiveis em ordem deterministica por
   `(scheduled_for, created_at, job_id)`;
2. usa `FOR UPDATE SKIP LOCKED`;
3. grava `lease_token`, `lease_owner`, `lease_expires_at` e estado em execucao;
4. confirma a transacao;
5. executa o handler fora da transacao de reivindicacao.

Somente o token vigente pode renovar lease ou concluir a tentativa. Resultado
de token expirado ou substituido e descartado e auditado. Jobs com lease
expirado voltam a ser elegiveis em um ciclo posterior.

Valores iniciais e limites de configuracao:

| Parametro | Padrao | Limite |
|---|---:|---:|
| `SCHEDULER_POLL_INTERVAL_SECONDS` | 1 | 1 a 30 |
| `SCHEDULER_BATCH_SIZE` | 4 | 1 a 16 |
| `SCHEDULER_CONCURRENCY` | 4 | 1 a 16 |
| `SCHEDULER_LEASE_SECONDS` | 60 | 30 a 300 |
| `SCHEDULER_LEASE_RENEW_SECONDS` | 20 | no maximo um terco do lease |
| `SCHEDULER_SHUTDOWN_GRACE_SECONDS` | 30 | 5 a 120 |
| `SCHEDULER_MAX_ATTEMPT_RUNTIME_SECONDS` | 300 | 30 a 1800 |

Cada ciclo reivindica no maximo `min(batch_size, slots_de_execucao_livres)`. Um
job so recebe lease quando existe slot para iniciar imediatamente; o worker nao
mantem backlog local de jobs reivindicados. O pool de conexoes do worker nao
pode exceder concorrencia mais duas conexoes.
Configuracao invalida impede o startup. O limite total de conexoes da API e do
worker deve respeitar a capacidade do PostgreSQL do ambiente.

### Relogio, timezone e atraso

- Instantes persistidos usam `timestamptz` e UTC.
- `clock_timestamp()` do PostgreSQL e o relogio autoritativo para elegibilidade,
  lease e atraso; o relogio de aplicacao e injetavel para dominio e testes.
- Datas de negocio continuam sob os contextos de origem. O Scheduler nao cria
  novo vencimento nem converte calendario financeiro.
- A timezone do Tenant e validada como identificador IANA e serve apenas para
  apresentacao ou para interpretar uma intencao local antes de persistir UTC.

`lag_seconds` e `max(0, clock_timestamp() - scheduled_for)` do job pendente
vencido mais antigo:

- readiness `healthy`: ate 60 segundos;
- readiness `degraded`: acima de 60 segundos em tres ciclos consecutivos;
- worker `unhealthy`: fila inacessivel continuamente por 20 segundos, loop sem
  heartbeat por 30 segundos, lease proprio sem renovacao antes de expirar ou
  tentativa em execucao acima de `SCHEDULER_MAX_ATTEMPT_RUNTIME_SECONDS`.

O supervisor mede a duracao de cada tentativa pelo relogio monotônico local e
nao renova o lease depois do limite. O handler recebe cancelamento cooperativo;
se um efeito externo puder ter ocorrido, o resultado fica desconhecido em vez
de ser repetido automaticamente.

Atraso do worker nao altera sozinho o HTTP de `/health` da API. Liveness,
readiness e metricas detalhadas do worker ficam em mecanismo interno ou
protegido.

### Tentativas, backoff e falhas

Sao permitidas no maximo cinco tentativas totais. Falha temporaria usa os
intervalos 30 segundos, 2 minutos, 10 minutos e 30 minutos, com jitter de mais
ou menos 20%. `Retry-After` pode ser respeitado, limitado entre 30 segundos e
30 minutos. Testes injetam jitter deterministico.

Falha permanente nao repete a mesma solicitacao. Exige correcao e nova
`SolicitacaoNotificacao` versionada, vinculada a anterior; a origem de negocio
nao precisa mudar quando a correcao for tecnica. Resultado externo desconhecido
nao e retentado automaticamente e segue a conciliacao definida pela ADR-009.

### Cancelamento e shutdown

- Cancelamento e cooperativo: marca a intencao duravelmente e o handler verifica
  o sinal em pontos seguros.
- No shutdown, o worker para novas reivindicacoes, solicita cancelamento dos
  handlers, renova leases durante a drenagem e aguarda ate 30 segundos.
- Ao fim do prazo, encerra sem marcar trabalho incompleto como concluido. Outro
  worker recupera o job depois da expiracao do lease.

### Retencao, identidade e operacao

- Jobs terminais e tentativas ficam por 90 dias apos resolucao.
- Falha pendente de acao administrativa e resultado desconhecido nao sao
  removidos automaticamente.
- Auditoria e Comunicacao seguem suas politicas proprias e nao sao apagadas com
  a fila tecnica.
- O processo usa ator tecnico interno `scheduler-worker`, com Tenant e Carteira
  herdados do job. Isso nao cria Principal externo nem contorna IAM.
- Consulta, cancelamento, retry e conciliacao humanos exigem permissoes IAM
  distintas, escopo Tenant/Carteira, motivo e auditoria.

O runbook operacional deve cobrir fila atrasada, lease preso, esgotamento de
tentativas, indisponibilidade do banco, drenagem e recuperacao. Nenhum endpoint
permite criar ou disparar job arbitrario.

---

## Alternativas Consideradas

| Opcao | Pros | Contras | Decisao |
|---|---|---|---|
| Timer no processo da API | simples | perde trabalho e duplica em replicas | rejeitada |
| Broker externo | escala e recursos maduros | infraestrutura prematura | adiada |
| PostgreSQL + worker separado | duravel, transacional e compativel com a stack | exige polling e disciplina de lease | escolhida |

---

## Consequencias

- A migration do EPIC-010 deve modelar job, tentativa, lease e indices de claim.
- API e worker terao ciclo de vida, pools e health separados.
- A entrega e pelo menos uma vez; idempotencia do efeito externo e obrigatoria.
- O PLAN-018 deve criar suites de concorrencia, lease, retry, shutdown e
  atomicidade antes da implementacao.
- Broker, outbox generica e Workflow continuam fora do escopo.

---

## Validacao

- concorrencia com dois workers prova que um job tem um unico token vigente;
- lease expirado e recuperado e token antigo nao conclui;
- criacao/cancelamento de Lembrete e job sofre rollback atomico;
- backoff, limite de cinco tentativas e falha permanente sao testados;
- shutdown nao produz conclusao falsa;
- lag separa readiness do worker do `/health` publico da API;
- guardrail impede calculo financeiro e disparo arbitrario.

---

## Referencias

- EPIC-010 - Automacao Operacional, Scheduler e Notificacoes;
- AMP-001 - reserva arquitetural ADR-007;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-005 - Event Bus Interno e Eventos de Dominio;
- ADR-015 - CI/CD e Gates de Qualidade;
- ADR-016 - Observability, Logging e Correlation ID;
- FOUNDATION-007 - Product Map;
- FOUNDATION-009 - Capability Map;
- [PostgreSQL 16 - SELECT locking clause](https://www.postgresql.org/docs/16/sql-select.html);
- [PostgreSQL 16 - Date/Time Functions](https://www.postgresql.org/docs/16/functions-datetime.html).

---

## Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-11 | Decisao do Scheduler duravel, concorrencia, relogio, health, retry, retencao e operacao. |
