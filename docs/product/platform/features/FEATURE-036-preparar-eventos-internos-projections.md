# FEATURE-036 - Preparar Eventos Internos e Projections

**ID:** FEATURE-036

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Definir contrato inicial para eventos internos e projections/read models
reconstruiveis, sem introduzir broker externo nem verdade financeira paralela.

---

# 2. Valor de Negócio

Preparar desacoplamento e leituras mais eficientes sem aumentar complexidade
operacional antes da hora.

---

# 3. Escopo

- envelope minimo de evento interno;
- porta de publicacao em memoria ou contrato equivalente;
- idempotencia e versao de evento;
- diretrizes de projections reconstruiveis;
- guardrail anti-calculo financeiro fora do Motor.

---

# 4. Fora do Escopo

- broker externo;
- outbox transacional completa;
- Saga distribuida;
- read model como fonte oficial de calculo financeiro.

---

# 5. User Stories

- US-097 - Definir Contrato Inicial de Eventos Internos;
- US-098 - Proteger Projections contra Verdade Paralela.

---

# 6. Dependências

- EPIC-008 - Fundacao Operacional e Observabilidade;
- ADR-005 - Event Bus Interno e Eventos de Dominio;
- EPIC-005 - Motor Financeiro;
- EPIC-007 - Operacao Diaria.

---

# 7. Critérios de Aprovação

- evento possui ID, tipo, versao, horario, tenant, correlation ID e payload;
- publicacao inicial nao exige infraestrutura distribuida;
- projections sao reconstruiveis a partir de fatos oficiais;
- nenhuma projection calcula juros, saldo, quitacao, amortizacao ou memoria.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature de eventos internos e projections. |
