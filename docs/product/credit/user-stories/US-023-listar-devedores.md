# US-023 — Listar Devedores

**ID:** US-023

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** listar os Devedores da minha Carteira

**Para** visualizar o conjunto de cadastros com paginação, ordenação e filtros.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a listagem for paginada com parâmetros de página e tamanho;
- a ordenação for determinística;
- filtros opcionais por nome, documento e estado forem suportados;
- apenas Devedores da Carteira do Tenant forem retornados;
- a resposta utilizar o DTO único e sem dados internos;
- a listagem não gerar trilha de auditoria (leitura).

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-020 — Aggregate Devedor (estados operacionais oficiais);
- FEATURE-006 — Consultar Devedor;
- ADR-002 — leitura não auditada;
- FOUNDATION-006 — isolamento multi-tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-006 — Consultar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

Mesmo padrão da listagem de Tenants do EPIC-001 (FEATURE-002 IMP-026/027): paginação obrigatória, ordenação determinística por criado_em + id, DTO único.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Listar Devedores. |