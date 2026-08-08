# US-039 — Validar Token e Resolver Principal

**ID:** US-039

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Sistema

**Quero** validar o token de acesso apresentado em toda requisição a endpoint protegido — verificando assinatura e expiração — e resolver o Principal (Usuário e Tenant) a partir dele

**Para** garantir, de forma verificada (e não por disciplina), que nenhuma operação protegida execute sem um Principal autenticado, e que cada requisição carregue o Usuário e o Tenant que ela representa.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a validação do token de acesso verificar a assinatura e a expiração, sem consultar o banco de dados — o token é autocontido, conforme o desenho da ADR-004;
- o Principal (Usuário e Tenant) resolvido a partir do token validado for propagado a toda a requisição e às camadas subsequentes (Application, Domain e Infraestrutura);
- os 13 endpoints protegidos exigirem token de acesso válido, respondendo 401 sem token, com token malformado, com assinatura inválida ou expirado após os 15 minutos de validade;
- um token de acesso expirado (após 15 minutos) não conceder acesso, mesmo que a assinatura seja válida;
- o endpoint `/health` continuar acessível sem autenticação (o único dos 14 endpoints que permanece público);
- um Principal cujo Usuário não esteja no estado Ativo (Convidado, Inativo ou Removido) não obter acesso pelo token, respondendo 401;
- o Principal refletir o Tenant do Usuário autenticado, sem que a requisição possa escolher ou presumir outro Tenant — nenhum acesso cruza a fronteira de Tenant (FOUNDATION-006, Princípios 01-03);
- o token sem permissão para a operação que o recurso exige ser encaminhado à autorização por Perfil (RBAC, FEATURE-011), que responde 403 — sendo 403 a competência da US-040, e o 404 cross-tenant, da US-041.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): token de acesso curto, autocontido e verificável sem consulta ao banco, com validade de 15 minutos (a janela de revogação); IAM no Platform Context;
- DOMAIN-018 — Entity Usuario (INV-001: todo Usuário pertence a exatamente um Tenant; apenas o estado Ativo valida o acesso);
- DOMAIN-017 — Aggregate Tenant (o Principal carrega o Tenant resolvido do usuário);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03: isolamento absoluto entre Tenants — o acesso não cruza fronteira);
- PRODUCT-001 — Capability Administrar Plataforma (para a qual o IAM é o EPIC-006);
- EPIC-006 — Discovery IAM (UC-028 e §10 — Todo Principal autenticado carrega Tenant e Usuário resolvidos; nenhuma operação executa sem Principal em endpoint protegido);
- FEATURE-012 — Autorizar Requisição (esta US é parte dela: validar token e resolver o Principal).

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-012 — Autorizar Requisição;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM): o token de acesso é emitido pela autenticação (FEATURE-009) e validado aqui como autocontido;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario.

---

# 5. Observações Técnicas

A validação do token é um passo de segurança da fronteira (Presentation) que segue o desenho da ADR-004: o token de acesso é curto (15 minutos), autocontido e verificável por assinatura e expiração, sem consulta ao banco; o refresh persistido e revogável fica fora desta validação (pertence à FEATURE-009). O Principal resolvido (Usuário e Tenant) é propagado pela requisição e passa a ser fonte única do Tenant — o código nunca o presume da URL ou de corpos. A validação é independente da autorização: o 401 (sem token válido) é decidido aqui; o 403 (sem permissão) e o 404 (recurso de outro Tenant) são das camadas de autorização e pertinência preferidas. Qualquer malformação, assinatura inválida, expiração ou estado não-Ativo responde 401 sem distinguir o motivo — para não revelar informação. A trilha de auditoria (ADR-002) registra as tentativas que resultam em 401.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Validar Token e Resolver Principal. |