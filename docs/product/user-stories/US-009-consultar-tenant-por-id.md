# US-009 — Consultar Tenant por ID

**ID:** US-009

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** consultar uma organização (Tenant) por seu identificador único

**Para** visualizar suas informações institucionais e seu estado operacional.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir consultar um Tenant por seu identificador único;
- apenas Tenants existentes puderem ser retornados;
- as informações retornadas corresponderem ao estado atual da organização;
- o resultado conter apenas os dados definidos para consulta;
- nenhuma informação interna da infraestrutura for exposta;
- a operação não alterar qualquer estado do domínio;
- o sistema retornar 404 quando o Tenant não existir;
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

A consulta deverá ser exclusivamente de leitura.

Nenhuma regra de negócio poderá ser executada durante a operação.

O Aggregate Tenant não deverá sofrer qualquer alteração de estado.

A resposta deverá utilizar DTO específico da camada Presentation.

O endpoint implementado durante a FEATURE-001 passa a ser oficialmente pertencente à FEATURE-002, não devendo existir duplicação de implementação.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 02/08/2026 | Primeira versão oficial da User Story Consultar Tenant por ID. |