# US-025 — Inativar Devedor

**ID:** US-025

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** inativar um Devedor Ativo

**Para** encerrar a elegibilidade do cadastro para novas operações sem perder seu histórico.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a transição Ativo → Inativo for executada;
- o histórico cadastral e financeiro permanecer intacto;
- Devedor inexistente retornar 404;
- Devedor já inativo retornar 409 (estado divergente);
- a transição for registrada para auditoria.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-020 — Aggregate Devedor (INV-005, RN-005/RN-006);
- DOMAIN-025 — Business Rule Exclusão Física Proibida;
- FEATURE-008 — Inativar/Reativar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-008 — Inativar/Reativar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

Mesmo padrão do EPIC-001 (IMP-033..036): transição no Domain, Application traduz violação de invariante em 409 `conflito_estado`, auditoria nos eventos inicio/sucesso/falha.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Inativar Devedor. |