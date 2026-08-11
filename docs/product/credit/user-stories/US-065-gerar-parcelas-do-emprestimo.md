# US-065 - Gerar Parcelas do Emprestimo

**ID:** US-065

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** operador autorizado de credito,
**quero** gerar Parcelas para um Emprestimo,
**para** acompanhar vencimentos e obrigacoes financeiras.

---

# 2. Critérios de Aceitação

- Parcelas sao geradas somente para Emprestimo valido;
- cada Parcela possui vencimento, valor previsto e estado;
- o plano de Parcelas possui memoria de calculo inicial;
- valores monetarios usam `Decimal`.

---

# 3. Regras de Negócio Relacionadas

- Parcelas pertencem a um Emprestimo;
- valores monetarios usam `Decimal`.

---

# 4. Dependências

- FEATURE-024 - Gerar Plano de Parcelas;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Plano inicial deve produzir memoria de calculo reproduzivel.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Gerar Parcelas do Emprestimo. |
