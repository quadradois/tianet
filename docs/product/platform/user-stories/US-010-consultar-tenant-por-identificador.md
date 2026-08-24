# US-010 — Consultar Tenant por Identificador Institucional

**ID:** US-010

**Versão:** 1.1.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** consultar um Credor (Tenant) utilizando seu identificador institucional

**Para** localizar rapidamente uma organização sem conhecer seu identificador interno.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir consultar um Tenant pelo identificador institucional;
- apenas um Tenant puder ser retornado para cada identificador;
- a busca respeitar a unicidade definida pelo domínio;
- o resultado retornar apenas as informações previstas para consulta;
- nenhuma informação interna da infraestrutura for exposta;
- a operação não alterar qualquer estado do domínio;
- o sistema retornar 404 quando o identificador não existir;
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

O identificador institucional deverá ser tratado como único dentro da plataforma.

Nenhuma regra de negócio poderá ser executada durante a operação.

O Aggregate Tenant não deverá sofrer qualquer alteração de estado.

A resposta deverá utilizar DTO específico da camada Presentation.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.1.0 | 23/08/2026 | Tenant descrito como Credor, nao como organizacao, conforme FOUNDATION-001 (IMP-338). |
| 1.0.0 | 02/08/2026 | Primeira versão oficial da User Story Consultar Tenant por Identificador Institucional. |
