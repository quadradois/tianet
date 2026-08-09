# US-037 — Atribuir Perfil a Usuário

**ID:** US-037

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Administrador do Tenant

**Quero** atribuir, alterar ou remover o Perfil de Acesso de um Usuário do meu Tenant

**Para** decidir, de forma rastreável, o que cada Usuário pode executar na plataforma — com o RBAC sustentado por um Perfil real, e não por um campo de texto livre como o `perfil_acesso` atual, que guarda um único valor em uso ("administrador") sem estrutura de autorização.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir atribuir a um Usuário um Perfil do mesmo Tenant, validando que o Usuário e o Perfil pertencem ao mesmo Tenant do Administrador autenticado;
- a atribuição de um Perfil de outro Tenant, ou a um Usuário de outro Tenant, responder 404, sem revelar a existência do recurso (precedente da ADR-018);
- a atribuição de um Perfil inexistente no Tenant responder 404;
- a atribuição de um Perfil desativado responder 409, sem alterar o vínculo em vigor;
- a alteração da atribuição substituir o Perfil atual, e a remoção desvincular o Perfil do Usuário, preservando em auditoria o histórico de atribuições anterior;
- requisição sem token válido responder 401; Usuário autenticado sem permissão de gerir Perfis responder 403;
- toda operação de escrita exigir Idempotency-Key e o evento de atribuição, alteração ou remoção de Perfil ser registrado por sessão independente na trilha de auditoria append-only;
- o campo de texto livre `perfil_acesso` deixar de ser fonte da autorização, com o vínculo passando a referenciar um Perfil real.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): RBAC por Perfil corrente e IAM no Platform Context;
- DOMAIN-017 — Aggregate Tenant (todo Perfil e todo Usuário pertencem a exatamente um Tenant);
- DOMAIN-018 — Entity Usuario (INV-001: Usuário pertence a exatamente um Tenant; a atribuição de Perfil ocorre dentro do Tenant);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03: isolamento absoluto entre Tenants);
- PRODUCT-001 — Capability Administrar Plataforma (o IAM é o EPIC-006);
- EPIC-006 — Discovery IAM (UC-026 Atribuir Perfil a Usuário; `perfil_acesso` livre não é estrutura RBAC);
- FEATURE-011 — Gerir Perfis e Permissões.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-011 — Gerir Perfis e Permissões;
- US-005 — Criar Usuário Administrador (o Perfil é atribuído a Usuários do Tenant);
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM).

---

# 5. Observações Técnicas

O campo legado `perfil_acesso` deixa de ser fonte de autorização. A atribuição referencia um Perfil real em `usuario_perfil`, resolvido a partir do Tenant do Principal autenticado. Atribuição, alteração e remoção são restritas a Usuário e Perfil do mesmo Tenant; Perfil inativo não pode ser atribuído. Toda escrita usa Idempotency-Key e o evento é registrado por sessão independente na trilha append-only, sobrevivendo ao rollback conforme ADR-002. A alteração do vínculo passa a valer na requisição seguinte porque o RBAC corrente é resolvido durante a autorização.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Atribuir Perfil a Usuário. |
