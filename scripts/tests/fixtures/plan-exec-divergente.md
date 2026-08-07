# PLAN-900 — Fixture: backlog divergente

Reproduz o defeito real que originou a DR-001: o backlog declara o recurso em
forma plana enquanto o plano o declara aninhado sob a Carteira.

**Versão:** 1.0.0

---

# 5. API — Presentation

## IMP-900 — Endpoint POST /credit/carteiras/{carteira_id}/devedores

- **Objetivo:** criação de Devedor na Carteira (201).

## IMP-901 — Endpoints de consulta

- **Objetivo:** GET `/devedores/{id}` — DIVERGENTE: forma plana, o plano exige
  o caminho aninhado sob a Carteira.

## IMP-902 — Endpoint fora do plano

- **Objetivo:** DELETE `/credit/carteiras/{carteira_id}/devedores/{id}` — escopo
  que entrou pela execução sem passar pelo planejamento (regra 1.3).

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Fixture — backlog divergente do plano. |
