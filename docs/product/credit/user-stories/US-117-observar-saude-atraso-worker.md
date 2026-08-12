# US-117 - Observar Saude e Atraso do Worker

**ID:** US-117

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador da plataforma,
**quero** observar liveness, readiness e atraso do worker,
**para** detectar automacao degradada sem expor detalhes publicamente.

---

# 2. Critérios de Aceitação

- liveness/readiness do worker usam mecanismo interno ou protegido;
- readiness fica `degraded` acima do limite de lag da ADR-007;
- falta de acesso a fila ou incapacidade de renovar lease fica `unhealthy`;
- metricas nao expoem payload, contato, segredo ou dados financeiros;
- atraso isolado do worker nao altera sozinho o HTTP de `GET /health` da API.

---

# 3. Regras de Negócio Relacionadas

- health da API e do worker sao contratos separados;
- detalhes de fila exigem autorizacao operacional.

---

# 4. Dependências

- FEATURE-043 - Processar Jobs Duraveis;
- EPIC-008 - Fundacao Operacional e Observabilidade.

---

# 5. Observações Técnicas

O limite de lag e responsabilidade da ADR-007, antes do PLAN.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Observar Saude e Atraso do Worker. |
