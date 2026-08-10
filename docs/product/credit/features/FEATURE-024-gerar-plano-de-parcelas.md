# FEATURE-024 - Gerar Plano de Parcelas

**ID:** FEATURE-024

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. Objetivo

Gerar o plano de Parcelas do Emprestimo usando parametros financeiros
rastreaveis, datas reais e memoria de calculo inicial.

---

# 2. Valor de Negócio

Permite que o credor acompanhe vencimentos e obrigacoes com base em regra
financeira reproduzivel.

---

# 3. Escopo

- gerar Parcelas previstas;
- calcular vencimentos;
- registrar periodo financeiro de cada Parcela;
- manter valores monetarios com `Decimal`;
- impedir uso de `float` ou periodo fixo implicito.

---

---

# 4. Fora do Escopo

- registrar pagamentos;
- quitar Emprestimo;
- executar cobranca ativa.

---

# 5. User Stories

- US-065 - Gerar Parcelas do Emprestimo;
- US-066 - Validar Periodos Financeiros Reais.

---

# 6. Dependências

- FEATURE-023 - Criar Emprestimo a partir de Contrato Liberado;
- DOMAIN-005 - Entity Parcela;
- DOMAIN-007 - VO Dinheiro.

---

# 7. Critérios de Aprovação

- Parcelas sao geradas apenas para Emprestimo valido;
- valores monetarios usam `Decimal`;
- datas de vencimento e periodo financeiro ficam explicitos;
- memoria de calculo inicial permite reproduzir o plano.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Gerar Plano de Parcelas. |
