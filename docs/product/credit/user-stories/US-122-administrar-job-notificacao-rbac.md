# US-122 - Administrar Job e Notificacao com RBAC

**ID:** US-122

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** administrador operacional autorizado,
**quero** consultar, cancelar ou solicitar retry de jobs e notificacoes,
**para** recuperar falhas sem obter um endpoint de disparo arbitrario.

---

# 2. Critérios de Aceitação

- consulta, cancelamento, retry e conciliacao usam permissoes distintas;
- Tenant e Carteira limitam todos os recursos;
- recurso inexistente ou cross-tenant retorna `404` logico;
- transicao proibida ou idempotencia divergente retorna `409`;
- retry exige justificativa e revalida origem, estado e classificacao da falha.

---

# 3. Regras de Negócio Relacionadas

- nao existe endpoint publico para disparo livre;
- falha permanente exige solicitacao corrigida e versionada.

---

# 4. Dependências

- FEATURE-045 - Operar e Reconciliar Automacao;
- EPIC-006 - IAM.

---

# 5. Observações Técnicas

APIs devem documentar `200/202/400/401/403/404/409` no OpenAPI.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Administrar Job e Notificacao com RBAC. |
