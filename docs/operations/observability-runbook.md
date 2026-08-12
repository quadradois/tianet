# Runbook Operacional de Observabilidade

**Versao:** 1.1.0

**Status:** Aprovado

---

# 1. Objetivo

Este runbook orienta diagnostico inicial de falhas tecnicas cobertas pelo
EPIC-008/Fundacao Operacional e Observabilidade: healthcheck, correlation ID,
logs estruturados, erro inesperado, pipeline, migrations e o worker Scheduler do
EPIC-010.

---

# 2. Healthcheck

Endpoint publico:

```text
GET /health
```

Contrato esperado:

- `200` quando o backend e o banco estiverem `healthy`;
- `503` quando dependencia essencial estiver `degraded` ou `unhealthy`;
- corpo minimo com `status`, `service` e `checks`;
- header `X-Correlation-ID` em todas as respostas.

O healthcheck nao deve expor tenant, usuario, DSN, token, segredo, stack trace
ou dados financeiros.

---

# 3. Correlation ID

Ao investigar erro operacional:

1. capture o valor de `X-Correlation-ID` retornado pela API;
2. procure esse valor nos logs tecnicos estruturados;
3. use o par metodo/caminho/status para isolar a falha;
4. nunca cole token, senha, DSN ou payload sensivel em tickets ou mensagens.

Quando o cliente nao envia um ID valido, a API gera um UUID e devolve no header.

---

# 4. Erro Tecnico 500

Resposta esperada:

```json
{"codigo":"erro_interno","mensagem":"erro inesperado no servidor"}
```

O detalhe tecnico fica somente nos logs estruturados e deve registrar, no minimo:

- `correlation_id`;
- metodo HTTP;
- caminho HTTP;
- status HTTP ou tipo do erro.

Stack trace, segredo, token, DSN e dados financeiros nao devem aparecer no
payload HTTP.

---

# 5. Pipeline e Migrations

Gates oficiais locais:

```bash
uv run pytest -q
uv run ruff check .
uv run black --check .
uv run mypy src tests
npm run docs:validate
npm run docs:test
npm run quality:migrations
```

`npm run quality:migrations` e destrutivo e deve rodar apenas contra banco
descartavel com `MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE=1`.

---

# 6. Eventos e Projections

Eventos internos usam envelope minimo com:

```text
event_id, event_type, event_version, occurred_at, tenant_id, correlation_id, payload
```

Projections/read models devem ser reconstruiveis a partir de fatos oficiais,
registrando origem, versao e `data_referencia` quando aplicavel. Nenhuma
projection pode calcular juros, saldo, quitacao, amortizacao ou memoria de
calculo fora do Motor Financeiro.

---

# 7. Scheduler e Notification

O health da API e do worker sao contratos separados. Atraso da fila nao deve
alterar sozinho o HTTP de `/health`. Liveness, readiness e metricas do worker
ficam em mecanismo interno ou protegido.

Diagnostico inicial do worker:

1. confirme acesso do worker ao PostgreSQL e compare seu heartbeat com o limite
   de 30 segundos;
2. inspecione o job vencido mais antigo e `lag_seconds`; acima de 60 segundos em
   tres ciclos consecutivos significa readiness `degraded`;
3. procure leases expirados, tokens concorrentes, tentativas acima de 300
   segundos e tentativas esgotadas pelos
   identificadores `job_id`, `notification_id` e `correlation_id`;
4. nao force estado terminal: leases expirados devem ser recuperados por novo
   claim, e resultado externo desconhecido exige conciliacao;
5. em shutdown, pare novos claims e aguarde drenagem por ate 30 segundos; trabalho
   incompleto nao pode ser marcado como concluido.

Indisponibilidade do banco por 20 segundos, heartbeat ausente por 30 segundos,
tentativa acima de 300 segundos ou falha de renovacao antes do lease expirar
torna o worker `unhealthy`. Jobs
terminais e tentativas permanecem por 90 dias; falhas administrativas e
resultados desconhecidos nao sao purgados automaticamente.

Para falha do Resend:

- 429, conflito concorrente da mesma chave e falha comprovadamente anterior ao
  envio seguem retry governado, sem retry interno no adaptador;
- 5xx, 2xx malformado ou falha apos possivel transmissao ficam como
  `resultado_desconhecido` e nao autorizam retry;
- credencial, contato ou template invalido exigem correcao e nova solicitacao;
- timeout apos possivel transmissao vira `resultado_desconhecido` e bloqueia
  reenvio automatico;
- conciliacao exige permissao IAM, evidencia externa, motivo e auditoria;
- aceite do provedor nao significa entrega ou leitura.

Nunca inclua destinatario integral, corpo, chave do provedor ou PII em ticket,
log, metrica ou resposta administrativa.

---

# 8. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-11 | Diagnostico, health, shutdown, retencao e conciliacao do Scheduler/Notification adicionados. |
| 1.0.0 | 2026-08-11 | Runbook inicial de observabilidade operacional do EPIC-008. |
