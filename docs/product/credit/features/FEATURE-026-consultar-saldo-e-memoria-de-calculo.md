# FEATURE-026 - Consultar Saldo e Memoria de Calculo

**ID:** FEATURE-026

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. Objetivo

Consultar saldo devedor, posicao financeira e memoria de calculo de um
Emprestimo em data de referencia.

---

# 2. Valor de Negócio

Dá transparencia operacional e auditabilidade para explicar valores financeiros
sem duplicar calculo em outros contextos.

---

# 3. Escopo

- consultar saldo devedor;
- consultar juros e amortizacoes aplicadas;
- consultar memoria de calculo;
- informar data de referencia;
- proteger dados por Tenant/Carteira/RBAC.

---

---

# 4. Fora do Escopo

- recalculo em relatorios;
- comunicacao com devedor;
- definicao de politica de cobranca.

---

# 5. User Stories

- US-069 - Consultar Saldo Devedor;
- US-070 - Consultar Memoria de Calculo.

---

# 6. Dependências

- FEATURE-025 - Registrar Pagamento;
- DOMAIN-010 - Service Motor Financeiro.

---

# 7. Critérios de Aprovação

- saldo vem do Motor Financeiro;
- memoria possui entradas, regra, periodo e resultado;
- recurso de outro Tenant responde 404;
- usuario sem permissao recebe 403.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Consultar Saldo e Memoria de Calculo. |
