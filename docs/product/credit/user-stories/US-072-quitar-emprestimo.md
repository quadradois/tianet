# US-072 - Quitar Emprestimo

**ID:** US-072

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** operador autorizado de credito,
**quero** quitar um Emprestimo,
**para** encerrar a obrigacao financeira quando o valor devido for liquidado.

---

# 2. Critérios de Aceitação

- quitacao usa valor calculado pelo Motor;
- Emprestimo quitado publica evento `EmprestimoQuitado`;
- Emprestimo quitado nao recebe novos Pagamentos;
- a quitacao e auditada e possui memoria de calculo;
- replay com mesma `Idempotency-Key` e mesmo payload retorna o resultado original;
- replay com mesma `Idempotency-Key` e payload divergente responde conflito.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-027 - Quitar e Renegociar Operacao;
- DOMAIN-013 - Domain Event Emprestimo Quitado;
- DOMAIN-016 - Business Rule Emprestimo quitado nao recebe pagamentos.

---

# 4. Dependências

- FEATURE-027 - Quitar e Renegociar Operacao;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Quitacao deve publicar evento financeiro, registrar auditoria e usar
idempotencia transacional antes de alterar saldo ou estado.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-10 | Especifica contrato de idempotencia da quitacao. |
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Quitar Emprestimo. |
