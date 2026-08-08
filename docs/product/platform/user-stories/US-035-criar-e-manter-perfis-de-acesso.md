# US-035 — Criar e Manter Perfis de Acesso

**ID:** US-035

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Administrador do Tenant

**Quero** criar, renomear e desativar Perfis de Acesso dentro do meu Tenant

**Para** controlar o que cada Usuário pode executar na plataforma, com nomes claros e vínculos auditáveis, sem que um Perfil em uso seja descartado sem tratamento.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir criar um Perfil informando um nome, com validade restrita ao Tenant do Administrador autenticado;
- a criação de Perfil com nome já existente no mesmo Tenant retornar 409 (conflito de unicidade);
- o Perfil com nome vazio, apenas espaços ou fora do limite de tamanho for recusado com 422 (violação de regra de domínio);
- o sistema permitir renomear um Perfil existente, mantendo a unicidade do nome dentro do Tenant;
- um Perfil sem Usuários vinculados puder ser desativado; um Perfil desativado não puder ser atribuído a novos Usuários;
- a tentativa de desativar um Perfil com ao menos um Usuário vinculado no Tenant retornar 409, sem alterar o estado do Perfil;
- requisição sem token válido responder 401; Usuário autenticado sem permissão de gerir Perfis responder 403; Perfil de outro Tenant responder 404, sem revelar a existência;
- toda operação de escrita exigir Idempotency-Key e o evento de criação, renomeação ou desativação ser registrado na trilha de auditoria.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): RBAC por Perfil, IAM no Platform Context, janela de revogação de até 15 minutos;
- DOMAIN-017 — Aggregate Tenant (todo Perfil pertence a exatamente um Tenant);
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

O Perfil de Acesso é um artefato do Platform Context, ao lado de Tenant e Usuário (ADR-004). A unicidade do nome é garantida dentro de cada Tenant. A desativação é lógica: o estado Inativo preserva o histórico de atribuições e conversa a analogia ao ciclo de vida do Usuário (DOMAIN-018). Um Perfil desativado deixa de autorizar novas operações dentro da janela de revogação de até 15 minutos do token de acesso, conforme fixado na ADR-004. Operações de escrita usam Idempotency-Key e os eventos são registrados na trilha de auditoria append-only (ADR-002), na mesma transação do caso de uso. Requisições autenticadas resolvem o Tenant do Principal; acesso a Perfil de outro Tenant é negado respondendo 404, sem revelar a existência.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Criar e Manter Perfis de Acesso. |