# PLAN-900 — Fixture: backlog coerente

**Versão:** 1.0.0

---

# 5. API — Presentation

## IMP-900 — Endpoint POST /credit/carteiras/{carteira_id}/devedores

- **Objetivo:** criação de Devedor na Carteira (201).
- **Critérios de conclusão:** 201 com DevedorResponse; 404; 422.

## IMP-901 — Endpoints de consulta

- **Objetivo:** GET `/carteiras/{carteira_id}/devedores/{id}` — o prefixo do
  bounded context está omitido de propósito: é o mesmo endpoint do plano.
- **Critérios de conclusão:** 200; 404 devedor_nao_encontrado.

## IMP-902 — Atualização e estado

- **Objetivo:** PATCH `/carteiras/{carteira_id}/devedores/{id}` e POST
  `/carteiras/{carteira_id}/devedores/{id}/inativar` (400/422).

> Nota: nenhuma rota oficial em `/devedores/{id}`. Esta linha é citação e não
> deve ser lida como declaração de endpoint.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Fixture — backlog coerente com o plano, com PATCH `/devedores/{id}` citado só aqui. |
