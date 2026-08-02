# US-011 — Listar Tenants

**ID:** US-011

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** listar as organizações (Tenants) cadastradas

**Para** localizar rapidamente uma organização e iniciar sua administração.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir listar os Tenants cadastrados;
- a listagem utilizar paginação;
- a ordenação da resposta for determinística;
- o sistema permitir filtrar pelo estado do Tenant;
- o sistema permitir pesquisar pelo identificador institucional;
- apenas as informações definidas para listagem forem retornadas;
- nenhuma informação interna da infraestrutura for exposta;
- a operação não alterar qualquer estado do domínio;
- a resposta seguir o contrato oficial da API.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-017 — Aggregate Tenant;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-002 — Consultar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- FEATURE-002 — Consultar Tenant.

---

# 5. Observações Técnicas

A listagem deverá utilizar paginação desde a primeira versão.

A ordenação deverá ser determinística para garantir estabilidade entre páginas.

Os filtros deverão ser executados pela camada de Application.

A resposta deverá utilizar DTO específico da camada Presentation.

Nenhuma regra de negócio poderá ser executada durante a operação.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 02/08/2026 | Primeira versão oficial da User Story Listar Tenants. |
