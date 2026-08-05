# US-001 — Criar Tenant

**ID:** US-001

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** criar uma nova organização (Tenant)

**Para** disponibilizar um novo ambiente operacional na TiaNet de forma segura, isolada e pronta para utilização.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir informar os dados obrigatórios do Tenant;
- os dados forem validados antes da criação;
- a unicidade do Tenant for garantida;
- o Tenant for criado com sucesso;
- a Carteira padrão for criada automaticamente;
- o primeiro Usuário Administrador for criado automaticamente;
- o Usuário Administrador for associado ao Tenant;
- as configurações iniciais forem provisionadas;
- o processo for registrado para auditoria;
- o sistema confirmar a criação da organização.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuário;
- DOMAIN-019 — Toda Carteira pertence exatamente a um Tenant;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FEATURE-001 — Criar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- EPIC-001 — Gerenciar Tenant;
- PRODUCT-001 — Capability Administrar Plataforma.

---

# 5. Observações Técnicas

A implementação deverá tratar a criação do Tenant como um processo de provisionamento e não como um simples cadastro.

Todo o fluxo deverá ser executado de forma consistente, garantindo que a organização esteja pronta para operar ao final do processo.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da User Story Criar Tenant. |
