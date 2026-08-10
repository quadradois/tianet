# FEATURE-025 - Registrar Pagamento

**ID:** FEATURE-025

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. Objetivo

Registrar Pagamentos recebidos e processa-los pelo Motor Financeiro antes de
alterar saldo, Parcelas ou estado do Emprestimo.

---

# 2. Valor de Negócio

Mantem a posicao financeira da operacao correta apos recebimentos, com
distribuicao auditavel e sem duplicidade.

---

# 3. Escopo

- receber Pagamento;
- validar valor positivo;
- aplicar chave idempotente quando disponivel;
- distribuir pagamento entre juros, encargos e amortizacao;
- atualizar fatos financeiros;
- registrar memoria de calculo e auditoria.

---

---

# 4. Fora do Escopo

- conciliacao bancaria externa;
- emissao de boleto ou PIX;
- cobranca ativa.

---

# 5. User Stories

- US-067 - Registrar Pagamento;
- US-068 - Priorizar Juros antes da Amortizacao.

---

# 6. Dependências

- FEATURE-024 - Gerar Plano de Parcelas;
- DOMAIN-006 - Entity Pagamento;
- DOMAIN-015 - Business Rule Pagamento nao pode ser negativo.

---

# 7. Critérios de Aprovação

- pagamento sem Emprestimo valido nao e aceito;
- valor zero ou negativo e recusado;
- pagamento duplicado nao altera saldo duas vezes;
- distribuicao financeira e feita pelo Motor;
- memoria de calculo registra a distribuicao.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Registrar Pagamento. |
