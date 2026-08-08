# US-002 — Validar Dados Obrigatórios

**ID:** US-002

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** que os dados obrigatórios sejam validados antes da criação da organização

**Para** impedir que um Tenant seja provisionado com informações incompletas ou inválidas.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- identificador institucional, nome, nome do administrador e e-mail do administrador forem obrigatórios;
- valores vazios ou compostos apenas de espaços forem rejeitados;
- o e-mail do administrador for validado quanto ao formato mínimo;
- a validação de fronteira ocorrer na camada Presentation e as invariantes permanecerem no Domain;
- dados inválidos impedirem a criação, sem persistir nenhum recurso parcial;
- a violação de invariante retornar resposta padronizada de regra violada.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-017 — Aggregate Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-001 — Criar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- US-001 — Criar Tenant.

---

# 5. Observações Técnicas

A validação de formato pertence ao DTO da camada Presentation; as invariantes do
Aggregate Tenant permanecem no Domain e são a fonte da verdade.

Nenhum recurso deverá ser persistido quando a validação falhar — a transação
única (AD-001) garante ausência de estado parcial.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Materialização da User Story, referenciada pela FEATURE-001 desde 01/08/2026 e implementada no EPIC-001. |
