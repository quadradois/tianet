# US-042 — Auditar Eventos de Acesso

**ID:** US-042

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Administrador do Tenant

**Quero** que cada evento de acesso do meu Tenant — autenticação bem-sucedida, tentativa recusada, autorização negada e encerramento de sessão — seja registrado na trilha de auditoria

**Para** verificar quem acessou a plataforma e quando, e detectar tentativas de acesso indevido, sem que a própria auditoria seja alterável ou vaze existência de recursos.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- cada autenticação bem-sucedida gerar um registro na trilha de auditoria, com o identificador do Usuário autenticado e do respectivo Tenant;
- cada tentativa de autenticação recusada gerar um registro na trilha, sem que a resposta e o registro indiquem se o identificador informado existia;
- cada autorização negada (resposta 403, por Perfil) e cada acesso a recurso de outro Tenant (resposta 404) gerarem um registro na trilha, sem revelar a existência do recurso;
- cada encerramento de sessão (logout) gerar um registro na trilha de auditoria;
- consultas de leitura — como consultar Devedor ou listar — não gerarem registros na trilha de acesso;
- a trilha de auditoria ser append-only, registrada em sessão independente que sobrevive a rollback, e nenhuma operação do sistema apagar ou alterar registros já gravados;
- credencial de acesso nunca ser gravada, em texto legível ou de qualquer forma recuperável, na trilha de auditoria.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): validade do token de acesso de 15 minutos, RBAC por Perfil, contrato de erro 401/403/404;
- ADR-002 — Auditoria Independente da Transação (trilha append-only em sessão própria);
- DOMAIN-017 — Aggregate Tenant (isolamento da entidade);
- DOMAIN-018 — Entity Usuario (INV-001 — todo Usuário pertence a exatamente um Tenant);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03, isolamento absoluto entre Tenants);
- PRODUCT-001 — IAM é a capability da plataforma;
- EPIC-006 — Discovery do IAM (eventos de acesso auditados na trilha append-only);
- FEATURE-012 — Autorizar Requisição.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-012 — Autorizar Requisição;
- EPIC-006 — Autenticação e Controle de Acesso (IAM);
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-002 — Auditoria Independente da Transação (infraestrutura existente).

---

# 5. Observações Técnicas

A auditoria de acesso usa a trilha append-only existente (ADR-002), gravada em sessão independente que sobrevive a rollback da operação. Os registros usam o mesmo padrão de eventos de início, sucesso e falha adotado nos fluxos atuais do EPIC-001. A decisão de não auditar consultas de leitura mantém a trilha enxuta e direcionada a eventos que mudam o ciclo de segurança. O registro nunca inclui o conteúdo da credencial; identifica o Principal (Usuário e Tenant) e o resultado da tentativa.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Auditar Eventos de Acesso. |
