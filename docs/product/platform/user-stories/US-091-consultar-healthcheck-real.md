# US-091 - Consultar Healthcheck Real

**ID:** US-091

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador da plataforma,

**Quero** consultar um healthcheck real,

**Para** saber se aplicacao e banco estao aptos a receber trafego.

---

# 2. Critérios de Aceitação

- `/health` responde sem token;
- banco disponivel retorna estado `healthy`;
- banco indisponivel retorna estado `degraded` ou `unhealthy`;
- resposta inclui correlation ID;
- status HTTP e coerente com o estado operacional: `200` para `healthy` e
  `503` para `degraded` ou `unhealthy`.

---

# 3. Regras de Negócio Relacionadas

- `/health` e excecao publica aceita pelo IAM;
- healthcheck e telemetria tecnica, nao auditoria de negocio.

---

# 4. Dependências

- FEATURE-033 - Validar Saude Operacional do Backend;
- EPIC-006 - IAM;
- ADR-016 - Observability, Logging e Correlation ID.

---

# 5. Observações Técnicas

A implementacao deve testar explicitamente banco disponivel e indisponivel sem
depender de dados de Tenant.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de healthcheck real. |
