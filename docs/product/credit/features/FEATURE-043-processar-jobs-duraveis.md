# FEATURE-043 - Processar Jobs Duraveis

**ID:** FEATURE-043

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Executar trabalho temporal de forma duravel, concorrente e recuperavel no
PostgreSQL, sem decidir regras dos dominios de origem.

---

# 2. Valor de Negócio

Permite automacao reiniciavel e observavel sem depender inicialmente de broker
externo.

---

# 3. Escopo

- reivindicar jobs devidos por lease atomico;
- renovar lease e rejeitar token antigo;
- registrar tentativas e resultados protegidos;
- recuperar jobs abandonados e aplicar retry governado;
- expor liveness/readiness internas do worker.

---

# 4. Fora do Escopo

- workflow de negocio;
- broker ou outbox generica;
- alterar o `/health` publico da API por atraso isolado do worker.

---

# 5. User Stories

- US-115 - Reivindicar e Executar Job com Lease;
- US-116 - Recuperar Job e Aplicar Retry Governado;
- US-117 - Observar Saude e Atraso do Worker.

---

# 6. Dependências

- EPIC-010 - Automacao Operacional, Scheduler e Notificacoes;
- EPIC-008 - Fundacao Operacional e Observabilidade;
- ADR-007 - Scheduler / Batch Processing.

---

# 7. Critérios de Aprovação

- somente o lease vigente conclui a tentativa;
- restart nao perde jobs devidos;
- falha temporaria e permanente seguem politicas distintas;
- health do worker permanece interno ou protegido.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature Processar Jobs Duraveis. |
