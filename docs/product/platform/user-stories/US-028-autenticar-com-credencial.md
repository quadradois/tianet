# US-028 — Autenticar com Credencial

**ID:** US-028

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Usuário operador do Tenant

**Quero** me autenticar apresentando meu e-mail e minha credencial

**Para** obter um token de acesso válido por 15 minutos e um refresh token válido por 7 dias, e assim operar a plataforma de forma segura e rastreável.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- um Usuário Ativo, com e-mail e credencial corretos, receber um token de acesso com validade de 15 minutos e um refresh token com validade de 7 dias;
- o token de acesso emitido for autocontido e verificável sem consulta ao banco (a autorização por Perfil utiliza o RBAC da FEATURE-011);
- o login exigir o identificador institucional do Tenant além do e-mail, permitindo a mesma identidade de e-mail em Tenants distintos sem ambiguidade;
- a credencial nunca for retornada na resposta nem persistida, trafegada ou auditada em texto legível — a comparação é feita sobre a forma armazenada (hash);
- Usuário com credencial incorreta receber 401, sem mensagem que revele qual dado estava errado;
- Usuário inexistente receber o mesmo 401 genérico, sem revelar se o e-mail existe na plataforma;
- Usuário em estado diferente de Ativo (Convidado, Inativo ou Removido) não autenticar e receber 401;
- cada tentativa de acesso — sucesso e falha — ser registrada na trilha de auditoria append-only (ADR-002);
- o Tenant e o Perfil resolvidos pelo token valerem para as requisições seguintes da mesma sessão.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): token de acesso curto e autocontido, Principal/RBAC corrente e refresh token persistido e revogável;
- ADR-001 — Stack Tecnológica Oficial do MVP: JWT (Bearer) + Refresh Token;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario (INV-001: todo Usuário pertence a exatamente um Tenant; apenas o estado Ativo autentica);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03): isolamento absoluto entre Tenants;
- FOUNDATION-009 — Capability Map: autorização por RBAC (Perfis e Permissões);
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- FEATURE-009 — Autenticar Usuário.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-009 — Autenticar Usuário;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario.

---

# 5. Observações Técnicas

A autenticação segue a ADR-004: a assinatura e a expiração do access token são verificáveis sem estado de Sessão, enquanto Tenant, Usuário e Perfil correntes são consultados ao resolver o Principal. O refresh token é persistido e revogável. A credencial nunca é armazenada ou auditada em texto legível. A identidade de login é composta pelo identificador institucional do Tenant e pelo e-mail; qualquer falha responde de forma uniforme, sem revelar qual componente existe.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Autenticar com Credencial. |
