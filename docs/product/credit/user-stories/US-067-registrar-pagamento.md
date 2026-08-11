# US-067 - Registrar Pagamento

**ID:** US-067

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** operador autorizado de credito,
**quero** registrar um Pagamento recebido,
**para** atualizar a situacao financeira da operacao.

---

# 2. Critérios de Aceitação

- Pagamento possui valor maior que zero;
- Pagamento pertence a um Emprestimo;
- Pagamento e processado pelo Motor antes de alterar saldo;
- Pagamento duplicado nao altera a operacao duas vezes;
- evento `PagamentoRegistrado` e publicado.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-025 - Registrar Pagamento;
- DOMAIN-006 - Entity Pagamento;
- DOMAIN-015 - Business Rule Pagamento nao pode ser negativo.

---

# 4. Dependências

- FEATURE-025 - Registrar Pagamento;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Pagamento deve possuir estrategia de idempotencia antes de afetar saldo.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Registrar Pagamento. |
