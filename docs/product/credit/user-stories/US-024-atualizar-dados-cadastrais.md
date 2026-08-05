# US-024 — Atualizar Dados Cadastrais do Devedor

**ID:** US-024

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** atualizar os dados cadastrais do Devedor

**Para** manter o cadastro preciso e o contato com o tomador atualizado.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o nome do Devedor puder ser atualizado;
- contatos puderem ser adicionados, alterados e removidos;
- o contato preferencial puder ser alterado;
- o documento e o vínculo com a Carteira permanecerem imutáveis;
- Devedor inexistente retornar 404;
- a alteração for registrada para auditoria.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-020 — Aggregate Devedor (INV-003);
- DOMAIN-021 — Entity Contato;
- DOMAIN-022 — Value Object Documento (imutabilidade);
- ADR-002 — Auditoria Independente da Transação;
- FEATURE-007 — Atualizar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-007 — Atualizar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

PATCH parcial (padrão EPIC-001 — PATCH /platform/tenants/{id}, IMP-032): apenas campos informados são atualizados; resposta com DTO único do Devedor.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Atualizar Dados Cadastrais do Devedor. |