# US-022 — Consultar Devedor por Documento

**ID:** US-022

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** consultar um Devedor pelo documento (CPF)

**Para** circular o cadastro por um dado humano e estável, integrando sistemas externos sem depender do ID interno.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema retornar o Devedor a partir do documento (normalizado, apenas dígitos);
- documento inexistente retornar 404;
- a unicidade do documento garantir no máximo um resultado;
- o isolamento por Carteira/Tenant for preservado;
- a consulta utilizar o DTO único e sem expor dados internos.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-022 — Value Object Documento;
- DOMAIN-024 — Business Rule Documento Único por Carteira;
- FEATURE-006 — Consultar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-006 — Consultar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

A busca por documento é normalizada (somente dígitos) e indexada pela constraint UNIQUE da Carteira (DOMAIN-024), respeitando o isolamento multi-tenant.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Consultar Devedor por Documento. |