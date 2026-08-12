# US-115 - Reivindicar e Executar Job com Lease

**ID:** US-115

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operacao da plataforma,
**quero** que workers reivindiquem jobs por lease,
**para** evitar execucao concorrente do mesmo trabalho.

---

# 2. Critérios de Aceitação

- reivindicacao de job devido e atomica no PostgreSQL;
- lease identifica owner, token e expiracao;
- somente o token vigente renova ou conclui a tentativa;
- dois workers concorrentes nao executam o mesmo lease;
- cada tentativa preserva correlation ID e execution ID.

---

# 3. Regras de Negócio Relacionadas

- Scheduler nao decide regra do dominio de origem;
- isolamento por Tenant acompanha job, tentativa e logs.

---

# 4. Dependências

- FEATURE-043 - Processar Jobs Duraveis;
- ADR-007 - Scheduler / Batch Processing.

---

# 5. Observações Técnicas

Indices e estrategia de lock serao definidos no PLAN apos ADR-007.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Reivindicar e Executar Job com Lease. |
