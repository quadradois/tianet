# US-012 — Atualizar Dados Cadastrais do Tenant

**ID:** US-012

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** atualizar os dados cadastrais permitidos de uma organização (Tenant)

**Para** manter suas informações institucionais corretas e atualizadas durante todo o seu ciclo de vida.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir atualizar apenas os atributos permitidos do Tenant;
- a operação utilizar PATCH como contrato principal;
- o identificador institucional permanecer imutável;
- as invariantes do Aggregate Tenant forem preservadas;
- os dados atualizados forem validados antes da persistência;
- a infraestrutura oficial de auditoria registrar a operação;
- a resposta retornar o estado atualizado da organização;
- nenhuma regra de negócio for executada fora do Domain;
- a resposta utilizar DTO específico da camada Presentation.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-017 — Aggregate Tenant;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-003 — Atualizar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- FEATURE-002 — Consultar Tenant;
- FEATURE-003 — Atualizar Tenant.

---

# 5. Observações Técnicas

A atualização deverá ocorrer exclusivamente sobre os atributos explicitamente enviados na requisição.

O Aggregate Tenant deverá continuar sendo o responsável pela proteção de todas as invariantes do domínio.

A auditoria deverá utilizar a infraestrutura transversal definida na ADR-002.

A resposta deverá utilizar DTO específico da camada Presentation.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 02/08/2026 | Primeira versão oficial da User Story Atualizar Dados Cadastrais do Tenant. |
