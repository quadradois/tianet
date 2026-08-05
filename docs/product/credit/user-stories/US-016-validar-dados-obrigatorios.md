# US-016 — Validar Dados Obrigatórios do Devedor

**ID:** US-016

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** que os dados obrigatórios do Devedor sejam validados antes do cadastro

**Para** evitar o registro de devedores incompletos ou inconsistentes.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o nome do Devedor for obrigatório;
- o documento (CPF) for obrigatório e válido;
- ao menos um contato válido for obrigatório;
- dados inválidos retornarem 422 sem criar cadastro;
- a validação ocorrer antes de qualquer escrita.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-020 — Aggregate Devedor;
- DOMAIN-022 — Value Object Documento (VO-022-VAL-001/002);
- DOMAIN-021 — Entity Contato (RN-003);
- FEATURE-005 — Criar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- US-015 — Criar Devedor;
- FEATURE-005 — Criar Devedor.

---

# 5. Observações Técnicas

A validação de entrada pertence à Presentation (schemas Pydantic); as invariantes de negócio pertencem ao Domain (ex.: validade do CPF como Value Object).

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Validar Dados Obrigatórios do Devedor. |