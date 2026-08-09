# US-034 — Redefinir Credencial de Usuário

**ID:** US-034

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Usuário do Tenant com permissão de redefinir credencial (RBAC)

**Quero** redefinir a credencial de outro Usuário do mesmo Tenant

**Para** restaurar o acesso de um Usuário que perdeu ou teve a credencial comprometida, revogando de imediato os refresh tokens existentes e limitando o impacto a uma janela de até 15 minutos.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a redefinição somente for aceita para um Usuário autenticado (estado Ativo) com a permissão de redefinir credencial — sem token válido a requisição responder 401 e, com token válido, sem permissão, responder 403;
- a redefinição operar exclusivamente sobre Usuário do mesmo Tenant do solicitante — Usuário de outro Tenant responder 404, sem jamais revelar a existência do recurso (precedente da ADR-018);
- Usuário inexistente responder 404, indistinguível da recusa por outro Tenant;
- a redefinição revogar todos os refresh tokens do Usuário afetado, de modo que o acesso anterior cesse na janela de até 15 minutos (validade do token de acesso da ADR-004);
- após a redefinição, a credencial anterior deixar de autenticar e apenas a nova credencial estabelecer uma nova sessão;
- a credencial nova nunca for armazenada, trafegada ou auditada em texto legível — a credencial não é recuperável, apenas redefinível;
- a operação não alterar o estado do Usuário afetado;
- a redefinição for registrada para auditoria na trilha append-only (ADR-002), registrando quem executou a operação.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): token de acesso curto e autocontido, refresh token persistido e revogável, validade de 15 minutos como janela de revogação, RBAC e IAM no Platform Context;
- ADR-018 — precedente de não revelar existência de recurso de outro Tenant (404);
- DOMAIN-017 — Aggregate Tenant: todo Usuário pertence a exatamente um Tenant (INV-001); nenhum acesso cruza a fronteira de Tenant;
- DOMAIN-018 — Entity Usuario: apenas o estado Ativo autentica (RN relacionada), ciclo de vida Convidado → Ativo → Inativo → Removido;
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03): isolamento absoluto entre Tenants;
- FOUNDATION-009 — Capability Map: autorização por RBAC (Perfis e Permissões);
- ADR-002 — Auditoria Independente da Transação;
- FEATURE-010 — Gerir Credenciais (User Story US-034);
- EPIC-006 — IAM (Identidade e Controle de Acesso): credencial não recuperável, apenas redefinível;
- PRODUCT-001 — Capability Administrar Plataforma.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-010 — Gerir Credenciais
- EPIC-006 — IAM (Identidade e Controle de Acesso)
- PRODUCT-001 — Capability Administrar Plataforma
- ADR-004 — Autenticação e Autorização (IAM)
- ADR-002 — Auditoria Independente da Transação
- ADR-001 — Stack Tecnológica Oficial do MVP
- DOMAIN-017 — Aggregate Tenant
- DOMAIN-018 — Entity Usuario

---

# 5. Observações Técnicas

A redefinição é uma ação administrativa que executa em transação única e articula o contrato de autenticação da ADR-004: como o token de acesso é curto e sem estado, revogar os refresh tokens do Usuário afetado não corta sessões ativas de imediato — o acesso cessa na próxima renovação, no pior caso dentro da janela de 15 minutos, que é aceita e documentada. A credencial é tratada como dado de segurança de ponta a ponta: capturada uma única vez no sentido de escrita, nunca lida, reproduzida ou devolvida em resposta, e seus eventos são registrados na trilha append-only (ADR-002). A autorização da operação segue o RBAC do Perfil do solicitante (FEATURE-011), e a verificação de pertinência ao Tenant resolve o Usuário alvo a partir do Principal — qualquer recusa responde 404, indistinguível entre inexistência e outro Tenant (FOUNDATION-006, precedente da ADR-018).

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Redefinir Credencial de Usuário, criada no ciclo SDD do EPIC-006. |
