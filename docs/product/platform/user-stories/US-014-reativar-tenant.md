# US-014 — Reativar Tenant

**ID:** US-014

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** reativar uma organização (Tenant)

**Para** permitir que ela volte a operar normalmente na plataforma preservando todo o seu histórico.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- apenas Tenants em estado **Inativo** puderem ser reativados;
- a operação alterar apenas o estado operacional do Tenant;
- nenhuma informação da organização for removida ou recriada;
- a máquina de estados oficial do Aggregate Tenant for respeitada;
- a infraestrutura oficial de auditoria registrar a operação;
- o sistema retornar o novo estado da organização;
- nenhuma regra de negócio for executada fora do Domain;
- a resposta utilizar DTO específico da camada Presentation.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-017 — Aggregate Tenant;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-004 — Inativar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- FEATURE-002 — Consultar Tenant;
- FEATURE-003 — Atualizar Tenant;
- FEATURE-004 — Inativar Tenant.

---

# 5. Observações Técnicas

A operação deverá representar exclusivamente uma mudança de estado do Aggregate Tenant.

Nenhum dado deverá ser recriado durante a reativação.

A auditoria deverá utilizar a infraestrutura transversal definida na ADR-002.

A resposta deverá utilizar DTO específico da camada Presentation.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 02/08/2026 | Primeira versão oficial da User Story Reativar Tenant. |
