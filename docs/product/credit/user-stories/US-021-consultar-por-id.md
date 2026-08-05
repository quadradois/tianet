# US-021 — Consultar Devedor por ID

**ID:** US-021

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** consultar um Devedor pelo seu ID

**Para** obter os dados cadastrais e o estado atual do cadastro de forma rápida e isolada.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema retornar os dados cadastrais do Devedor a partir do ID;
- ID inexistente retornar 404;
- a consulta for exclusivamente de leitura (sem efeitos colaterais);
- o isolamento por Carteira/Tenant for preservado;
- a resposta utilizar o DTO único, sem dados internos.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-020 — Aggregate Devedor (INV-006);
- FEATURE-006 — Consultar Devedor;
- ADR-002 — leitura não auditada.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-006 — Consultar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

Consulta mediada pela Carteira do Tenant do usuário (FOUNDATION-006 Princípio 02/03): o ID é resolvido dentro da Carteira, nunca de forma global.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Consultar Devedor por ID. |