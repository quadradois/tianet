# US-064 - Impedir Emprestimo sem Contrato Liberado

**ID:** US-064

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** responsavel pela governanca financeira,
**quero** impedir Emprestimo sem contrato liberado,
**para** evitar operacao financeira sem origem formal.

---

# 2. Critérios de Aceitação

- contrato inexistente ou de outro Tenant responde 404 logico;
- contrato nao liberado nao cria Emprestimo;
- contrato ja consumido nao cria segundo Emprestimo ativo;
- a tentativa recusada nao altera fatos financeiros.

---

# 3. Regras de Negócio Relacionadas

- Emprestimo sem contrato liberado e proibido;
- recurso cross-tenant deve ser indistinguivel de inexistente.

---

# 4. Dependências

- FEATURE-023 - Criar Emprestimo a partir de Contrato Liberado;
- EPIC-004 - Contratos de Credito;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Contrato ja consumido deve ser tratado por idempotencia ou conflito documentado.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Impedir Emprestimo sem Contrato Liberado. |
