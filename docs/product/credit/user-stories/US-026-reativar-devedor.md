# US-026 — Reativar Devedor

**ID:** US-026

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** reativar um Devedor Inativo

**Para** restabelecer a elegibilidade do cadastro para novas operações.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a transição Inativo → Ativo for executada;
- a unicidade do documento for revalidada na Carteira;
- Devedor inexistente retornar 404;
- Devedor já ativo retornar 409 (estado divergente);
- a reativação for registrada para auditoria.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-020 — Aggregate Devedor (INV-005);
- DOMAIN-024 — Business Rule Documento Único por Carteira (reativação);
- FEATURE-008 — Inativar/Reativar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-008 — Inativar/Reativar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

A reativação reutiliza a validação de unicidade (DOMAIN-023) para impedir conflito de documento com outro cadastro na mesma Carteira (em qualquer estado — DOMAIN-024 §4).

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Reativar Devedor. |