# PLAN-900 — Fixture: plano coerente

**Versão:** 1.0.0

---

# 6. API

- `POST /credit/carteiras/{carteira_id}/devedores` — criação (201);
- `GET /credit/carteiras/{carteira_id}/devedores/{id}` — consulta por ID;
- `PATCH /credit/carteiras/{carteira_id}/devedores/{id}` — atualização;
- `POST /credit/carteiras/{carteira_id}/devedores/{id}/inativar` — transição.

Padrões de erro: 400 payload_invalido / 404 devedor_nao_encontrado / 422 regra_violada.

# 7. Estratégia de Testes

Nada aqui deve ser lido como endpoint.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Fixture — plano coerente. Cita GET `/devedores/{id}`, rota antiga, apenas no histórico. |
