# US-027 — Consultar Histórico Cadastral do Devedor

**ID:** US-027

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** consultar o histórico cadastral do Devedor

**Para** reconstituir todas as alterações realizadas no cadastro ao longo do tempo.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a consulta retornar a trilha de auditoria do cadastro (criação e alterações);
- cada evento da trilha indicar origem, data e estado;
- apenas o histórico da Carteira do Tenant for retornado;
- Devedor inexistente retornar 404;
- a consulta for exclusivamente de leitura.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-020 — Aggregate Devedor (INV-004);
- FEATURE-006 — Consultar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-006 — Consultar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

O histórico é lido da trilha append-only (SqlAlchemyAuditoriaRegistro) já existente (ADR-002), filtrada por entidade (Devedor) e Carteira.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Consultar Histórico Cadastral do Devedor. |