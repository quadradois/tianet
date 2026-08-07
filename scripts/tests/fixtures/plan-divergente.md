# PLAN-901 — Fixture: plano com prefixo divergente

Idêntico ao plan-ok, exceto pelo bounded context: `/platform` em vez de
`/credit`. Serve ao CA-004 — mudança de prefixo deve ser detectada, ao contrário
da mudança de placeholder (CA-003), que não é divergência.

**Versão:** 1.0.0

---

# 6. API

- `POST /platform/carteiras/{carteira_id}/devedores` — criação (201);
- `GET /platform/carteiras/{carteira_id}/devedores/{id}` — consulta por ID.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Fixture — plano sob bounded context distinto. |
