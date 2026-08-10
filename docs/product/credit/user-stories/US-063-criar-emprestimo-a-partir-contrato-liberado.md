# US-063 - Criar Emprestimo a partir de Contrato Liberado

**ID:** US-063

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** operador autorizado de credito,
**quero** criar um Emprestimo a partir de um contrato liberado,
**para** iniciar a operacao financeira com rastreabilidade formal.

---

# 2. Critérios de Aceitação

- dado um `ContratoLiberadoLogico` valido, quando o Motor criar a operacao,
  entao um Emprestimo sera registrado;
- o Emprestimo preserva Tenant, Carteira, Devedor, Contrato e parametros
  congelados;
- o evento `EmprestimoCriado` e publicado;
- a criacao e auditada.

---

# 3. Regras de Negócio Relacionadas

- Emprestimo nasce somente de `ContratoLiberadoLogico`;
- Motor Financeiro e a unica autoridade de criacao da operacao financeira.

---

# 4. Dependências

- FEATURE-023 - Criar Emprestimo a partir de Contrato Liberado;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Criacao deve ser idempotente por contrato liberado.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Criar Emprestimo a partir de Contrato Liberado. |
