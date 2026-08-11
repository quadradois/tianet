# Runbook Operacional de Observabilidade

**Versao:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Este runbook orienta diagnostico inicial de falhas tecnicas cobertas pelo
EPIC-008/Fundacao Operacional e Observabilidade: healthcheck, correlation ID,
logs estruturados, erro inesperado, pipeline e migrations.

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

# 7. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Runbook inicial de observabilidade operacional do EPIC-008. |
