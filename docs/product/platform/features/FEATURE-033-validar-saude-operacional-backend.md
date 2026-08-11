# FEATURE-033 - Validar Saude Operacional do Backend

**ID:** FEATURE-033

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Disponibilizar healthcheck real para indicar se aplicacao e dependencias
criticas estao operacionais.

---

# 2. Valor de Negócio

Permitir que operadores e automacoes detectem indisponibilidade de banco ou
aplicacao antes que usuarios encontrem erros de negocio.

---

# 3. Escopo

- manter endpoint publico de health;
- verificar conectividade com banco;
- retornar estados `healthy`, `degraded` ou `unhealthy`;
- responder HTTP coerente com o estado;
- incluir correlation ID;
- impedir vazamento de credenciais, DSN, stack trace ou dados sensiveis.

---

# 4. Fora do Escopo

- dashboard externo;
- monitoramento SaaS;
- alerting;
- checks de todos os servicos futuros.

---

# 5. User Stories

- US-091 - Consultar Healthcheck Real;
- US-092 - Impedir Vazamento no Healthcheck.

---

# 6. Dependências

- EPIC-008 - Fundacao Operacional e Observabilidade;
- ADR-016 - Observability, Logging e Correlation ID;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- `/health` permanece publico;
- banco indisponivel altera o estado retornado;
- resposta nao contem segredo ou detalhe interno sensivel;
- OpenAPI documenta o contrato publico.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature de healthcheck real. |
