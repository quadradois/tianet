# US-097 - Definir Contrato Inicial de Eventos Internos

**ID:** US-097

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** arquiteto da plataforma,

**Quero** um contrato inicial de eventos internos,

**Para** preparar desacoplamento futuro sem introduzir broker externo antes da hora.

---

# 2. Critérios de Aceitação

- envelope possui `event_id`, `event_type`, `event_version`, `occurred_at`,
  `tenant_id`, `correlation_id` e `payload`;
- publicacao inicial pode ser em memoria ou porta interna;
- broker externo e outbox completa ficam fora do ciclo;
- eventos carregam versao e permitem idempotencia.

---

# 3. Regras de Negócio Relacionadas

- evento interno nao e fonte unica de verdade se o fato oficial vive em outro
  contexto;
- correlation ID acompanha a cadeia tecnica do evento.

---

# 4. Dependências

- FEATURE-036 - Preparar Eventos Internos e Projections;
- ADR-005 - Event Bus Interno e Eventos de Dominio;
- ADR-016 - Observability, Logging e Correlation ID.

---

# 5. Observações Técnicas

O PLAN deve evitar broker, fila externa ou outbox completa neste ciclo.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de eventos internos. |
