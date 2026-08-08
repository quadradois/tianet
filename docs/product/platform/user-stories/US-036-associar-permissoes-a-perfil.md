# US-036 — Associar Permissões a Perfil

**ID:** US-036

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Administrador do Tenant

**Quero** definir quais Permissões cada Perfil concede, associando e removendo Permissões de um Perfil do meu Tenant

**Para** autorizar, por Perfil, o que cada Usuário pode executar — como cadastrar ou inativar um Devedor — sem depender de ajuste individual e com efeito nas próximas autorizações.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir associar uma Permissão do catálogo de operações a um Perfil ativo do Tenant, com validade restrita ao Tenant do Administrador autenticado;
- a associação de Permissão inexistente ou fora do catálogo de operações do sistema ser recusada com 422 (violação de regra de domínio);
- a associação repetida da mesma Permissão ao mesmo Perfil não gerar duplicidade — a configuração é tratada como conjunto e o resultado da nova associação é o mesmo estado já existente;
- o sistema permitir remover uma Permissão de um Perfil, e a nova configuração passar a valer nas próximas autorizações;
- a tentativa de associar ou remover Permissão de um Perfil desativado retornar 409, sem alterar a configuração do Perfil;
- requisição sem token válido responder 401; Usuário autenticado sem permissão para gerir Perfis responder 403; Perfil de outro Tenant responder 404, sem revelar a existência;
- toda operação de escrita exigir Idempotency-Key e cada associação ou remoção de Permissão ser registrada na trilha de auditoria, com efeito nas próximas autorizações dentro da janela de até 15 minutos do token de acesso.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): RBAC por Perfil, autorização decidida por permissão de operação, janela de revogação de até 15 minutos, IAM no Platform Context;
- DOMAIN-017 — Aggregate Tenant (todo Perfil pertence exatamente a um Tenant);
- DOMAIN-018 — Entity Usuario (INV-001: Usuário pertence a exatamente um Tenant; o Perfil é atribuído dentro do Tenant);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03: isolamento absoluto entre Tenants);
- PRODUCT-001 — Capability Administrar Plataforma (o IAM é o EPIC-006);
- EPIC-006 — Discovery IAM (Linguagem Ubíqua: Perfil de Acesso e Permissão; isolamento por Tenant);
- FEATURE-011 — Gerir Perfis e Permissões.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-011 — Gerir Perfis e Permissões;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM).

---

# 5. Observações Técnicas

A Permissão identifica uma operação do sistema (ex.: cadastrar devedor, inativar devedor), e não um recurso individual — a decisão de autorização é por operação, conforme o RBAC fixado na ADR-004. O catálogo de Permissões é conhecido e estável, referenciado por identificador; a associação de Perfil e Permissão é um vínculo de muitos-para-muitos dentro do Platform Context. A alteração da configuração passa a valer nas próximas autorizações: como o token de acesso é curto, autocontido e verificável sem consulta ao banco, a janela de revogação de até 15 minutos fixada na ADR-004 é o limite para a nova configuração refletir sem nova autenticação. Operações de escrita usam Idempotency-Key e os eventos de associação e remoção são registrados na trilha de auditoria append-only (ADR-002), na mesma transação do caso de uso. Requisições autenticadas resolvem o Tenant do Principal; Perfil de outro Tenant é tratado como inexistente, respondendo 404 sem revelar a existência.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Associar Permissões a Perfil. |